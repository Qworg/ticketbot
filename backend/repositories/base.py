"""Base repository class with common database operations."""

from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository class providing common CRUD operations."""
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """Initialize repository with model class and database session.
        
        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session
    
    async def create(self, **kwargs) -> ModelType:
        """Create a new record.
        
        Args:
            **kwargs: Field values for the new record
            
        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get a record by its ID.
        
        Args:
            id: Record UUID
            
        Returns:
            Model instance or None if not found
        """
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
        """Get all records with optional pagination and ordering.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Field name to order by
            
        Returns:
            List of model instances
        """
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
    
    async def update(self, id: UUID, **kwargs) -> Optional[ModelType]:
        """Update a record by ID.
        
        Args:
            id: Record UUID
            **kwargs: Fields to update
            
        Returns:
            Updated model instance or None if not found
        """
        # Use all provided kwargs, including explicit None values
        update_data = kwargs
        
        if not update_data:
            return await self.get_by_id(id)
        
        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
        )
        
        return await self.get_by_id(id)
    
    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID.
        
        Args:
            id: Record UUID
            
        Returns:
            True if record was deleted, False if not found
        """
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0
    
    async def count(self, **filters) -> int:
        """Count records matching the given filters.
        
        Args:
            **filters: Field filters
            
        Returns:
            Number of matching records
        """
        query = select(func.count(self.model.id))
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        result = await self.session.execute(query)
        return result.scalar()
    
    async def exists(self, **filters) -> bool:
        """Check if a record exists matching the given filters.
        
        Args:
            **filters: Field filters
            
        Returns:
            True if record exists, False otherwise
        """
        query = select(self.model.id)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        query = query.limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def find_by(self, **filters) -> List[ModelType]:
        """Find records matching the given filters.
        
        Args:
            **filters: Field filters
            
        Returns:
            List of matching model instances
        """
        query = select(self.model)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def find_one_by(self, **filters) -> Optional[ModelType]:
        """Find a single record matching the given filters.
        
        Args:
            **filters: Field filters
            
        Returns:
            Model instance or None if not found
        """
        query = select(self.model)
        
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        
        query = query.limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()