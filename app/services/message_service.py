"""
Message service layer for database operations.

This module provides functions for creating, retrieving, updating, and deleting
message records in the database for the Discord message listener.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.message import Message
from app.models.ticket import get_ticket_by_channel_id
from app.models.guild import get_guild_staff_role_ids, get_guild_admin_role_ids

logger = logging.getLogger(__name__)


def save_discord_message(
    db: Session,
    message_id: int,
    ticket_id: int,
    author_id: int,
    content: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    is_staff_only: bool = False,
    created_at: Optional[datetime] = None
) -> Optional[Message]:
    """
    Save a Discord message to the database.
    
    Args:
        db: Database session
        message_id: Discord message ID (snowflake)
        ticket_id: Ticket ID the message belongs to
        author_id: Discord user ID of the message author
        content: Message text content
        attachments: List of attachment metadata
        is_staff_only: Whether this is a staff-only message
        created_at: Message creation timestamp (defaults to current time)
        
    Returns:
        Message object if successful, None if failed
    """
    try:
        # Check if message already exists (prevent duplicates)
        existing_message = db.query(Message).filter(Message.id == message_id).first()
        if existing_message:
            logger.warning(f"Message {message_id} already exists in database")
            return existing_message
        
        # Create new message record
        message = Message(
            id=message_id,
            ticket_id=ticket_id,
            author_id=author_id,
            content=content,
            attachments=attachments,
            is_staff_only=is_staff_only,
            created_at=created_at or datetime.utcnow(),
            is_deleted=False
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        logger.info(f"Saved message {message_id} to ticket {ticket_id}")
        return message
        
    except SQLAlchemyError as e:
        logger.error(f"Database error saving message {message_id}: {e}")
        db.rollback()
        return None
    except Exception as e:
        logger.error(f"Unexpected error saving message {message_id}: {e}")
        db.rollback()
        return None


def update_message_content(
    db: Session,
    message_id: int,
    new_content: str,
    edited_at: Optional[datetime] = None
) -> bool:
    """
    Update message content when message is edited.
    
    Args:
        db: Database session
        message_id: Discord message ID
        new_content: Updated message content
        edited_at: Edit timestamp (defaults to current time)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            logger.warning(f"Message {message_id} not found for update")
            return False
        
        message.content = new_content
        message.edited_at = edited_at or datetime.utcnow()
        
        db.commit()
        logger.info(f"Updated message {message_id} content")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error updating message {message_id}: {e}")
        db.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating message {message_id}: {e}")
        db.rollback()
        return False


def soft_delete_message(
    db: Session,
    message_id: int
) -> bool:
    """
    Soft delete a message (mark as deleted but preserve content).
    
    Args:
        db: Database session
        message_id: Discord message ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            logger.warning(f"Message {message_id} not found for deletion")
            return False
        
        message.is_deleted = True
        
        db.commit()
        logger.info(f"Soft deleted message {message_id}")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting message {message_id}: {e}")
        db.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting message {message_id}: {e}")
        db.rollback()
        return False


def get_ticket_by_channel(
    db: Session,
    channel_id: int
) -> Optional[Any]:
    """
    Get ticket information by Discord channel ID.
    
    Args:
        db: Database session
        channel_id: Discord channel ID
        
    Returns:
        Ticket object if found, None otherwise
    """
    try:
        return get_ticket_by_channel_id(db, channel_id)
    except Exception as e:
        logger.error(f"Error retrieving ticket for channel {channel_id}: {e}")
        return None


def is_user_staff(
    db: Session,
    user_id: int,
    guild_id: int,
    user_roles: List[int]
) -> bool:
    """
    Check if a user is staff based on their roles in the guild.
    
    Args:
        db: Database session
        user_id: Discord user ID
        guild_id: Discord guild ID
        user_roles: List of role IDs the user has
        
    Returns:
        True if user is staff, False otherwise
    """
    try:
        # Get staff role IDs for the guild
        staff_role_ids = get_guild_staff_role_ids(db, guild_id)
        admin_role_ids = get_guild_admin_role_ids(db, guild_id)
        
        # Combine staff and admin role IDs
        all_staff_roles = set(staff_role_ids + admin_role_ids)
        
        # Check if user has any staff roles
        user_role_set = set(user_roles)
        is_staff = bool(user_role_set.intersection(all_staff_roles))
        
        logger.debug(f"User {user_id} staff check: {is_staff}")
        return is_staff
        
    except Exception as e:
        logger.error(f"Error checking staff status for user {user_id}: {e}")
        return False


def extract_attachment_metadata(attachments) -> List[Dict[str, Any]]:
    """
    Extract attachment metadata from Discord attachment objects.
    
    Args:
        attachments: Discord attachment objects from interactions.py
        
    Returns:
        List of attachment metadata dictionaries
    """
    attachment_list = []
    
    try:
        for attachment in attachments:
            attachment_data = {
                "filename": attachment.filename,
                "size": attachment.size,
                "content_type": attachment.content_type,
                "url": attachment.url,
                "proxy_url": getattr(attachment, 'proxy_url', None),
                "width": getattr(attachment, 'width', None),
                "height": getattr(attachment, 'height', None),
            }
            attachment_list.append(attachment_data)
            
    except Exception as e:
        logger.error(f"Error extracting attachment metadata: {e}")
    
    return attachment_list


def get_message_by_id(
    db: Session,
    message_id: int
) -> Optional[Message]:
    """
    Get a message by its Discord message ID.
    
    Args:
        db: Database session
        message_id: Discord message ID
        
    Returns:
        Message object if found, None otherwise
    """
    try:
        return db.query(Message).filter(Message.id == message_id).first()
    except Exception as e:
        logger.error(f"Error retrieving message {message_id}: {e}")
        return None


def get_ticket_messages(
    db: Session,
    ticket_id: int,
    include_staff_only: bool = False,
    include_deleted: bool = False,
    limit: Optional[int] = None
) -> List[Message]:
    """
    Get messages for a ticket with filtering options.
    
    Args:
        db: Database session
        ticket_id: Ticket ID
        include_staff_only: Whether to include staff-only messages
        include_deleted: Whether to include deleted messages
        limit: Maximum number of messages to return
        
    Returns:
        List of Message objects
    """
    try:
        query = db.query(Message).filter(Message.ticket_id == ticket_id)
        
        if not include_staff_only:
            query = query.filter(Message.is_staff_only == False)
        
        if not include_deleted:
            query = query.filter(Message.is_deleted == False)
        
        query = query.order_by(Message.created_at)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
        
    except Exception as e:
        logger.error(f"Error retrieving messages for ticket {ticket_id}: {e}")
        return []
