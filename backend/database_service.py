"""Database service layer providing repository access and transaction management.

This module implements a database service layer that provides:
1. Connection pooling and management
2. Repository pattern implementation for database operations
3. Transaction management with automatic commit/rollback
4. Error handling and recovery
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional, Type, TypeVar, Generic
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from backend.db import get_db_session
from backend.repositories import (
    BaseRepository,
    TicketRepository,
    MessageRepository,
    TranscriptRepository,
    StaffRepository
)

# Configure logger
logger = logging.getLogger(__name__)

# Type variable for repository types
T = TypeVar('T', bound=BaseRepository)


class DatabaseService:
    """Database service providing access to repositories and transaction management.
    
    This service implements the repository pattern for database operations,
    providing a clean interface for accessing different entity repositories
    while handling transaction management and connection pooling.
    
    Attributes:
        session: SQLAlchemy async session
        _repositories: Dictionary of cached repository instances
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize database service with session.
        
        Args:
            session: Async database session
        """
        self.session = session
        self._repositories = {}
    
    def _get_repository(self, repo_class: Type[T]) -> T:
        """Get or create a repository instance.
        
        Args:
            repo_class: Repository class to instantiate
            
        Returns:
            Repository instance
        """
        repo_name = repo_class.__name__
        if repo_name not in self._repositories:
            self._repositories[repo_name] = repo_class(self.session)
        return self._repositories[repo_name]
    
    @property
    def tickets(self) -> TicketRepository:
        """Get ticket repository."""
        return self._get_repository(TicketRepository)
    
    @property
    def messages(self) -> MessageRepository:
        """Get message repository."""
        return self._get_repository(MessageRepository)
    
    @property
    def transcripts(self) -> TranscriptRepository:
        """Get transcript repository."""
        return self._get_repository(TranscriptRepository)
    
    @property
    def staff(self) -> StaffRepository:
        """Get staff repository."""
        return self._get_repository(StaffRepository)
    
    async def commit(self):
        """Commit the current transaction.
        
        Raises:
            SQLAlchemyError: If the commit fails
        """
        try:
            await self.session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error committing transaction: {str(e)}")
            await self.session.rollback()
            raise
    
    async def rollback(self):
        """Rollback the current transaction.
        
        Raises:
            SQLAlchemyError: If the rollback fails
        """
        try:
            await self.session.rollback()
        except SQLAlchemyError as e:
            logger.error(f"Error rolling back transaction: {str(e)}")
            raise
    
    async def refresh(self, instance):
        """Refresh an instance from the database.
        
        Args:
            instance: SQLAlchemy model instance to refresh
            
        Raises:
            SQLAlchemyError: If the refresh fails
        """
        try:
            await self.session.refresh(instance)
        except SQLAlchemyError as e:
            logger.error(f"Error refreshing instance: {str(e)}")
            raise
    
    async def flush(self):
        """Flush pending changes to the database.
        
        Raises:
            SQLAlchemyError: If the flush fails
        """
        try:
            await self.session.flush()
        except SQLAlchemyError as e:
            logger.error(f"Error flushing session: {str(e)}")
            raise
    
    async def execute_in_transaction(self, func, *args, **kwargs):
        """Execute a function within a transaction.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function
            
        Raises:
            Exception: Any exception raised by the function
        """
        try:
            result = await func(*args, **kwargs)
            await self.commit()
            return result
        except Exception as e:
            await self.rollback()
            logger.error(f"Transaction failed: {str(e)}")
            raise
    
    async def check_health(self) -> Dict[str, Any]:
        """Check database health and return status information.
        
        Returns:
            Dictionary with health check information
        """
        start_time = time.time()
        try:
            from sqlalchemy import text
            result = await self.session.execute(text("SELECT 1"))
            is_connected = result.scalar() == 1
            
            # Get connection pool stats if available
            pool_info = {}
            if hasattr(self.session.bind, "pool"):
                pool = self.session.bind.pool
                pool_info = {
                    "size": pool.size(),
                    "checkedin": pool.checkedin(),
                    "overflow": pool.overflow(),
                    "checkedout": pool.checkedout(),
                }
            
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "pool": pool_info
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }


@asynccontextmanager
async def get_database_service() -> AsyncGenerator[DatabaseService, None]:
    """Get a database service instance with automatic transaction management.
    
    This context manager provides a database service with automatic
    transaction management, committing on successful exit or
    rolling back on exception.
    
    Usage:
        async def some_function():
            async with get_database_service() as db:
                ticket = await db.tickets.create(...)
                message = await db.messages.create(...)
                # Transaction is automatically committed on success
                # or rolled back on exception
                
    Yields:
        DatabaseService instance
        
    Raises:
        SQLAlchemyError: If a database error occurs
    """
    async with get_db_session() as session:
        db_service = DatabaseService(session)
        try:
            yield db_service
        except Exception as e:
            logger.error(f"Database service error: {str(e)}")
            await db_service.rollback()
            raise


# Dependency for FastAPI
async def get_db_service() -> AsyncGenerator[DatabaseService, None]:
    """FastAPI dependency for database service.
    
    This function is designed to be used as a FastAPI dependency
    to provide a database service to API endpoints.
    
    Usage in FastAPI endpoints:
        @app.get("/tickets")
        async def get_tickets(db: DatabaseService = Depends(get_db_service)):
            return await db.tickets.get_all()
            
    Yields:
        DatabaseService instance
    """
    async with get_database_service() as db:
        yield db