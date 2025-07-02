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
    
    # Assignment tracking
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    
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

    # Relationships
    participants = relationship("TicketParticipant", back_populates="ticket", cascade="all, delete-orphan")

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
        user_role: str = "USER",
        close_reason: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> bool:
        """
        Update ticket status with validation and audit logging.
        
        Args:
            new_status: New status to transition to
            changed_by: User ID who is making the change
            user_role: Role of the user making the change (for permission checking)
            close_reason: Reason for closure if transitioning to closed
            db_session: Database session for persistence
            
        Returns:
            True if status was updated successfully
            
        Raises:
            StatusTransitionError: If transition is invalid
            TicketClosureError: If closure validation fails
            ValueError: If close_reason is required but not provided
        """
        from app.status import validate_ticket_closure, TicketClosureError
        
        # Validate the transition
        previous_status = str(self.status)
        validated_status = enforce_status_transition(previous_status, new_status)
        
        # If transitioning to closed, perform comprehensive closure validation
        if validated_status == TicketStatus.CLOSED:
            try:
                validate_ticket_closure(
                    ticket=self,
                    user_id=changed_by,
                    user_role=user_role,
                    close_reason=close_reason
                )
            except TicketClosureError as e:
                logger.error(f"Ticket closure validation failed: {e}")
                raise
        
        # Check if close reason is required (this is also validated in closure validation)
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


def update_ticket(
    db: Session,
    ticket_id: int,
    user_id: int,
    user_role: str = "USER",
    status: Optional[str] = None,
    category: Optional[str] = None,
    assigned_to: Optional[int] = None,
    close_reason: Optional[str] = None
) -> Ticket:
    """
    Update a ticket with the provided fields.
    
    Args:
        db: Database session
        ticket_id: ID of the ticket to update
        user_id: Discord user ID of the user making the update
        user_role: Role of the user making the update (for permission checking)
        status: New status (optional)
        category: New category (optional)
        assigned_to: New assigned user ID (optional, can be None to unassign)
        close_reason: Reason for closing (optional, required when transitioning to closed)
        
    Returns:
        Updated Ticket object
        
    Raises:
        ValueError: If ticket not found or validation fails
        StatusTransitionError: If status transition is invalid
        TicketClosureError: If closure validation fails
        SQLAlchemyError: If database operation fails
    """
    try:
        # Get the ticket
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket with ID {ticket_id} not found")
        
        changes_made = []
        
        # Update status if provided
        if status is not None and status != str(getattr(ticket, 'status', '')):
            # Use the ticket's update_status method for validation and logging
            ticket.update_status(
                new_status=status,
                changed_by=user_id,
                user_role=user_role,
                close_reason=close_reason
            )
            changes_made.append(f"status: {getattr(ticket, 'status', '')} -> {status}")
        
        # Update category if provided
        if category is not None and category != str(getattr(ticket, 'category', '') or ''):
            old_category = getattr(ticket, 'category', None) or "None"
            setattr(ticket, 'category', category)
            changes_made.append(f"category: {old_category} -> {category or 'None'}")
        
        # Update assigned_to if provided (including None to unassign)
        current_assigned = getattr(ticket, 'assigned_to', None)
        if assigned_to != current_assigned:
            old_assigned = current_assigned or "None"
            setattr(ticket, 'assigned_to', assigned_to)
            changes_made.append(f"assigned_to: {old_assigned} -> {assigned_to or 'None'}")
            
            # If assigning to someone and ticket is open, automatically set to in_progress
            current_status = getattr(ticket, 'status', None)
            if assigned_to is not None and current_status == TicketStatus.OPEN.value:
                ticket.update_status(
                    new_status=TicketStatus.IN_PROGRESS.value,
                    changed_by=user_id
                )
                changes_made.append(f"status: {TicketStatus.OPEN.value} -> {TicketStatus.IN_PROGRESS.value} (auto-assigned)")
        
        # Update close_reason if provided and not already set via status update
        if close_reason is not None and close_reason != getattr(ticket, 'close_reason', None):
            old_reason = getattr(ticket, 'close_reason', None) or "None"
            setattr(ticket, 'close_reason', close_reason)
            changes_made.append(f"close_reason: {old_reason} -> {close_reason}")
        
        # Commit the changes
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        logger.info(f"Updated ticket {ticket_id}: {', '.join(changes_made)}")
        return ticket
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to update ticket {ticket_id}: {e}")
        raise


def claim_ticket(db: Session, ticket_id: int, staff_discord_id: int) -> Optional[Ticket]:
    """
    Claim an unassigned ticket for a staff member.
    
    Args:
        db: Database session
        ticket_id: ID of the ticket to claim
        staff_discord_id: Discord ID of the staff member claiming the ticket
        
    Returns:
        Updated ticket object if successful, None if ticket not found
        
    Raises:
        ValueError: If ticket is already assigned or cannot be assigned
        SQLAlchemyError: If database operation fails
    """
    try:
        # Get the ticket
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return None
            
        # Check if ticket can be assigned
        if not ticket.can_be_assigned():
            raise ValueError(f"Ticket {ticket_id} with status '{getattr(ticket, 'status', 'unknown')}' cannot be assigned")
            
        # Check if ticket is already assigned
        current_assigned = getattr(ticket, 'assigned_to', None)
        if current_assigned is not None:
            raise ValueError(f"Ticket {ticket_id} is already assigned to user {current_assigned}")
            
        # Check if user is trying to claim their own ticket
        creator_id = getattr(ticket, 'creator_id', None)
        if creator_id == staff_discord_id:
            raise ValueError("Users cannot claim their own tickets")
            
        # Claim the ticket
        setattr(ticket, 'assigned_to', staff_discord_id)
        setattr(ticket, 'claimed_at', datetime.utcnow())
        
        # Set status to IN_PROGRESS if currently OPEN
        current_status = getattr(ticket, 'status', None)
        if current_status == 'open':
            # Use the ticket's update_status method for validation and logging
            ticket.update_status(
                new_status='in_progress',
                changed_by=staff_discord_id,
                db_session=db
            )
        else:
            # Just commit the assignment changes
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
        
        logger.info(f"Ticket {ticket_id} claimed by staff member {staff_discord_id}")
        return ticket
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to claim ticket {ticket_id}: {e}")
        raise


