"""Ticket service containing business logic for ticket operations.

This service implements the core business logic for ticket lifecycle management,
including creation, updates, assignment, status transitions, and archiving.
It enforces business rules and validation for all ticket operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from backend.database_service import DatabaseService
from backend.models import Ticket, TicketStatus, Priority, Message, MessageType
from backend.schemas import TicketCreate, TicketUpdate

# Configure logger
logger = logging.getLogger(__name__)


class TicketService:
    """Service class for ticket business logic operations.
    
    This service implements the core business logic for ticket lifecycle management,
    including creation, updates, assignment, status transitions, and archiving.
    It enforces business rules and validation for all ticket operations.
    """
    
    def __init__(self, db_service: DatabaseService):
        """Initialize ticket service with database service.
        
        Args:
            db_service: Database service instance
        """
        self.db = db_service
        self.status_change_handlers = {
            TicketStatus.OPEN.value: self._handle_open_status,
            TicketStatus.IN_PROGRESS.value: self._handle_in_progress_status,
            TicketStatus.WAITING.value: self._handle_waiting_status,
            TicketStatus.CLOSED.value: self._handle_closed_status,
            TicketStatus.ARCHIVED.value: self._handle_archived_status
        }
    
    async def create_ticket(
        self, 
        ticket_data: TicketCreate,
        creator_discord_id: int
    ) -> Ticket:
        """Create a new ticket with business logic validation.
        
        Args:
            ticket_data: Ticket creation data
            creator_discord_id: Discord ID of the ticket creator
            
        Returns:
            Created ticket instance
            
        Raises:
            ValueError: If validation fails
        """
        # Validate that the Discord channel ID is not already in use
        existing_ticket = await self.db.tickets.get_by_discord_channel_id(
            ticket_data.discord_channel_id
        )
        if existing_ticket:
            raise ValueError(
                f"Ticket already exists for Discord channel {ticket_data.discord_channel_id}"
            )
        
        # Create the ticket
        ticket = await self.db.tickets.create(
            discord_channel_id=ticket_data.discord_channel_id,
            title=ticket_data.title,
            description=ticket_data.description,
            priority=ticket_data.priority or Priority.MEDIUM.value,
            creator_discord_id=creator_discord_id,
            status=TicketStatus.OPEN.value
        )
        
        await self.db.commit()
        return ticket
    
    async def get_ticket(self, ticket_id: UUID) -> Optional[Ticket]:
        """Get a ticket by ID.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Ticket instance or None if not found
        """
        return await self.db.tickets.get_by_id(ticket_id)
    
    async def get_ticket_by_channel(self, discord_channel_id: int) -> Optional[Ticket]:
        """Get a ticket by Discord channel ID.
        
        Args:
            discord_channel_id: Discord channel ID
            
        Returns:
            Ticket instance or None if not found
        """
        return await self.db.tickets.get_by_discord_channel_id(discord_channel_id)
    
    async def update_ticket(
        self, 
        ticket_id: UUID, 
        ticket_data: TicketUpdate,
        updated_by_discord_id: int
    ) -> Optional[Ticket]:
        """Update a ticket with business logic validation.
        
        Args:
            ticket_id: Ticket UUID
            ticket_data: Ticket update data
            updated_by_discord_id: Discord ID of the user making the update
            
        Returns:
            Updated ticket instance or None if not found
            
        Raises:
            ValueError: If validation fails
        """
        # Get the existing ticket
        ticket = await self.db.tickets.get_by_id(ticket_id)
        if not ticket:
            return None
        
        # Validate status transitions
        if ticket_data.status and ticket_data.status != ticket.status:
            if not self._is_valid_status_transition(ticket.status, ticket_data.status):
                raise ValueError(
                    f"Invalid status transition from {ticket.status} to {ticket_data.status}"
                )
        
        # Validate staff assignment
        if ticket_data.assigned_staff_id is not None:
            if ticket_data.assigned_staff_id != 0:  # 0 means unassign
                staff_exists = await self.db.staff.is_staff_member(ticket_data.assigned_staff_id)
                if not staff_exists:
                    raise ValueError(
                        f"Staff member {ticket_data.assigned_staff_id} does not exist or is not active"
                    )
        
        # Prepare update data
        update_data = {}
        if ticket_data.title is not None:
            update_data['title'] = ticket_data.title
        if ticket_data.description is not None:
            update_data['description'] = ticket_data.description
        if ticket_data.status is not None:
            update_data['status'] = ticket_data.status
        if ticket_data.priority is not None:
            update_data['priority'] = ticket_data.priority
        if hasattr(ticket_data, 'assigned_staff_id') and ticket_data.assigned_staff_id is not None:
            if ticket_data.assigned_staff_id == 0:
                update_data['assigned_staff_id'] = None
            else:
                update_data['assigned_staff_id'] = ticket_data.assigned_staff_id
        
        # Update the ticket
        updated_ticket = await self.db.tickets.update(ticket_id, **update_data)
        await self.db.commit()
        
        return updated_ticket
    
    async def assign_ticket(
        self, 
        ticket_id: UUID, 
        staff_discord_id: int,
        assigned_by_discord_id: int
    ) -> Optional[Ticket]:
        """Assign a ticket to a staff member.
        
        Args:
            ticket_id: Ticket UUID
            staff_discord_id: Discord ID of the staff member to assign
            assigned_by_discord_id: Discord ID of the user making the assignment
            
        Returns:
            Updated ticket instance or None if not found
            
        Raises:
            ValueError: If validation fails
        """
        # Validate that the staff member exists and is active
        staff_exists = await self.db.staff.is_staff_member(staff_discord_id)
        if not staff_exists:
            raise ValueError(
                f"Staff member {staff_discord_id} does not exist or is not active"
            )
        
        # Update the ticket assignment
        updated_ticket = await self.db.tickets.update(
            ticket_id,
            assigned_staff_id=staff_discord_id,
            status=TicketStatus.IN_PROGRESS.value
        )
        
        if updated_ticket:
            await self.db.commit()
        
        return updated_ticket
    
    async def unassign_ticket(
        self, 
        ticket_id: UUID,
        unassigned_by_discord_id: int
    ) -> Optional[Ticket]:
        """Unassign a ticket from its current staff member.
        
        Args:
            ticket_id: Ticket UUID
            unassigned_by_discord_id: Discord ID of the user making the unassignment
            
        Returns:
            Updated ticket instance or None if not found
        """
        updated_ticket = await self.db.tickets.update(
            ticket_id,
            assigned_staff_id=None,
            status=TicketStatus.OPEN.value
        )
        
        if updated_ticket:
            await self.db.commit()
        
        return updated_ticket
    
    async def close_ticket(
        self, 
        ticket_id: UUID,
        closed_by_discord_id: int
    ) -> Optional[Ticket]:
        """Close a ticket with proper lifecycle management.
        
        Args:
            ticket_id: Ticket UUID
            closed_by_discord_id: Discord ID of the user closing the ticket
            
        Returns:
            Closed ticket instance or None if not found
            
        Raises:
            ValueError: If ticket cannot be closed
        """
        # Get the existing ticket
        ticket = await self.db.tickets.get_by_id(ticket_id)
        if not ticket:
            return None
        
        # Validate that the ticket can be closed
        if ticket.status == TicketStatus.CLOSED.value:
            raise ValueError("Ticket is already closed")
        
        if ticket.status == TicketStatus.ARCHIVED.value:
            raise ValueError("Cannot close an archived ticket")
        
        # Close the ticket
        closed_ticket = await self.db.tickets.close_ticket(ticket_id)
        
        if closed_ticket:
            await self.db.commit()
        
        return closed_ticket
    
    async def reopen_ticket(
        self, 
        ticket_id: UUID,
        reopened_by_discord_id: int
    ) -> Optional[Ticket]:
        """Reopen a closed ticket.
        
        Args:
            ticket_id: Ticket UUID
            reopened_by_discord_id: Discord ID of the user reopening the ticket
            
        Returns:
            Reopened ticket instance or None if not found
            
        Raises:
            ValueError: If ticket cannot be reopened
        """
        # Get the existing ticket
        ticket = await self.db.tickets.get_by_id(ticket_id)
        if not ticket:
            return None
        
        # Validate that the ticket can be reopened
        if ticket.status != TicketStatus.CLOSED.value:
            raise ValueError("Only closed tickets can be reopened")
        
        # Reopen the ticket
        updated_ticket = await self.db.tickets.update(
            ticket_id,
            status=TicketStatus.OPEN.value,
            closed_at=None
        )
        
        if updated_ticket:
            await self.db.commit()
        
        return updated_ticket
    
    async def archive_ticket(
        self, 
        ticket_id: UUID,
        archived_by_discord_id: int
    ) -> Optional[Ticket]:
        """Archive a ticket.
        
        Args:
            ticket_id: Ticket UUID
            archived_by_discord_id: Discord ID of the user archiving the ticket
            
        Returns:
            Archived ticket instance or None if not found
            
        Raises:
            ValueError: If ticket cannot be archived
        """
        # Get the existing ticket
        ticket = await self.db.tickets.get_by_id(ticket_id)
        if not ticket:
            return None
        
        # Validate that the ticket can be archived
        if ticket.status != TicketStatus.CLOSED.value:
            raise ValueError("Only closed tickets can be archived")
        
        # Archive the ticket
        updated_ticket = await self.db.tickets.update(
            ticket_id,
            status=TicketStatus.ARCHIVED.value
        )
        
        if updated_ticket:
            await self.db.commit()
        
        return updated_ticket
    
    async def get_user_tickets(
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
        return await self.db.tickets.get_by_creator(
            creator_discord_id, status, limit, offset
        )
    
    async def get_staff_tickets(
        self, 
        staff_discord_id: int,
        status: Optional[TicketStatus] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Ticket]:
        """Get tickets assigned to a specific staff member.
        
        Args:
            staff_discord_id: Discord ID of the staff member
            status: Optional status filter
            limit: Maximum number of tickets to return
            offset: Number of tickets to skip
            
        Returns:
            List of tickets
        """
        return await self.db.tickets.get_by_assigned_staff(
            staff_discord_id, status, limit, offset
        )
    
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
        return await self.db.tickets.search_tickets(
            search_term=search_term,
            status=status,
            creator_discord_id=creator_discord_id,
            assigned_staff_id=assigned_staff_id,
            priority=priority,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset
        )
    
    async def get_ticket_statistics(self) -> Dict[str, Any]:
        """Get comprehensive ticket statistics.
        
        Returns:
            Dictionary with ticket statistics
        """
        return await self.db.tickets.get_ticket_stats()
    
    async def add_ticket_message(
        self,
        ticket_id: UUID,
        author_discord_id: int,
        content: str,
        message_type: MessageType = MessageType.USER_MESSAGE,
        discord_message_id: Optional[int] = None
    ) -> Message:
        """Add a message to a ticket.
        
        Args:
            ticket_id: Ticket UUID
            author_discord_id: Discord ID of the message author
            content: Message content
            message_type: Type of message
            discord_message_id: Optional Discord message ID
            
        Returns:
            Created message instance
            
        Raises:
            ValueError: If the ticket does not exist
        """
        # Verify the ticket exists
        ticket = await self.db.tickets.get_by_id(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket with ID {ticket_id} does not exist")
        
        # Create the message
        message = await self.db.messages.create(
            ticket_id=ticket_id,
            author_discord_id=author_discord_id,
            content=content,
            message_type=message_type.value,
            discord_message_id=discord_message_id
        )
        
        # Update ticket's updated_at timestamp
        await self.db.tickets.update(ticket_id)
        
        await self.db.commit()
        return message
    
    async def add_system_message(
        self,
        ticket_id: UUID,
        content: str,
        discord_message_id: Optional[int] = None
    ) -> Message:
        """Add a system message to a ticket.
        
        Args:
            ticket_id: Ticket UUID
            content: Message content
            discord_message_id: Optional Discord message ID
            
        Returns:
            Created message instance
        """
        return await self.add_ticket_message(
            ticket_id=ticket_id,
            author_discord_id=0,  # System messages use 0 as author ID
            content=content,
            message_type=MessageType.SYSTEM_MESSAGE,
            discord_message_id=discord_message_id
        )
    
    async def get_ticket_messages(
        self,
        ticket_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        newest_first: bool = False
    ) -> List[Message]:
        """Get messages for a specific ticket.
        
        Args:
            ticket_id: Ticket UUID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            newest_first: If True, return newest messages first
            
        Returns:
            List of messages
            
        Raises:
            ValueError: If the ticket does not exist
        """
        # Verify the ticket exists
        ticket = await self.db.tickets.get_by_id(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket with ID {ticket_id} does not exist")
        
        return await self.db.messages.get_by_ticket_id(
            ticket_id=ticket_id,
            limit=limit,
            offset=offset,
            order_desc=newest_first
        )
    
    async def get_ticket_with_messages(self, ticket_id: UUID) -> Optional[Tuple[Ticket, List[Message]]]:
        """Get a ticket with all its messages.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Tuple of (ticket, messages) or None if ticket not found
        """
        ticket = await self.db.tickets.get_by_id(ticket_id)
        if not ticket:
            return None
        
        messages = await self.db.messages.get_by_ticket_id(ticket_id)
        return ticket, messages
    
    async def change_ticket_status(
        self,
        ticket_id: UUID,
        new_status: TicketStatus,
        changed_by_discord_id: int,
        reason: Optional[str] = None
    ) -> Optional[Ticket]:
        """Change a ticket's status with proper lifecycle management.
        
        Args:
            ticket_id: Ticket UUID
            new_status: New ticket status
            changed_by_discord_id: Discord ID of the user changing the status
            reason: Optional reason for the status change
            
        Returns:
            Updated ticket instance or None if not found
            
        Raises:
            ValueError: If the status transition is invalid
        """
        # Get the existing ticket
        ticket = await self.db.tickets.get_by_id(ticket_id)
        if not ticket:
            return None
        
        # Validate the status transition
        if not self._is_valid_status_transition(ticket.status, new_status.value):
            raise ValueError(
                f"Invalid status transition from {ticket.status} to {new_status.value}"
            )
        
        # Update the ticket status
        update_data = {"status": new_status.value}
        
        # Add closed_at timestamp if closing the ticket
        if new_status == TicketStatus.CLOSED and ticket.status != TicketStatus.CLOSED.value:
            update_data["closed_at"] = datetime.utcnow()
        
        # Clear closed_at timestamp if reopening the ticket
        if ticket.status == TicketStatus.CLOSED.value and new_status == TicketStatus.OPEN:
            update_data["closed_at"] = None
        
        # Update the ticket
        updated_ticket = await self.db.tickets.update(ticket_id, **update_data)
        
        if updated_ticket:
            # Add a system message about the status change
            status_message = f"Ticket status changed from {ticket.status} to {new_status.value}"
            if reason:
                status_message += f" - Reason: {reason}"
            
            await self.add_system_message(ticket_id, status_message)
            
            # Execute status-specific handler if available
            if new_status.value in self.status_change_handlers:
                await self.status_change_handlers[new_status.value](
                    updated_ticket, changed_by_discord_id
                )
            
            await self.db.commit()
        
        return updated_ticket
    
    async def _handle_open_status(self, ticket: Ticket, changed_by_discord_id: int) -> None:
        """Handle actions when a ticket is set to open status.
        
        Args:
            ticket: The ticket that was updated
            changed_by_discord_id: Discord ID of the user who changed the status
        """
        # If the ticket was reopened, clear assignment
        if ticket.assigned_staff_id is not None:
            await self.db.tickets.update(ticket.id, assigned_staff_id=None)
    
    async def _handle_in_progress_status(self, ticket: Ticket, changed_by_discord_id: int) -> None:
        """Handle actions when a ticket is set to in-progress status.
        
        Args:
            ticket: The ticket that was updated
            changed_by_discord_id: Discord ID of the user who changed the status
        """
        # If no staff is assigned, assign to the user who changed the status
        if ticket.assigned_staff_id is None:
            # Check if the user is a staff member
            is_staff = await self.db.staff.is_staff_member(changed_by_discord_id)
            if is_staff:
                await self.db.tickets.update(ticket.id, assigned_staff_id=changed_by_discord_id)
                await self.add_system_message(
                    ticket.id, 
                    f"Ticket automatically assigned to staff member <@{changed_by_discord_id}>"
                )
    
    async def _handle_waiting_status(self, ticket: Ticket, changed_by_discord_id: int) -> None:
        """Handle actions when a ticket is set to waiting status.
        
        Args:
            ticket: The ticket that was updated
            changed_by_discord_id: Discord ID of the user who changed the status
        """
        # No special actions needed for waiting status
        pass
    
    async def _handle_closed_status(self, ticket: Ticket, changed_by_discord_id: int) -> None:
        """Handle actions when a ticket is set to closed status.
        
        Args:
            ticket: The ticket that was updated
            changed_by_discord_id: Discord ID of the user who changed the status
        """
        # Generate a transcript when a ticket is closed
        from backend.services.transcript_service import TranscriptService
        transcript_service = TranscriptService(self.db)
        
        try:
            # Check if a transcript already exists
            existing_transcript = await self.db.transcripts.get_by_ticket_id(ticket.id)
            
            if not existing_transcript:
                # Generate a new transcript
                await transcript_service.generate_transcript(ticket.id)
                await self.add_system_message(
                    ticket.id, 
                    "Ticket closed. A transcript has been generated."
                )
            else:
                # Update existing transcript
                await transcript_service.update_transcript(ticket.id)
                await self.add_system_message(
                    ticket.id, 
                    "Ticket closed. The transcript has been updated."
                )
        except Exception as e:
            logger.error(f"Failed to generate transcript for ticket {ticket.id}: {str(e)}")
            await self.add_system_message(
                ticket.id, 
                "Ticket closed. Failed to generate transcript."
            )
    
    async def _handle_archived_status(self, ticket: Ticket, changed_by_discord_id: int) -> None:
        """Handle actions when a ticket is set to archived status.
        
        Args:
            ticket: The ticket that was updated
            changed_by_discord_id: Discord ID of the user who changed the status
        """
        # No special actions needed for archived status
        pass
    
    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """Validate if a status transition is allowed.
        
        Args:
            current_status: Current ticket status
            new_status: Desired new status
            
        Returns:
            True if transition is valid, False otherwise
        """
        # Define valid status transitions
        valid_transitions = {
            TicketStatus.OPEN.value: [
                TicketStatus.IN_PROGRESS.value,
                TicketStatus.WAITING.value,
                TicketStatus.CLOSED.value
            ],
            TicketStatus.IN_PROGRESS.value: [
                TicketStatus.OPEN.value,
                TicketStatus.WAITING.value,
                TicketStatus.CLOSED.value
            ],
            TicketStatus.WAITING.value: [
                TicketStatus.OPEN.value,
                TicketStatus.IN_PROGRESS.value,
                TicketStatus.CLOSED.value
            ],
            TicketStatus.CLOSED.value: [
                TicketStatus.OPEN.value,  # Reopen
                TicketStatus.ARCHIVED.value
            ],
            TicketStatus.ARCHIVED.value: []  # No transitions from archived
        }
        
        return new_status in valid_transitions.get(current_status, [])