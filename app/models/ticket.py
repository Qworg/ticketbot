"""
Ticket model for the ticketbot application.
Represents support tickets created by users in Discord guilds.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean, ForeignKey, Index, or_
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import Base
from app.status import (
    TicketStatus, validate_status_transition, enforce_status_transition, 
    log_status_transition, StatusTransitionError, is_open_status, 
    is_closed_status, can_be_assigned, requires_close_reason
)
import logging

logger = logging.getLogger(__name__)

class Ticket(Base):
    """
    Ticket model representing support tickets in the system.
    
    Attributes:
        id: Unique serial primary key
        channel_id: Discord channel ID (snowflake), unique
        guild_id: Discord guild ID (snowflake), references guilds table
        creator_id: Discord user ID who created the ticket
        assigned_to: Discord user ID of assigned staff member (nullable)
        status: Current ticket status (open, in_progress, resolved, closed)
        category: Ticket categorization for organization
        reason: User-provided description of the ticket
        created_at: Timestamp when ticket was created
        updated_at: Timestamp when ticket was last updated
        closed_at: Timestamp when ticket was closed (nullable)
        close_reason: Reason provided when ticket was closed (nullable)
        is_shadow_closed: Whether ticket is shadow closed (archived but not fully closed)
    """
    __tablename__ = "tickets"

    # Primary key - SERIAL for auto-incrementing integer
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Discord channel ID - optional, unique for channel reference
    channel_id = Column(BigInteger, unique=True, nullable=True, index=True)
    
    # Discord guild ID - required, will reference guilds table
    guild_id = Column(BigInteger, nullable=False, index=True)
    
    # Creator Discord user ID - required
    creator_id = Column(BigInteger, nullable=False, index=True)
    
    # Assigned staff member - nullable for unassigned tickets
    assigned_to = Column(BigInteger, nullable=True, index=True)
    
    # Ticket status - required with default 'open'
    status = Column(String(50), nullable=False, default='open', index=True)
    
    # Ticket category - optional for organization
    category = Column(String(100), nullable=True)
    
    # Ticket reason/description - required
    reason = Column(Text, nullable=False)
    
    # Timestamps - automatic creation and update tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Closure tracking
    closed_at = Column(DateTime(timezone=True), nullable=True)
    close_reason = Column(Text, nullable=True)
    
    # Shadow closure for archiving
    is_shadow_closed = Column(Boolean, nullable=False, default=False)

    # Indexes for performance optimization
    __table_args__ = (
        # Composite index for guild filtering by status
        Index('idx_tickets_guild_status', 'guild_id', 'status'),
        # Index for staff ticket queries
        Index('idx_tickets_assigned_to', 'assigned_to'),
        # Index for user ticket lookups
        Index('idx_tickets_creator_id', 'creator_id'),
        # Index for channel lookups
        Index('idx_tickets_channel_id', 'channel_id'),
        # Index for status queries
        Index('idx_tickets_status', 'status'),
        # Index for created_at ordering
        Index('idx_tickets_created_at', 'created_at'),
    )

    def __init__(self, **kwargs):
        """Initialize ticket with default values."""
        if 'status' not in kwargs:
            kwargs['status'] = 'open'
        if 'is_shadow_closed' not in kwargs:
            kwargs['is_shadow_closed'] = False
        super().__init__(**kwargs)

    def __repr__(self):
        """String representation of the ticket."""
        return f"<Ticket(id={self.id}, channel_id={self.channel_id}, status='{self.status}', creator_id={self.creator_id})>"

    def is_open(self) -> bool:
        """Check if ticket is in an open state."""
        return is_open_status(str(self.status))

    def is_closed(self) -> bool:
        """Check if ticket is closed."""
        return is_closed_status(str(self.status))

    def can_be_assigned(self) -> bool:
        """Check if ticket can be assigned to staff."""
        return can_be_assigned(str(self.status))

    def validate_status_transition(self, new_status: str) -> bool:
        """Validate if transition to new status is allowed."""
        return validate_status_transition(str(self.status), new_status)

    def update_status(
        self, 
        new_status: str, 
        changed_by: int,
        close_reason: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> bool:
        """
        Update ticket status with validation and audit logging.
        
        Args:
            new_status: New status to transition to
            changed_by: User ID who is making the change
            close_reason: Reason for closure if transitioning to closed
            db_session: Database session for persistence
            
        Returns:
            True if status was updated successfully
            
        Raises:
            StatusTransitionError: If transition is invalid
            ValueError: If close_reason is required but not provided
        """
        # Validate the transition
        previous_status = str(self.status)
        validated_status = enforce_status_transition(previous_status, new_status)
        
        # Check if close reason is required
        if requires_close_reason(previous_status, validated_status) and not close_reason:
            raise ValueError("Close reason is required when transitioning to closed status")
        
        # Update the status
        self.status = validated_status
        
        # Set closed_at timestamp if transitioning to closed
        if validated_status == TicketStatus.CLOSED:
            self.closed_at = datetime.utcnow()
            if close_reason:
                self.close_reason = close_reason
        
        # Log the transition
        ticket_id = getattr(self, 'id', 0)
        transition_log = log_status_transition(
            ticket_id=ticket_id,
            previous_status=previous_status,
            new_status=validated_status,
            changed_by=changed_by,
            reason=close_reason
        )
        
        # Persist to database if session provided
        if db_session:
            try:
                db_session.add(self)
                db_session.commit()
                logger.info(f"Updated ticket {self.id} status from {previous_status} to {validated_status}")
            except SQLAlchemyError as e:
                db_session.rollback()
                logger.error(f"Failed to update ticket status: {e}")
                raise
        
        return True

    def to_dict(self) -> dict:
        """Convert ticket to dictionary representation."""
        # Handle datetime fields properly for SQLAlchemy instances
        created_at_str = None
        updated_at_str = None
        closed_at_str = None
        
        if hasattr(self, 'created_at') and self.created_at is not None:
            created_at_str = self.created_at.isoformat()
        if hasattr(self, 'updated_at') and self.updated_at is not None:
            updated_at_str = self.updated_at.isoformat()
        if hasattr(self, 'closed_at') and self.closed_at is not None:
            closed_at_str = self.closed_at.isoformat()
            
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'guild_id': self.guild_id,
            'creator_id': self.creator_id,
            'assigned_to': self.assigned_to,
            'status': self.status,
            'category': self.category,
            'reason': self.reason,
            'created_at': created_at_str,
            'updated_at': updated_at_str,
            'closed_at': closed_at_str,
            'close_reason': self.close_reason,
            'is_shadow_closed': self.is_shadow_closed,
        }


# Database functions for ticket operations

def create_ticket(
    db: Session,
    guild_id: int,
    creator_id: int,
    reason: str,
    channel_id: Optional[int] = None,
    category: Optional[str] = None
) -> Ticket:
    """
    Create a new ticket in the database.
    
    Args:
        db: Database session
        guild_id: Discord guild ID where ticket is created
        creator_id: Discord user ID who created the ticket
        reason: Ticket description/reason
        channel_id: Optional Discord channel ID for the ticket
        category: Optional category for the ticket
        
    Returns:
        Created Ticket object
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        ticket = Ticket(
            guild_id=guild_id,
            creator_id=creator_id,
            reason=reason,
            channel_id=channel_id,
            category=category,
            status=TicketStatus.OPEN.value
        )
        
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        logger.info(f"Created ticket {ticket.id} for user {creator_id} in guild {guild_id}")
        return ticket
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create ticket: {e}")
        raise


