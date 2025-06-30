"""
Guild model for storing guild-specific configuration.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, func, JSON
from sqlalchemy.orm import Session

from ..database import Base


class Guild(Base):
    """Guild configuration model."""
    
    __tablename__ = 'guilds'
    
    # Discord guild ID as primary key
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Guild name (for reference)
    name = Column(String(100), nullable=False)
    
    # Staff role configurations (JSON array of role IDs)
    staff_role_ids = Column(JSON, nullable=True, default=list)
    
    # Admin role configurations (JSON array of role IDs)
    admin_role_ids = Column(JSON, nullable=True, default=list)
    
    # Ticket category settings
    ticket_category_id = Column(BigInteger, nullable=True)
    ticket_category_name = Column(String(100), nullable=False, default="🎫 Tickets")
    
    # Auto-archive settings
    auto_archive_hours = Column(BigInteger, nullable=False, default=24)
    
    # Transcript settings
    auto_transcript = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


def get_guild_by_id(db: Session, guild_id: int) -> Optional[Guild]:
    """
    Get guild configuration by Discord guild ID.
    
    Args:
        db: Database session
        guild_id: Discord guild ID
        
    Returns:
        Guild configuration or None if not found
    """
    return db.query(Guild).filter(Guild.id == guild_id).first()


def create_or_update_guild(
    db: Session,
    guild_id: int,
    name: str,
    staff_role_ids: Optional[List[int]] = None,
    admin_role_ids: Optional[List[int]] = None,
    ticket_category_id: Optional[int] = None,
    ticket_category_name: str = "🎫 Tickets",
    auto_archive_hours: int = 24,
    auto_transcript: bool = False
) -> Guild:
    """
    Create or update guild configuration.
    
    Args:
        db: Database session
        guild_id: Discord guild ID
        name: Guild name
        staff_role_ids: List of staff role IDs
        admin_role_ids: List of admin role IDs
        ticket_category_id: Ticket category channel ID
        ticket_category_name: Ticket category name
        auto_archive_hours: Hours before auto-archiving tickets
        auto_transcript: Whether to auto-generate transcripts
        
    Returns:
        Guild configuration object
    """
    guild = get_guild_by_id(db, guild_id)
    
    if guild:
        # Update existing guild
        guild.name = name
        if staff_role_ids is not None:
            guild.staff_role_ids = staff_role_ids
        if admin_role_ids is not None:
            guild.admin_role_ids = admin_role_ids
        if ticket_category_id is not None:
            guild.ticket_category_id = ticket_category_id
        guild.ticket_category_name = ticket_category_name
        guild.auto_archive_hours = auto_archive_hours
        guild.auto_transcript = auto_transcript
        guild.updated_at = datetime.utcnow()
    else:
        # Create new guild
        guild = Guild(
            id=guild_id,
            name=name,
            staff_role_ids=staff_role_ids or [],
            admin_role_ids=admin_role_ids or [],
            ticket_category_id=ticket_category_id,
            ticket_category_name=ticket_category_name,
            auto_archive_hours=auto_archive_hours,
            auto_transcript=auto_transcript
        )
        db.add(guild)
    
    db.commit()
    db.refresh(guild)
    return guild


def get_guild_staff_role_ids(db: Session, guild_id: int) -> List[int]:
    """
    Get staff role IDs for a guild.
    
    Args:
        db: Database session
        guild_id: Discord guild ID
        
    Returns:
        List of staff role IDs
    """
    guild = get_guild_by_id(db, guild_id)
    if guild and guild.staff_role_ids:
        return guild.staff_role_ids
    return []


def get_guild_admin_role_ids(db: Session, guild_id: int) -> List[int]:
    """
    Get admin role IDs for a guild.
    
    Args:
        db: Database session
        guild_id: Discord guild ID
        
    Returns:
        List of admin role IDs
    """
    guild = get_guild_by_id(db, guild_id)
    if guild and guild.admin_role_ids:
        return guild.admin_role_ids
    return []
