"""Database connection utilities for the Discord Ticket Bot system.

This module provides database connection management with:
1. Connection pooling for efficient database access
2. Async and sync session factories
3. Health check utilities
4. Error handling and connection recovery
"""

import os
import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional, Generator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, DBAPIError
from sqlalchemy.pool import QueuePool

# Configure logger
logger = logging.getLogger(__name__)

# Get database configuration from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://ticketbot:ticketbot_dev@localhost:5432/ticketbot"
)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# Convert the PostgreSQL URL to its async variant for asyncpg
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine for application use with optimized connection pooling
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=DB_ECHO,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before using them
    connect_args={
        "command_timeout": 10,  # Timeout for commands in seconds
        "server_settings": {
            "application_name": "discord_ticket_bot"  # Identify app in pg_stat_activity
        }
    }
)

# Create sync engine for migrations and utilities
sync_engine = create_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={
        "application_name": "discord_ticket_bot_sync"
    }
)

# Create session factories
AsyncSessionFactory = async_sessionmaker(
    async_engine, 
    expire_on_commit=False,
    class_=AsyncSession
)

SyncSessionFactory = sessionmaker(
    sync_engine,
    expire_on_commit=False
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for use in FastAPI dependency injection.
    
    This context manager provides an async database session with automatic
    transaction management, committing on successful exit or
    rolling back on exception.
    
    Usage:
        async def get_tickets():
            async with get_db_session() as session:
                result = await session.execute(select(Ticket))
                return result.scalars().all()
                
    Yields:
        AsyncSession: SQLAlchemy async session
        
    Raises:
        SQLAlchemyError: If a database error occurs
    """
    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error in database session: {str(e)}")
        raise
    finally:
        await session.close()


async def check_db_connection() -> Dict[str, Any]:
    """Check database connection and return status information.
    
    This function performs a health check on the database connection,
    including connection status, version information, and table statistics.
    
    Returns:
        Dict[str, Any]: Dictionary with connection status information
    """
    start_time = time.time()
    try:
        async with AsyncSessionFactory() as session:
            # Check basic connectivity
            result = await session.execute(text("SELECT version();"))
            version = result.scalar()
            
            # Get table statistics
            table_stats = {}
            for table in ["tickets", "messages", "transcripts", "staff"]:
                try:
                    result = await session.execute(text(f"SELECT count(*) FROM {table};"))
                    table_stats[table] = result.scalar()
                except SQLAlchemyError as e:
                    table_stats[table] = f"Error: {str(e)}"
            
            # Get connection pool statistics
            pool_stats = {}
            if hasattr(async_engine, "pool"):
                pool = async_engine.pool
                pool_stats = {
                    "size": pool.size(),
                    "checkedin": pool.checkedin(),
                    "overflow": pool.overflow(),
                    "checkedout": pool.checkedout(),
                }
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                "status": "connected",
                "version": version,
                "response_time_ms": response_time,
                "tables": table_stats,
                "pool": pool_stats
            }
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }


def get_sync_session():
    """Get a synchronous database session for utilities and scripts.
    
    Returns:
        Session: SQLAlchemy synchronous session
    """
    return SyncSessionFactory()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for getting a database session.
    
    This function provides a synchronous database session for use with
    FastAPI dependency injection. The session is automatically closed
    after the request is processed.
    
    Yields:
        Session: SQLAlchemy synchronous session
    """
    db = SyncSessionFactory()
    try:
        yield db
    finally:
        db.close()


async def execute_with_retry(session: AsyncSession, query, max_retries: int = 3, retry_delay: float = 0.5) -> Any:
    """Execute a database query with retry logic for transient errors.
    
    Args:
        session: SQLAlchemy async session
        query: SQLAlchemy query to execute
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Query result
        
    Raises:
        SQLAlchemyError: If all retry attempts fail
    """
    retries = 0
    last_error = None
    
    while retries <= max_retries:
        try:
            return await session.execute(query)
        except (DBAPIError) as e:
            # Only retry on connection-related errors
            if e.connection_invalidated or "connection" in str(e).lower():
                last_error = e
                retries += 1
                if retries <= max_retries:
                    wait_time = retry_delay * (2 ** (retries - 1))  # Exponential backoff
                    logger.warning(f"Database connection error, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
            raise
    
    logger.error(f"Failed to execute query after {max_retries} retries")
    raise last_error