"""
Message model for storing Discord messages in ticket channels.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, BigInteger, Integer, Text, TIMESTAMP, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Message(Base):
    """
    Message model representing Discord messages in ticket channels.
    
    Attributes:
        id (int): Discord message ID (PRIMARY KEY)
        ticket_id (int): Foreign key to tickets table
        author_id (int): Discord user ID of message author
        content (str): Message content text
        attachments (dict): JSON metadata for file attachments
        is_staff_only (bool): Whether message is visible only to staff
        created_at (datetime): When message was created
        edited_at (datetime): When message was last edited (nullable)
        is_deleted (bool): Whether message is soft deleted
    """
    
    __tablename__ = "messages"
    
    # Primary key using Discord message ID
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Foreign key to tickets table
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Discord user ID of message author
    author_id = Column(BigInteger, nullable=False, index=True)
    
    # Message content
    content = Column(Text, nullable=False)
    
    # JSON metadata for file attachments
    attachments = Column(JSON, nullable=True)
    
    # Staff-only message flag
    is_staff_only = Column(Boolean, default=False, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    edited_at = Column(TIMESTAMP, nullable=True)
    
    # Soft deletion flag
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Relationship to ticket
    ticket = relationship("Ticket", back_populates="messages")
    
    # Create composite indexes for efficient querying
    __table_args__ = (
        Index("ix_messages_ticket_created", "ticket_id", "created_at"),
        Index("ix_messages_ticket_staff_only", "ticket_id", "is_staff_only"),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, ticket_id={self.ticket_id}, author_id={self.author_id}, is_staff_only={self.is_staff_only})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for API responses."""
        return {
            "id": str(self.id),
            "ticket_id": self.ticket_id,
            "author_id": str(self.author_id),
            "content": self.content,
            "attachments": self.attachments,
            "is_staff_only": self.is_staff_only,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "edited_at": self.edited_at.isoformat() if self.edited_at is not None else None,
            "is_deleted": self.is_deleted,
        }
