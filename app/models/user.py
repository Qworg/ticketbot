"""
User model for the ticketbot application.
Represents Discord users in the system with authentication and role management.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
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
