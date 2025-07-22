"""
Base repository class for common database operations.
"""

from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.models import Base

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, db: Session, model: Type[T]):
        """
        Initialize the base repository.
        
        Args:
            db: Database session
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model
    
    def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: Entity ID
            
        Returns:
            Entity if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Get all entities with pagination.
        
        Args:
            skip: Number of entities to skip
            limit: Maximum number of entities to return
            
        Returns:
            List of entities
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def count(self) -> int:
        """
        Count total number of entities.
        
        Returns:
            Total count of entities
        """
        return self.db.query(self.model).count()
    
    def create(self, entity_data: Dict[str, Any]) -> T:
        """
        Create a new entity.
        
        Args:
            entity_data: Dictionary containing entity data
            
        Returns:
            Created entity
            
        Raises:
            IntegrityError: If there's a database constraint violation
        """
        entity = self.model(**entity_data)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def update(self, id: UUID, update_data: Dict[str, Any]) -> Optional[T]:
        """
        Update an entity by ID.
        
        Args:
            id: Entity ID
            update_data: Dictionary containing update data
            
        Returns:
            Updated entity if found, None otherwise
        """
        entity = self.get_by_id(id)
        if not entity:
            return None
        
        for key, value in update_data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def delete(self, id: UUID) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            True if entity was deleted, False if not found
        """
        entity = self.get_by_id(id)
        if not entity:
            return False
        
        self.db.delete(entity)
        self.db.commit()
        return True
    
    def exists(self, id: UUID) -> bool:
        """
        Check if an entity exists by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            True if entity exists, False otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first() is not None