def unclaim_ticket(db: Session, ticket_id: int, requesting_user_discord_id: int, requesting_user_role: str) -> Optional[Ticket]:
    """
    Unclaim a ticket (remove assignment).
    
    Args:
        db: Database session
        ticket_id: ID of the ticket to unclaim
        requesting_user_discord_id: Discord ID of the user requesting unclaim
        requesting_user_role: Role of the requesting user (ADMIN, STAFF, USER)
        
    Returns:
        Updated ticket object if successful, None if ticket not found
        
    Raises:
        ValueError: If user doesn't have permission to unclaim
        SQLAlchemyError: If database operation fails
    """
    try:
        # Get the ticket
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return None
            
        # Check if ticket is assigned
        current_assigned = getattr(ticket, 'assigned_to', None)
        if current_assigned is None:
            raise ValueError(f"Ticket {ticket_id} is not assigned to anyone")
            
        # Check permissions
        can_unclaim = False
        
        # Staff can unclaim tickets they own
        if requesting_user_role in ['STAFF', 'ADMIN'] and current_assigned == requesting_user_discord_id:
            can_unclaim = True
            
        # Admins can unclaim any ticket
        if requesting_user_role == 'ADMIN':
            can_unclaim = True
            
        if not can_unclaim:
            raise ValueError("Insufficient permissions to unclaim this ticket")
            
        # Unclaim the ticket
        old_assigned_to = current_assigned
        setattr(ticket, 'assigned_to', None)
        setattr(ticket, 'claimed_at', None)
        
        # Commit the changes
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        logger.info(f"Ticket {ticket_id} unclaimed from staff member {old_assigned_to} by {requesting_user_discord_id}")
        return ticket
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to unclaim ticket {ticket_id}: {e}")
        raise


def list_tickets_with_pagination(
    db: Session,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    assigned_to: Optional[int] = None,
    guild_id: Optional[int] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    user_id: Optional[int] = None,
    user_role: Optional[str] = None
) -> Dict[str, Any]:
    """
    List tickets with pagination and filtering.
    
    Args:
        db: Database session
        page: Page number (starts from 1)
        limit: Number of tickets per page
        status: Filter by ticket status
        assigned_to: Filter by assigned staff member
        guild_id: Filter by guild ID
        created_after: Filter tickets created after this date
        created_before: Filter tickets created before this date
        user_id: Current user ID for permission filtering
        user_role: Current user role for permission filtering
    
    Returns:
        Dictionary containing tickets and pagination metadata
    """
    try:
        # Build base query
        query = db.query(Ticket)
        
        # Apply filters
        if status:
            query = query.filter(Ticket.status == status)
        
        if assigned_to:
            query = query.filter(Ticket.assigned_to == assigned_to)
        
        if guild_id:
            query = query.filter(Ticket.guild_id == guild_id)
        
        if created_after:
            query = query.filter(Ticket.created_at >= created_after)
        
        if created_before:
            query = query.filter(Ticket.created_at <= created_before)
        
        # Apply user permission filtering
        # Regular users can only see their own tickets
        if user_role == "USER" and user_id:
            query = query.filter(Ticket.creator_id == user_id)
        
        # For non-admin users, require guild_id filter for security
        if user_role != "ADMIN" and not guild_id:
            raise ValueError("guild_id filter is required for non-admin users")
        
        # Order by created_at descending (newest first)
        query = query.order_by(Ticket.created_at.desc())
        
        # Get total count for pagination
        total_count = query.count()
        
        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_previous = page > 1
        
        # Apply pagination
        offset = (page - 1) * limit
        tickets = query.offset(offset).limit(limit).all()
        
        logger.info(f"Listed {len(tickets)} tickets (page {page}/{total_pages}, total: {total_count})")
        
        return {
            "tickets": tickets,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous
            }
        }
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to list tickets: {e}")
        raise


def get_tickets_count_by_filters(
    db: Session,
    status: Optional[str] = None,
    assigned_to: Optional[int] = None,
    guild_id: Optional[int] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    user_id: Optional[int] = None,
    user_role: Optional[str] = None
) -> int:
    """
    Get count of tickets matching the given filters.
    
    Args:
        db: Database session
        status: Filter by ticket status
        assigned_to: Filter by assigned staff member
        guild_id: Filter by guild ID
        created_after: Filter tickets created after this date
        created_before: Filter tickets created before this date
        user_id: Current user ID for permission filtering
        user_role: Current user role for permission filtering
    
    Returns:
        Count of tickets matching filters
    """
    try:
        # Build query with same filters as list_tickets_with_pagination
        query = db.query(Ticket)
        
        if status:
            query = query.filter(Ticket.status == status)
        
        if assigned_to:
            query = query.filter(Ticket.assigned_to == assigned_to)
        
        if guild_id:
            query = query.filter(Ticket.guild_id == guild_id)
        
        if created_after:
            query = query.filter(Ticket.created_at >= created_after)
        
        if created_before:
            query = query.filter(Ticket.created_at <= created_before)
        
        # Apply user permission filtering
        if user_role == "USER" and user_id:
            query = query.filter(Ticket.creator_id == user_id)
        
        return query.count()
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to count tickets: {e}")
        raise
