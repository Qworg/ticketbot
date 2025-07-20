"""API routes for ticket management."""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from backend.database_service import DatabaseService, get_db_service
from backend.models import TicketStatus, Priority
from backend.schemas import (
    Ticket, TicketCreate, TicketUpdate, TicketPagination,
    TicketWithMessages, ErrorResponse
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