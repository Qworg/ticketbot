"""
Ticket participant model for the ticketbot application.
Represents users who have access to a specific ticket.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import Base
import logging

logger = logging.getLogger(__name__)


class TicketParticipant(Base):
    """
    TicketParticipant model representing users with access to tickets.
    
    Attributes:
        id: Unique serial primary key
        ticket_id: ID of the ticket (foreign key)
        user_id: Discord user ID of the participant
        role: Role of the participant ('participant', 'creator', 'staff')
        added_at: Timestamp when user was added to ticket
        removed_at: Timestamp when user was removed (nullable)
    """
    __tablename__ = "ticket_participants"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Foreign key to tickets table
    ticket_id = Column(Integer, ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Discord user ID
    user_id = Column(BigInteger, nullable=False, index=True)
    
    # Role in the ticket
    role = Column(String(50), default='participant', nullable=False)
    
    # Timestamps
    added_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    removed_at = Column(DateTime, nullable=True)
    
    # Ensure unique participant per ticket
    __table_args__ = (
        UniqueConstraint('ticket_id', 'user_id', name='uq_ticket_participant'),
    )
    
    # Relationships
    ticket = relationship("Ticket", back_populates="participants")


def add_participant_to_ticket(
    db: Session, 
    ticket_id: int, 
    user_id: int, 
    role: str = 'participant'
) -> TicketParticipant:
    """
    Add a participant to a ticket.
    
    Args:
        db: Database session
        ticket_id: ID of the ticket
        user_id: Discord user ID to add
        role: Role of the participant (default: 'participant')
        
    Returns:
        TicketParticipant: The created participant record
        
    Raises:
        SQLAlchemyError: If participant already exists or database error
    """
    try:
        # Check if participant already exists
        existing = db.query(TicketParticipant).filter(
            TicketParticipant.ticket_id == ticket_id,
            TicketParticipant.user_id == user_id,
            TicketParticipant.removed_at.is_(None)
        ).first()
        
        if existing:
            raise ValueError(f"User {user_id} is already a participant in ticket {ticket_id}")
        
        # Create new participant
        participant = TicketParticipant(
            ticket_id=ticket_id,
            user_id=user_id,
            role=role
        )
        
        db.add(participant)
        db.commit()
        db.refresh(participant)
        
        logger.info(f"Added participant {user_id} to ticket {ticket_id} with role {role}")
        return participant
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to add participant {user_id} to ticket {ticket_id}: {e}")
        raise


def remove_participant_from_ticket(
    db: Session, 
    ticket_id: int, 
    user_id: int
) -> bool:
    """
    Remove a participant from a ticket (soft delete).
    
    Args:
        db: Database session
        ticket_id: ID of the ticket
        user_id: Discord user ID to remove
        
    Returns:
        bool: True if participant was removed, False if not found
        
    Raises:
        SQLAlchemyError: If database error occurs
    """
    try:
        participant = db.query(TicketParticipant).filter(
            TicketParticipant.ticket_id == ticket_id,
            TicketParticipant.user_id == user_id,
            TicketParticipant.removed_at.is_(None)
        ).first()
        
        if not participant:
            logger.warning(f"Participant {user_id} not found in ticket {ticket_id}")
            return False
        
        # Soft delete by setting removed_at timestamp
        participant.removed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Removed participant {user_id} from ticket {ticket_id}")
        return True
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to remove participant {user_id} from ticket {ticket_id}: {e}")
        raise


def get_ticket_participants(
    db: Session, 
    ticket_id: int,
    active_only: bool = True
) -> List[TicketParticipant]:
    """
    Get all participants for a ticket.
    
    Args:
        db: Database session
        ticket_id: ID of the ticket
        active_only: Only return active participants (not removed)
        
    Returns:
        List[TicketParticipant]: List of participants
    """
    query = db.query(TicketParticipant).filter(
        TicketParticipant.ticket_id == ticket_id
    )
    
    if active_only:
        query = query.filter(TicketParticipant.removed_at.is_(None))
    
    return query.order_by(TicketParticipant.added_at).all()


def is_participant_in_ticket(
    db: Session, 
    ticket_id: int, 
    user_id: int
) -> bool:
    """
    Check if a user is an active participant in a ticket.
    
    Args:
        db: Database session
        ticket_id: ID of the ticket
        user_id: Discord user ID to check
        
    Returns:
        bool: True if user is active participant
    """
    participant = db.query(TicketParticipant).filter(
        TicketParticipant.ticket_id == ticket_id,
        TicketParticipant.user_id == user_id,
        TicketParticipant.removed_at.is_(None)
    ).first()
    
    return participant is not None


def get_participant_role_in_ticket(
    db: Session, 
    ticket_id: int, 
    user_id: int
) -> Optional[str]:
    """
    Get the role of a participant in a ticket.
    
    Args:
        db: Database session
        ticket_id: ID of the ticket
        user_id: Discord user ID
        
    Returns:
        Optional[str]: Role of the participant, None if not found
    """
    participant = db.query(TicketParticipant).filter(
        TicketParticipant.ticket_id == ticket_id,
        TicketParticipant.user_id == user_id,
        TicketParticipant.removed_at.is_(None)
    ).first()
    
    if participant:
        return str(participant.role)
    return None
