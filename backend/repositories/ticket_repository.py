"""Repository for ticket database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import Ticket, TicketStatus
from backend.repositories.base import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    """Repository for ticket-specific database operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize ticket repository."""
        super().__init__(Ticket, session)
    
    async def get_by_discord_channel_id(self, channel_id: int) -> Optional[Ticket]:
        """Get ticket by Discord channel ID.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Ticket instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.discord_channel_id == channel_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_messages(self, ticket_id: UUID) -> Optional[Ticket]:
        """Get ticket with all its messages loaded.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Ticket instance with messages or None if not found
        """
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.messages))
            .where(self.model.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_transcripts(self, ticket_id: UUID) -> Optional[Ticket]:
        """Get ticket with all its transcripts loaded.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Ticket instance with transcripts or None if not found
        """
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.transcripts))
            .where(self.model.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_creator(
        self, 
        creator_discord_id: int,
        status: Optional[TicketStatus] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Ticket]:
        """Get tickets created by a specific user.
        
        Args:
            creator_discord_id: Discord ID of the ticket creator
            status: Optional status filter
            limit: Maximum number of tickets to return
            offset: Number of tickets to skip
            
        Returns:
            List of tickets
        """
        query = select(self.model).where(
            self.model.creator_discord_id == creator_discord_id
        )
        
        if status:
            query = query.where(self.model.status == status.value)
        
        query = query.order_by(self.model.created_at.desc())
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_assigned_staff(
        self,
        staff_discord_id: int,
        status: Optional[TicketStatus] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Ticket]:
        """Get tickets assigned to a specific staff member.
        
        Args:
            staff_discord_id: Discord ID of the assigned staff member
            status: Optional status filter
            limit: Maximum number of tickets to return
            offset: Number of tickets to skip
            
        Returns:
            List of tickets
        """
        query = select(self.model).where(
            self.model.assigned_staff_id == staff_discord_id
        )
        
        if status:
            query = query.where(self.model.status == status.value)
        
        query = query.order_by(self.model.updated_at.desc())
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: TicketStatus,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Ticket]:
        """Get tickets by status.
        
        Args:
            status: Ticket status
            limit: Maximum number of tickets to return
            offset: Number of tickets to skip
            
        Returns:
            List of tickets
        """
        query = select(self.model).where(self.model.status == status.value)
        query = query.order_by(self.model.updated_at.desc())
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_tickets(
        self,
        search_term: Optional[str] = None,
        status: Optional[TicketStatus] = None,
        creator_discord_id: Optional[int] = None,
        assigned_staff_id: Optional[int] = None,
        priority: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Ticket]:
        """Search tickets with multiple filters.
        
        Args:
            search_term: Search in title and description
            status: Ticket status filter
            creator_discord_id: Creator Discord ID filter
            assigned_staff_id: Assigned staff Discord ID filter
            priority: Priority filter
            created_after: Created after date filter
            created_before: Created before date filter
            limit: Maximum number of tickets to return
            offset: Number of tickets to skip
            
        Returns:
            List of matching tickets
        """
        query = select(self.model)
        
        # Text search in title and description
        if search_term:
            search_filter = or_(
                self.model.title.ilike(f"%{search_term}%"),
                self.model.description.ilike(f"%{search_term}%")
            )
            query = query.where(search_filter)
        
        # Status filter
        if status:
            query = query.where(self.model.status == status.value)
        
        # Creator filter
        if creator_discord_id:
            query = query.where(self.model.creator_discord_id == creator_discord_id)
        
        # Assigned staff filter
        if assigned_staff_id:
            query = query.where(self.model.assigned_staff_id == assigned_staff_id)
        
        # Priority filter
        if priority:
            query = query.where(self.model.priority == priority)
        
        # Date range filters
        if created_after:
            query = query.where(self.model.created_at >= created_after)
        
        if created_before:
            query = query.where(self.model.created_at <= created_before)
        
        # Order by most recently updated
        query = query.order_by(self.model.updated_at.desc())
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_ticket_stats(self) -> Dict[str, Any]:
        """Get ticket statistics.
        
        Returns:
            Dictionary with ticket statistics
        """
        # Count tickets by status
        status_counts = {}
        for status in TicketStatus:
            count_result = await self.session.execute(
                select(func.count(self.model.id)).where(
                    self.model.status == status.value
                )
            )
            status_counts[status.value] = count_result.scalar()
        
        # Total tickets
        total_result = await self.session.execute(
            select(func.count(self.model.id))
        )
        total_tickets = total_result.scalar()
        
        # Tickets created today
        today = datetime.now().date()
        today_result = await self.session.execute(
            select(func.count(self.model.id)).where(
                func.date(self.model.created_at) == today
            )
        )
        tickets_today = today_result.scalar()
        
        # Average resolution time for closed tickets
        avg_resolution_result = await self.session.execute(
            select(func.avg(
                func.extract('epoch', self.model.closed_at - self.model.created_at)
            )).where(
                and_(
                    self.model.status == TicketStatus.CLOSED.value,
                    self.model.closed_at.is_not(None)
                )
            )
        )
        avg_resolution_seconds = avg_resolution_result.scalar()
        avg_resolution_hours = avg_resolution_seconds / 3600 if avg_resolution_seconds else None
        
        return {
            "total_tickets": total_tickets,
            "tickets_today": tickets_today,
            "status_counts": status_counts,
            "avg_resolution_hours": avg_resolution_hours
        }
    
    async def close_ticket(self, ticket_id: UUID) -> Optional[Ticket]:
        """Close a ticket and set the closed_at timestamp.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Updated ticket instance or None if not found
        """
        return await self.update(
            ticket_id,
            status=TicketStatus.CLOSED.value,
            closed_at=datetime.utcnow()
        )