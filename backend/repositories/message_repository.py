"""Repository for message database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Message, MessageType
from backend.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for message-specific database operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize message repository."""
        super().__init__(Message, session)
    
    async def get_by_discord_message_id(self, discord_message_id: int) -> Optional[Message]:
        """Get message by Discord message ID.
        
        Args:
            discord_message_id: Discord message ID
            
        Returns:
            Message instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(
                self.model.discord_message_id == discord_message_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_ticket_id(
        self,
        ticket_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_desc: bool = False
    ) -> List[Message]:
        """Get messages for a specific ticket.
        
        Args:
            ticket_id: Ticket UUID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            order_desc: If True, order by created_at descending
            
        Returns:
            List of messages
        """
        query = select(self.model).where(self.model.ticket_id == ticket_id)
        
        if order_desc:
            query = query.order_by(desc(self.model.created_at))
        else:
            query = query.order_by(self.model.created_at)
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_author(
        self,
        author_discord_id: int,
        ticket_id: Optional[UUID] = None,
        message_type: Optional[MessageType] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Message]:
        """Get messages by author.
        
        Args:
            author_discord_id: Discord ID of the message author
            ticket_id: Optional ticket ID filter
            message_type: Optional message type filter
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of messages
        """
        query = select(self.model).where(
            self.model.author_discord_id == author_discord_id
        )
        
        if ticket_id:
            query = query.where(self.model.ticket_id == ticket_id)
        
        if message_type:
            query = query.where(self.model.message_type == message_type.value)
        
        query = query.order_by(desc(self.model.created_at))
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_type(
        self,
        message_type: MessageType,
        ticket_id: Optional[UUID] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Message]:
        """Get messages by type.
        
        Args:
            message_type: Message type
            ticket_id: Optional ticket ID filter
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of messages
        """
        query = select(self.model).where(
            self.model.message_type == message_type.value
        )
        
        if ticket_id:
            query = query.where(self.model.ticket_id == ticket_id)
        
        query = query.order_by(desc(self.model.created_at))
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_messages(
        self,
        search_term: str,
        ticket_id: Optional[UUID] = None,
        author_discord_id: Optional[int] = None,
        message_type: Optional[MessageType] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Message]:
        """Search messages by content and other filters.
        
        Args:
            search_term: Search term for message content
            ticket_id: Optional ticket ID filter
            author_discord_id: Optional author Discord ID filter
            message_type: Optional message type filter
            created_after: Optional created after date filter
            created_before: Optional created before date filter
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of matching messages
        """
        query = select(self.model).where(
            self.model.content.ilike(f"%{search_term}%")
        )
        
        if ticket_id:
            query = query.where(self.model.ticket_id == ticket_id)
        
        if author_discord_id:
            query = query.where(self.model.author_discord_id == author_discord_id)
        
        if message_type:
            query = query.where(self.model.message_type == message_type.value)
        
        if created_after:
            query = query.where(self.model.created_at >= created_after)
        
        if created_before:
            query = query.where(self.model.created_at <= created_before)
        
        query = query.order_by(desc(self.model.created_at))
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_message_count_by_ticket(self, ticket_id: UUID) -> int:
        """Get the number of messages in a ticket.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Number of messages in the ticket
        """
        result = await self.session.execute(
            select(func.count(self.model.id)).where(
                self.model.ticket_id == ticket_id
            )
        )
        return result.scalar()
    
    async def get_latest_message_by_ticket(self, ticket_id: UUID) -> Optional[Message]:
        """Get the latest message in a ticket.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Latest message or None if no messages exist
        """
        result = await self.session.execute(
            select(self.model)
            .where(self.model.ticket_id == ticket_id)
            .order_by(desc(self.model.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_message_stats_by_ticket(self, ticket_id: UUID) -> Dict[str, Any]:
        """Get message statistics for a ticket.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Dictionary with message statistics
        """
        # Total message count
        total_result = await self.session.execute(
            select(func.count(self.model.id)).where(
                self.model.ticket_id == ticket_id
            )
        )
        total_messages = total_result.scalar()
        
        # Count by message type
        type_counts = {}
        for msg_type in MessageType:
            count_result = await self.session.execute(
                select(func.count(self.model.id)).where(
                    self.model.ticket_id == ticket_id,
                    self.model.message_type == msg_type.value
                )
            )
            type_counts[msg_type.value] = count_result.scalar()
        
        # Unique authors count
        authors_result = await self.session.execute(
            select(func.count(func.distinct(self.model.author_discord_id))).where(
                self.model.ticket_id == ticket_id
            )
        )
        unique_authors = authors_result.scalar()
        
        # First and last message timestamps
        first_message_result = await self.session.execute(
            select(self.model.created_at)
            .where(self.model.ticket_id == ticket_id)
            .order_by(self.model.created_at)
            .limit(1)
        )
        first_message_time = first_message_result.scalar()
        
        last_message_result = await self.session.execute(
            select(self.model.created_at)
            .where(self.model.ticket_id == ticket_id)
            .order_by(desc(self.model.created_at))
            .limit(1)
        )
        last_message_time = last_message_result.scalar()
        
        return {
            "total_messages": total_messages,
            "type_counts": type_counts,
            "unique_authors": unique_authors,
            "first_message_time": first_message_time,
            "last_message_time": last_message_time
        }
    
    async def delete_by_ticket_id(self, ticket_id: UUID) -> int:
        """Delete all messages for a ticket.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Number of messages deleted
        """
        from sqlalchemy import delete
        
        result = await self.session.execute(
            delete(self.model).where(self.model.ticket_id == ticket_id)
        )
        return result.rowcount