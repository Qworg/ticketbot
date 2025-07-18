"""Database models for the Discord Ticket Bot system."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text, 
    UUID, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TicketStatus(str, Enum):
    """Ticket status enumeration."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    CLOSED = "closed"
    ARCHIVED = "archived"


class Priority(str, Enum):
    """Ticket priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(str, Enum):
    """Message type enumeration."""
    USER_MESSAGE = "user_message"
    STAFF_MESSAGE = "staff_message"
    SYSTEM_MESSAGE = "system_message"
    BOT_MESSAGE = "bot_message"


class StaffRole(str, Enum):
    """Staff role enumeration."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"


class Ticket(Base):
    """Ticket model representing a support ticket."""
    
    __tablename__ = "tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discord_channel_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), nullable=False, default=TicketStatus.OPEN.value, index=True)
    priority = Column(String(20), default=Priority.MEDIUM.value, index=True)
    creator_discord_id = Column(BigInteger, nullable=False, index=True)
    assigned_staff_id = Column(BigInteger, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True))
    
    # Relationships
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="ticket", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_tickets_status_created', 'status', 'created_at'),
        Index('idx_tickets_creator_status', 'creator_discord_id', 'status'),
        Index('idx_tickets_assigned_status', 'assigned_staff_id', 'status'),
    )


class Message(Base):
    """Message model representing messages within tickets."""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False, index=True)
    discord_message_id = Column(BigInteger, unique=True, index=True)
    author_discord_id = Column(BigInteger, nullable=False, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default=MessageType.USER_MESSAGE.value, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_messages_ticket_created', 'ticket_id', 'created_at'),
        Index('idx_messages_author_created', 'author_discord_id', 'created_at'),
    )


class Transcript(Base):
    """Transcript model for storing ticket conversation transcripts."""
    
    __tablename__ = "transcripts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    formatted_content = Column(JSON)
    share_token = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="transcripts")


class Staff(Base):
    """Staff model for managing staff members and their permissions."""
    
    __tablename__ = "staff"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discord_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, index=True)
    permissions = Column(JSON, default=dict)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_staff_role_active', 'role', 'active'),
    )