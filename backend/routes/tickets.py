"""API routes for ticket management."""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Response
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from backend.database_service import DatabaseService, get_db_service
from backend.models import TicketStatus, Priority, MessageType
from backend.schemas import (
    Ticket, TicketCreate, TicketUpdate, TicketPagination,
    TicketWithMessages, ErrorResponse, Message, MessageCreate
)

router = APIRouter(
    prefix="/api/tickets",
    tags=["tickets"],
    responses={
        http_status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        http_status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        http_status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    }
)


@router.post(
    "",
    response_model=Ticket,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a new ticket",
    description="Creates a new support ticket in the system."
)
async def create_ticket(
    ticket_data: TicketCreate,
    db: DatabaseService = Depends(get_db_service)
) -> Ticket:
    """Create a new ticket.
    
    Args:
        ticket_data: Ticket creation data
        db: Database service dependency
        
    Returns:
        Created ticket
        
    Raises:
        HTTPException: If ticket creation fails
    """
    try:
        # Check if a ticket with the same Discord channel ID already exists
        existing_ticket = await db.tickets.get_by_discord_channel_id(
            ticket_data.discord_channel_id
        )
        if existing_ticket:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"Ticket with Discord channel ID {ticket_data.discord_channel_id} already exists"
            )
        
        # Create the ticket
        ticket = await db.tickets.create(
            discord_channel_id=ticket_data.discord_channel_id,
            title=ticket_data.title,
            description=ticket_data.description,
            priority=ticket_data.priority,
            creator_discord_id=ticket_data.creator_discord_id
        )
        
        return ticket
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {str(e)}"
        )


@router.get(
    "",
    response_model=TicketPagination,
    summary="Get tickets with filtering and pagination",
    description="Retrieves a paginated list of tickets with optional filtering."
)
async def get_tickets(
    search: Optional[str] = Query(None, description="Search term for ticket title and description"),
    status: Optional[TicketStatus] = Query(None, description="Filter by ticket status"),
    priority: Optional[Priority] = Query(None, description="Filter by ticket priority"),
    creator_id: Optional[int] = Query(None, description="Filter by creator's Discord ID"),
    assigned_id: Optional[int] = Query(None, description="Filter by assigned staff's Discord ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: DatabaseService = Depends(get_db_service)
) -> TicketPagination:
    """Get tickets with filtering and pagination.
    
    Args:
        search: Optional search term for ticket title and description
        status: Optional filter by ticket status
        priority: Optional filter by ticket priority
        creator_id: Optional filter by creator's Discord ID
        assigned_id: Optional filter by assigned staff's Discord ID
        page: Page number (1-indexed)
        size: Items per page
        db: Database service dependency
        
    Returns:
        Paginated list of tickets
        
    Raises:
        HTTPException: If retrieving tickets fails
    """
    try:
        # Calculate offset for pagination
        offset = (page - 1) * size
        
        # Get tickets with filters
        tickets = await db.tickets.search_tickets(
            search_term=search,
            status=status,
            creator_discord_id=creator_id,
            assigned_staff_id=assigned_id,
            priority=priority.value if priority else None,
            limit=size,
            offset=offset
        )
        
        # Get total count for pagination
        total_count = await db.tickets.count(
            status=status.value if status else None,
            priority=priority.value if priority else None,
            creator_discord_id=creator_id,
            assigned_staff_id=assigned_id
        )
        
        # Calculate total pages
        total_pages = (total_count + size - 1) // size if total_count > 0 else 1
        
        return TicketPagination(
            items=tickets,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )
    except Exception as e:
        from fastapi import status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tickets: {str(e)}"
        )


