"""
User model for the ticketbot application.
Represents Discord users in the system with authentication and role management.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Session, relationship
from app.database import Base


class User(Base):
    """
    User model representing Discord users in the system.
    
    Attributes:
        id: Unique UUID primary key
        discord_id: Discord user ID (snowflake), unique and indexed
        email: User email address, nullable, indexed for auth queries
        role: User role for permission management (USER, STAFF, ADMIN)
        created_at: Timestamp when user was first created
        updated_at: Timestamp when user was last updated
    """
    __tablename__ = "users"

    # Primary key - UUID for better security and distribution
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Discord ID - required, unique, and indexed for fast lookups
    discord_id = Column(BigInteger, unique=True, nullable=False, index=True)
    
    # Email - optional, indexed for authentication queries
    email = Column(String(255), nullable=True, index=True)
    
    # Role - required for permission management
    role = Column(String(50), nullable=False, default="USER")
    
    # Timestamps - automatic creation and update tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    role_assignments = relationship("RoleAssignment", foreign_keys="RoleAssignment.user_id", back_populates="user")

    # Additional indexes for performance
    __table_args__ = (
        Index('idx_users_discord_id', 'discord_id'),
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
        Index('idx_users_created_at', 'created_at'),
    )

    def __init__(self, discord_id: int, email: str | None = None, role: str | None = None, **kwargs):
        """
        Initialize User with proper defaults.
        
        Args:
            discord_id: Discord user ID (snowflake)
            email: Optional email address
            role: User role, defaults to "USER"
        """
        super().__init__(
            discord_id=discord_id,
            email=email,
            role=role or "USER",
            **kwargs
        )

    def __repr__(self):
        """String representation of User model."""
        return f"<User(id={self.id}, discord_id={self.discord_id}, role={self.role})>"

    def to_dict(self):
        """Convert User model to dictionary for API responses."""
        return {
            "id": str(self.id),
            "discord_id": str(self.discord_id),
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
        }

    @classmethod
    def create_user(cls, discord_id: int, email: str | None = None, role: str = "USER"):
        """
        Factory method to create a new user with validation.
        
        Args:
            discord_id: Discord user ID (snowflake)
            email: Optional email address
            role: User role, defaults to "USER"
            
        Returns:
            New User instance
        """
        return cls(
            discord_id=discord_id,
            email=email,
            role=role.upper()
        )


# CRUD Functions for User Management

def create_user(db: Session, discord_id: int, email: Optional[str] = None, 
                username: Optional[str] = None, avatar: Optional[str] = None, 
                role: str = "USER") -> User:
    """
    Create a new user in the database.
    
    Args:
        db: Database session
        discord_id: Discord user ID (snowflake)
        email: Optional email address
        username: Optional Discord username
        avatar: Optional Discord avatar hash
        role: User role, defaults to "USER"
        
    Returns:
        Created User instance
    """
    user = User(
        discord_id=discord_id,
        email=email,
        role=role.upper()
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_discord_id(db: Session, discord_id: int) -> Optional[User]:
    """
    Get user by Discord ID.
    
    Args:
        db: Database session
        discord_id: Discord user ID (snowflake)
        
    Returns:
        User instance if found, None otherwise
    """
    return db.query(User).filter(User.discord_id == discord_id).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """
    Get user by UUID.
    
    Args:
        db: Database session
        user_id: User UUID
        
    Returns:
        User instance if found, None otherwise
    """
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id, **kwargs) -> Optional[User]:
    """
    Update user information.
    
    Args:
        db: Database session
        user_id: User UUID
        **kwargs: Fields to update
        
    Returns:
        Updated User instance if found, None otherwise
    """
    user = get_user_by_id(db, user_id)
    if user:
        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get user by email address.
    
    Args:
        db: Database session
        email: User email address
        
    Returns:
        User instance if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    """
    List users with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of User instances
    """
    return db.query(User).offset(skip).limit(limit).all()


def delete_user(db: Session, user_id: uuid.UUID) -> bool:
    """
    Delete user by ID.
    
    Args:
        db: Database session
        user_id: User UUID
        
    Returns:
        True if user was deleted, False if not found
    """
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False
