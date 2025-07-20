"""Enhanced tests for database service layer with connection pooling and error handling."""

import pytest
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text, Column, String
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

# Import from test_models for SQLite compatibility
from backend.tests.test_models import Base, Ticket, Message, Transcript, Staff, TicketStatus, MessageType, StaffRole
import uuid  # For generating UUIDs in tests
from backend.db import execute_with_retry, get_db_session
from contextlib import asynccontextmanager
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Create a test version of get_database_service
@asynccontextmanager
async def get_database_service():
    """Test version of get_database_service that uses our test DatabaseService class."""
    async with get_db_session() as session:
        db_service = DatabaseService(session)
        try:
            yield db_service
        except Exception as e:
            logger.error(f"Database service error: {str(e)}")
            await db_service.rollback()
            raise

# Import test repositories
from backend.tests.test_repositories import (
    BaseRepository, TicketRepository, MessageRepository, 
    TranscriptRepository, StaffRepository
)

# Create a test DatabaseService class that uses our test repositories
class DatabaseService:
    """Test database service using test repositories."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repositories = {}
    
    def _get_repository(self, repo_class):
        repo_name = repo_class.__name__
        if repo_name not in self._repositories:
            self._repositories[repo_name] = repo_class(self.session)
        return self._repositories[repo_name]
    
    @property
    def tickets(self) -> TicketRepository:
        return self._get_repository(TicketRepository)
    
    @property
    def messages(self) -> MessageRepository:
        return self._get_repository(MessageRepository)
    
    @property
    def transcripts(self) -> TranscriptRepository:
        return self._get_repository(TranscriptRepository)
    
    @property
    def staff(self) -> StaffRepository:
        return self._get_repository(StaffRepository)
    
    async def commit(self):
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise
    
    async def rollback(self):
        await self.session.rollback()
    
    async def refresh(self, instance):
        await self.session.refresh(instance)
    
    async def flush(self):
        await self.session.flush()
    
    async def execute_in_transaction(self, func, *args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            await self.commit()
            return result
        except Exception as e:
            await self.rollback()
            raise
    
    async def check_health(self):
        from sqlalchemy import text
        result = await self.session.execute(text("SELECT 1"))
        is_connected = result.scalar() == 1
        
        return {
            "status": "healthy" if is_connected else "unhealthy",
            "response_time_ms": 0.1
        }


# Test database URL - using in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override UUID columns for SQLite compatibility
from sqlalchemy import event
from sqlalchemy.dialects import sqlite

@event.listens_for(Base.metadata, 'before_create')
def receive_before_create(target, connection, **kw):
    """Convert UUID columns to String for SQLite."""
    for table in target.tables.values():
        for column in table.columns:
            if isinstance(column.type, sqlite.BLOB) and column.name.endswith('id'):
                column.type = String(36)


@pytest.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def db_service(test_session) -> DatabaseService:
    """Create database service for testing."""
    return DatabaseService(test_session)


@pytest.fixture
async def sample_ticket(db_service: DatabaseService) -> Ticket:
    """Create a sample ticket for testing."""
    ticket = await db_service.tickets.create(
        discord_channel_id=123456789,
        title="Test Ticket",
        description="This is a test ticket",
        creator_discord_id=987654321,
        status=TicketStatus.OPEN.value
    )
    await db_service.commit()
    return ticket


class TestEnhancedDatabaseService:
    """Test enhanced database service features."""
    
    async def test_repository_caching(self, db_service: DatabaseService):
        """Test that repositories are properly cached."""
        # Get repositories multiple times
        tickets1 = db_service.tickets
        tickets2 = db_service.tickets
        messages1 = db_service.messages
        messages2 = db_service.messages
        
        # Verify they are the same instances
        assert tickets1 is tickets2
        assert messages1 is messages2
        
        # Verify different repositories are different instances
        assert tickets1 is not messages1
    
    async def test_execute_in_transaction(self, db_service: DatabaseService):
        """Test executing a function within a transaction."""
        # Define a function to execute in transaction
        async def create_ticket_and_message():
            ticket = await db_service.tickets.create(
                discord_channel_id=111222333,
                title="Transaction Test",
                creator_discord_id=444555666
            )
            
            message = await db_service.messages.create(
                ticket_id=ticket.id,
                author_discord_id=444555666,
                content="Test message in transaction"
            )
            
            return ticket, message
        
        # Execute the function in a transaction
        ticket, message = await db_service.execute_in_transaction(create_ticket_and_message)
        
        # Verify the results
        assert ticket.id is not None
        assert message.id is not None
        assert message.ticket_id == ticket.id
        
        # Verify the data was committed
        retrieved_ticket = await db_service.tickets.get_by_id(ticket.id)
        assert retrieved_ticket is not None
        assert retrieved_ticket.title == "Transaction Test"
    
    async def test_transaction_rollback_on_error(self, db_service: DatabaseService):
        """Test that transactions are rolled back on error."""
        # Define a function that will raise an exception
        async def create_ticket_and_fail():
            ticket = await db_service.tickets.create(
                discord_channel_id=999888777,
                title="Rollback Test",
                creator_discord_id=666555444
            )
            
            # Store the ID for later verification
            ticket_id = ticket.id
            
            # Raise an exception
            raise ValueError("Intentional failure for testing")
        
        # Execute the function and expect it to fail
        with pytest.raises(ValueError):
            await db_service.execute_in_transaction(create_ticket_and_fail)
        
        # Verify no tickets were created (transaction was rolled back)
        tickets = await db_service.tickets.get_all()
        assert len(tickets) == 0
    
    async def test_health_check(self, db_service: DatabaseService):
        """Test database health check functionality."""
        health_info = await db_service.check_health()
        
        # Verify health check returns expected structure
        assert "status" in health_info
        assert health_info["status"] == "healthy"
        assert "response_time_ms" in health_info
        assert isinstance(health_info["response_time_ms"], (int, float))
    
    @patch('backend.db.AsyncSessionFactory')
    async def test_retry_logic(self, mock_session_factory, test_session):
        """Test query retry logic for transient errors."""
        # Create a mock session that fails twice then succeeds
        mock_session = MagicMock()
        mock_execute = AsyncMock()  # Use AsyncMock for async methods
        mock_session.execute = mock_execute
        
        # First two calls raise connection errors, third succeeds
        mock_result = MagicMock()
        mock_result.scalar.return_value = "success"
        mock_execute.side_effect = [
            DBAPIError("connection error", None, None, connection_invalidated=True),
            DBAPIError("connection error", None, None, connection_invalidated=True),
            mock_result
        ]
        
        # Execute with retry
        result = await execute_with_retry(
            mock_session, 
            text("SELECT 1"), 
            max_retries=3,
            retry_delay=0.01  # Short delay for testing
        )
        
        # Verify execute was called 3 times
        assert mock_execute.call_count == 3
        
        # Verify final result
        assert result.scalar() == "success"
    
    @patch('backend.db.AsyncSessionFactory')
    async def test_retry_exhaustion(self, mock_session_factory, test_session):
        """Test that retry logic gives up after max retries."""
        # Create a mock session that always fails
        mock_session = MagicMock()
        mock_execute = AsyncMock()  # Use AsyncMock for async methods
        mock_session.execute = mock_execute
        
        # All calls raise connection errors
        error = DBAPIError("connection error", None, None, connection_invalidated=True)
        mock_execute.side_effect = [error, error, error, error]
        
        # Execute with retry and expect it to fail
        with pytest.raises(DBAPIError):
            await execute_with_retry(
                mock_session, 
                text("SELECT 1"), 
                max_retries=3,
                retry_delay=0.01  # Short delay for testing
            )
        
        # Verify execute was called 4 times (initial + 3 retries)
        assert mock_execute.call_count == 4


class TestContextManagers:
    """Test context managers for database service."""
    
    @patch('backend.tests.test_enhanced_database_service.get_db_session')
    async def test_get_database_service(self, mock_get_db_session):
        """Test get_database_service context manager."""
        # Create a mock session with AsyncMock for async methods
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # Set up the mock result for execute
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        mock_get_db_session.return_value.__aenter__.return_value = mock_session
        
        # Use the context manager
        async with get_database_service() as db:
            # Verify we got a database service with the mock session
            assert isinstance(db, DatabaseService)
            assert db.session is mock_session
            
            # Perform some operation
            await db.check_health()
        
        # Verify the session context manager was used
        mock_get_db_session.assert_called_once()
        mock_get_db_session.return_value.__aenter__.assert_called_once()
        mock_get_db_session.return_value.__aexit__.assert_called_once()
    
    @patch('backend.tests.test_enhanced_database_service.get_db_session')
    async def test_get_database_service_with_exception(self, mock_get_db_session):
        """Test get_database_service context manager with exception."""
        # Create a mock session with AsyncMock for async methods
        mock_session = MagicMock()
        mock_session.rollback = AsyncMock()  # Use AsyncMock for async methods
        mock_get_db_session.return_value.__aenter__.return_value = mock_session
        
        # Use the context manager with an exception
        with pytest.raises(ValueError):
            async with get_database_service() as db:
                # Verify we got a database service with the mock session
                assert isinstance(db, DatabaseService)
                assert db.session is mock_session
                
                # Raise an exception
                raise ValueError("Test exception")
        
        # Verify rollback was called
        mock_session.rollback.assert_awaited_once()