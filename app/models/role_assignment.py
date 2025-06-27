"""
Role assignment model for managing user role assignments in guilds.
Supports guild-specific role assignments with Redis caching.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Set
from sqlalchemy import Column, String, DateTime, BigInteger, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Session, relationship
from app.database import Base
from app.permissions import Permission, get_user_permissions


class RoleAssignment(Base):
    """
    Role assignment model for guild-specific user roles.
    Allows users to have different roles in different Discord guilds.
    """
    __tablename__ = "role_assignments"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to users table
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Discord guild ID where this role assignment applies
    guild_id = Column(BigInteger, nullable=False, index=True)
    
    # Role assigned to user in this guild
    role = Column(String(50), nullable=False, default="USER")
    
    # Who assigned this role (for audit trail)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="role_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])

    # Unique constraint: one role per user per guild
    __table_args__ = (
        Index('idx_role_assignments_user_guild', 'user_id', 'guild_id', unique=True),
        Index('idx_role_assignments_guild_role', 'guild_id', 'role'),
        Index('idx_role_assignments_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<RoleAssignment(user_id={self.user_id}, guild_id={self.guild_id}, role={self.role})>"


# Add relationship to User model
def get_user_role_in_guild(db: Session, user_id: uuid.UUID, guild_id: int) -> str:
    """
    Get user's role in a specific guild.
    
    Args:
        db: Database session
        user_id: UUID of the user
        guild_id: Discord guild ID
        
    Returns:
        str: User's role in the guild, defaults to "USER" if not found
    """
    role_assignment = db.query(RoleAssignment).filter(
        RoleAssignment.user_id == user_id,
        RoleAssignment.guild_id == guild_id
    ).first()
    
    if role_assignment is not None:
        return str(role_assignment.role)
    
    # Check user's global role as fallback
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None:
        return str(user.role)
    
    return "USER"  # Default role


def get_user_permissions_in_guild(db: Session, user_id: uuid.UUID, guild_id: int) -> Set[Permission]:
    """
    Get user's permissions in a specific guild.
    
    Args:
        db: Database session
        user_id: UUID of the user
        guild_id: Discord guild ID
        
    Returns:
        Set[Permission]: Set of permissions for the user in the guild
    """
    user_role = get_user_role_in_guild(db, user_id, guild_id)
    return get_user_permissions(user_role)


def assign_role_in_guild(
    db: Session, 
    user_id: uuid.UUID, 
    guild_id: int, 
    role: str, 
    assigned_by: Optional[uuid.UUID] = None
) -> RoleAssignment:
    """
    Assign or update a user's role in a guild.
    
    Args:
        db: Database session
        user_id: UUID of the user
        guild_id: Discord guild ID
        role: Role to assign
        assigned_by: UUID of the user making the assignment
        
    Returns:
        RoleAssignment: The created or updated role assignment
    """
    # Check if assignment already exists
    existing = db.query(RoleAssignment).filter(
        RoleAssignment.user_id == user_id,
        RoleAssignment.guild_id == guild_id
    ).first()
    
    if existing:
        # Update existing assignment
        db.query(RoleAssignment).filter(
            RoleAssignment.user_id == user_id,
            RoleAssignment.guild_id == guild_id
        ).update({
            "role": role,
            "assigned_by": assigned_by,
            "updated_at": func.now()
        })
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_assignment = RoleAssignment(
            user_id=user_id,
            guild_id=guild_id,
            role=role,
            assigned_by=assigned_by
        )
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        return new_assignment