@router.get(
    "/{ticket_id}",
    response_model=TicketWithMessages,
    summary="Get ticket details",
    description="Retrieves detailed information about a specific ticket including messages."
)
async def get_ticket(
    ticket_id: UUID = Path(..., description="Ticket UUID"),
    db: DatabaseService = Depends(get_db_service)
) -> TicketWithMessages:
    """Get detailed information about a specific ticket.
    
    Args:
        ticket_id: Ticket UUID
        db: Database service dependency
        
    Returns:
        Ticket with messages
        
    Raises:
        HTTPException: If ticket is not found
    """
    try:
        # Get ticket with messages
        ticket = await db.tickets.get_with_messages(ticket_id)
        
        if not ticket:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        
        return ticket
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ticket: {str(e)}"
        )
@router.put(
    "/{ticket_id}",
    response_model=Ticket,
    summary="Update ticket details",
    description="Updates an existing ticket with new information."
)
async def update_ticket(
    ticket_data: TicketUpdate,
    ticket_id: UUID = Path(..., description="Ticket UUID"),
    db: DatabaseService = Depends(get_db_service)
) -> Ticket:
    """Update an existing ticket.
    
    Args:
        ticket_data: Ticket update data
        ticket_id: Ticket UUID
        db: Database service dependency
        
    Returns:
        Updated ticket
        
    Raises:
        HTTPException: If ticket is not found or update fails
    """
    try:
        # Check if ticket exists
        existing_ticket = await db.tickets.get_by_id(ticket_id)
        if not existing_ticket:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        
        # Prepare update data
        update_data = ticket_data.model_dump(exclude_unset=True)
        
        # Update the ticket
        updated_ticket = await db.tickets.update(
            ticket_id,
            **update_data
        )
        
        return updated_ticket
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ticket: {str(e)}"
        )


@router.delete(
    "/{ticket_id}",
    status_code=http_status.HTTP_200_OK,
    response_model=Ticket,
    summary="Close a ticket",
    description="Closes a ticket by setting its status to CLOSED and recording the closure time."
)
async def close_ticket(
    ticket_id: UUID = Path(..., description="Ticket UUID"),
    db: DatabaseService = Depends(get_db_service)
) -> Ticket:
    """Close a ticket.
    
    Args:
        ticket_id: Ticket UUID
        db: Database service dependency
        
    Returns:
        Closed ticket
        
    Raises:
        HTTPException: If ticket is not found or closure fails
    """
    try:
        # Check if ticket exists
        existing_ticket = await db.tickets.get_by_id(ticket_id)
        if not existing_ticket:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        
        # Check if ticket is already closed
        if existing_ticket.status == TicketStatus.CLOSED.value:
            return existing_ticket
        
        # Close the ticket
        closed_ticket = await db.tickets.close_ticket(ticket_id)
        
        return closed_ticket
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close ticket: {str(e)}"
        )


@router.post(
    "/{ticket_id}/messages",
    status_code=http_status.HTTP_201_CREATED,
    response_model=Message,
    summary="Add message to ticket",
    description="Adds a new message to an existing ticket."
)
async def add_message(
    message_data: MessageCreate,
    ticket_id: UUID = Path(..., description="Ticket UUID"),
    db: DatabaseService = Depends(get_db_service)
) -> Message:
    """Add a new message to a ticket.
    
    Args:
        message_data: Message creation data
        ticket_id: Ticket UUID
        db: Database service dependency
        
    Returns:
        Created message
        
    Raises:
        HTTPException: If ticket is not found or message creation fails
    """
    try:
        # Check if ticket exists
        existing_ticket = await db.tickets.get_by_id(ticket_id)
        if not existing_ticket:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        
        # Check if ticket is closed
        if existing_ticket.status == TicketStatus.CLOSED.value:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Cannot add messages to a closed ticket"
            )
        
        # Ensure the ticket_id in the path matches the one in the request body
        if message_data.ticket_id != ticket_id:
            message_data.ticket_id = ticket_id
        
        # Create the message
        message = await db.messages.create(
            ticket_id=message_data.ticket_id,
            content=message_data.content,
            author_discord_id=message_data.author_discord_id,
            discord_message_id=message_data.discord_message_id,
            message_type=message_data.message_type
        )
        
        # Update the ticket's updated_at timestamp
        await db.tickets.update(ticket_id, updated_at=message.created_at)
        
        return message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}"
        )