def get_user_open_tickets_in_guild(db: Session, user_id: int, guild_id: int) -> List[Ticket]:
    """
    Get all open tickets for a user in a specific guild.
    
    Args:
        db: Database session
        user_id: Discord user ID
        guild_id: Discord guild ID
        
    Returns:
        List of open tickets for the user in the guild
    """
    try:
        # Get all tickets for user in guild and filter in Python for now
        all_tickets = db.query(Ticket).filter(
            Ticket.creator_id == user_id,
            Ticket.guild_id == guild_id
        ).all()
        
        # Filter for open statuses in Python
        open_tickets = [
            ticket for ticket in all_tickets 
            if ticket.status in [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]
        ]
        
        return open_tickets
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to query user tickets: {e}")
        raise


def has_open_ticket_in_guild(db: Session, user_id: int, guild_id: int) -> bool:
    """
    Check if a user already has an open ticket in a guild.
    
    Args:
        db: Database session
        user_id: Discord user ID
        guild_id: Discord guild ID
        
    Returns:
        True if user has an open ticket in the guild, False otherwise
    """
    try:
        # Get all tickets for user in guild and check in Python
        all_tickets = db.query(Ticket).filter(
            Ticket.creator_id == user_id,
            Ticket.guild_id == guild_id
        ).all()
        
        # Check if any are open
        for ticket in all_tickets:
            if ticket.status in [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]:
                return True
        
        return False
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to check for existing tickets: {e}")
        raise


