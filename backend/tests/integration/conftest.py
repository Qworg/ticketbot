"""
Configuration for integration tests.
Provides shared fixtures and setup for integration testing.
"""
import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from contextlib import asynccontextmanager

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///test_integration.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

# Create test-specific database engines without pool settings for SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite:///test_integration.db"

# Create async engine for SQLite (no pool settings)
test_async_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

# Create sync engine for SQLite
test_sync_engine = create_engine(
    "sqlite:///test_integration.db",
    echo=False,
    connect_args={"check_same_thread": False}
)

# Create session factories for testing
TestAsyncSessionFactory = async_sessionmaker(
    test_async_engine,
    expire_on_commit=False,
    class_=AsyncSession
)

@asynccontextmanager
async def get_test_db_session():
    """Get a test database session."""
    session = TestAsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_environment():
    """Set up test environment for each test."""
    # Mock external dependencies
    with patch('backend.services.discord_service.DiscordService') as mock_discord:
        mock_discord.return_value.send_message = lambda *args, **kwargs: None
        mock_discord.return_value.create_channel = lambda *args, **kwargs: {"id": 123456789}
        mock_discord.return_value.update_permissions = lambda *args, **kwargs: None
        
        yield mock_discord


@pytest.fixture
def mock_redis():
    """Mock Redis for tests that don't need real Redis."""
    with patch('backend.services.redis_service.RedisService') as mock:
        mock_instance = mock.return_value
        mock_instance.publish = lambda *args, **kwargs: None
        mock_instance.subscribe = lambda *args, **kwargs: None
        yield mock_instance


@pytest.fixture
def mock_database():
    """Mock database for tests that don't need real database."""
    with patch('backend.database_service.DatabaseService') as mock:
        mock_instance = mock.return_value
        mock_instance.execute_query = lambda *args, **kwargs: []
        mock_instance.create_tables = lambda: None
        mock_instance.cleanup = lambda: None
        yield mock_instance