"""Test repositories for database service tests."""

import uuid
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.tests.test_models import Base, Ticket, Message, Transcript, Staff

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository class providing common CRUD operations for tests."""
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """Initialize repository with model class and database session."""
        self.model = model
        self.session = session
    
    async def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        # Generate UUID string for id if not provided
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid.uuid4())
            
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """Get a record by its ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """Get all records with optional pagination and ordering."""
        query = select(self.model)
        
        if order_by:
            if hasattr(self.model, order_by):
                query = query.order_by(getattr(self.model, order_by))
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """Update a record by ID."""
        update_data = kwargs
        
        if not update_data:
            return await self.get_by_id(id)
        
        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
        )
        
        return await self.get_by_id(id)
    
    async def delete(self, id: str) -> bool:
        """Delete a record by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0
    
    async def count(self, **filters) -> int:
        """Count records matching the given filters."""
        query = select(func.count(self.model.id))
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        result = await self.session.execute(query)
        return result.scalar()
    
    async def exists(self, **filters) -> bool:
        """Check if a record exists matching the given filters."""
        query = select(self.model.id)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        query = query.limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def find_by(self, **filters) -> List[ModelType]:
        """Find records matching the given filters."""
        query = select(self.model)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def find_one_by(self, **filters) -> Optional[ModelType]:
        """Find a single record matching the given filters."""
        query = select(self.model)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        query = query.limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class TicketRepository(BaseRepository[Ticket]):
    """Ticket repository for tests."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Ticket, session)


class MessageRepository(BaseRepository[Message]):
    """Message repository for tests."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)


class TranscriptRepository(BaseRepository[Transcript]):
    """Transcript repository for tests."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Transcript, session)


class StaffRepository(BaseRepository[Staff]):
    """Staff repository for tests."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Staff, session)