def get_ticket_by_id(db: Session, ticket_id: int) -> Optional[Ticket]:
    """
    Get a ticket by its ID.
    
    Args:
        db: Database session
        ticket_id: Ticket ID
        
    Returns:
        Ticket object if found, None otherwise
    """
    try:
        return db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to get ticket by ID: {e}")
        raise


def get_ticket_by_channel_id(db: Session, channel_id: int) -> Optional[Ticket]:
    """
    Get a ticket by its Discord channel ID.
    
    Args:
        db: Database session
        channel_id: Discord channel ID
        
    Returns:
        Ticket object if found, None otherwise
    """
    try:
        return db.query(Ticket).filter(Ticket.channel_id == channel_id).first()
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to get ticket by channel ID: {e}")
        raise


def get_ticket_details_with_users(db: Session, ticket_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a ticket by its ID with related user information.
    
    Args:
        db: Database session
        ticket_id: Ticket ID
        
    Returns:
        Dictionary with ticket data and related user information, None if not found
    """
    try:
        # Import here to avoid circular imports
        from app.models.user import User
        
        # Get the ticket first
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            return None
        
        # Get creator user information
        creator_user = None
        if ticket.creator_id is not None:
            creator_user = db.query(User).filter(User.discord_id == ticket.creator_id).first()
        
        # Get assigned staff user information
        assigned_user = None
        if ticket.assigned_to is not None:
            assigned_user = db.query(User).filter(User.discord_id == ticket.assigned_to).first()
        
        # Build response dictionary
        ticket_data = {
            'id': ticket.id,
            'channel_id': ticket.channel_id,
            'guild_id': ticket.guild_id,
            'creator_id': ticket.creator_id,
            'assigned_to': ticket.assigned_to,
            'status': ticket.status,
            'category': ticket.category,
            'reason': ticket.reason,
            'created_at': ticket.created_at,
            'updated_at': ticket.updated_at,
            'closed_at': ticket.closed_at,
            'close_reason': ticket.close_reason,
            'is_shadow_closed': ticket.is_shadow_closed,
            'creator': None,
            'assigned_staff': None,
            'participants_count': 1,  # At minimum the creator
            'recent_messages_count': 0  # TODO: Implement when messages table exists
        }
        
        # Add creator information if found
        if creator_user:
            ticket_data['creator'] = {
                'id': str(creator_user.id),
                'discord_id': creator_user.discord_id,
                'email': creator_user.email,
                'role': creator_user.role
            }
        
        # Add assigned staff information if found
        if assigned_user:
            ticket_data['assigned_staff'] = {
                'id': str(assigned_user.id),
                'discord_id': assigned_user.discord_id,
                'email': assigned_user.email,
                'role': assigned_user.role
            }
        
        return ticket_data
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to get ticket details with users: {e}")
        raise
