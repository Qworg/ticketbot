"""
Test-specific database service for integration tests.
Provides database service configured for SQLite testing.
"""
import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.database_service import DatabaseService
from backend.models import Base
from .conftest import test_async_engine, get_test_db_session


class TestDatabaseService(DatabaseService):
    """Test-specific database service with SQLite configuration."""
    
    def __init__(self, session: AsyncSession = None):
        """Initialize test database service."""
        if session is None:
            # Create a mock session for basic initialization
            session = AsyncMock(spec=AsyncSession)
        super().__init__(session)
    
    async def create_tables(self):
        """Create database tables for testing."""
        async with test_async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def cleanup(self):
        """Clean up test database."""
        async with test_async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def create_staff(self, staff_data: dict):
        """Create a test staff member."""
        from backend.models import Staff
        
        staff = Staff(
            discord_id=staff_data["discord_id"],
            username=staff_data["username"],
            role=staff_data["role"],
            permissions=staff_data.get("permissions", {})
        )
        
        self.session.add(staff)
        await self.session.flush()
        return staff
    
    async def execute_query(self, query, params=None):
        """Execute a raw query for testing."""
        if params:
            result = await self.session.execute(text(query), params)
        else:
            result = await self.session.execute(text(query))
        return result


@asynccontextmanager
async def get_test_database_service() -> AsyncGenerator[TestDatabaseService, None]:
    """Get a test database service instance."""
    async with get_test_db_session() as session:
        db_service = TestDatabaseService(session)
        try:
            yield db_service
        except Exception:
            await db_service.rollback()
            raise