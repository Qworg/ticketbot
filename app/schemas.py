"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.status import TicketStatus, get_valid_next_statuses, validate_status_transition
import re


class TicketCreateRequest(BaseModel):
    """
    Pydantic model for ticket creation request.
    """
    guild_id: int = Field(..., description="Discord guild ID where ticket is created")
    creator_id: int = Field(..., description="Discord user ID who created the ticket")
    reason: str = Field(..., min_length=5, max_length=500, description="Ticket description/reason")
    category: Optional[str] = Field(None, max_length=100, description="Optional ticket category")
    channel_id: Optional[int] = Field(None, description="Optional Discord channel ID")

    @field_validator('guild_id')
    @classmethod
    def validate_guild_id(cls, v):
        """Validate guild_id is a valid Discord snowflake."""
        if not isinstance(v, int) or v <= 0:
            raise ValueError('guild_id must be a positive integer')
        # Discord snowflakes are typically 17-19 digits long
        if len(str(v)) < 17 or len(str(v)) > 19:
            raise ValueError('guild_id must be a valid Discord snowflake (17-19 digits)')
        return v

    @field_validator('creator_id')
    @classmethod
    def validate_creator_id(cls, v):
        """Validate creator_id is a valid Discord snowflake."""
        if not isinstance(v, int) or v <= 0:
            raise ValueError('creator_id must be a positive integer')
        # Discord snowflakes are typically 17-19 digits long
        if len(str(v)) < 17 or len(str(v)) > 19:
            raise ValueError('creator_id must be a valid Discord snowflake (17-19 digits)')
        return v

    @field_validator('channel_id')
    @classmethod
    def validate_channel_id(cls, v):
        """Validate channel_id is a valid Discord snowflake if provided."""
        if v is not None:
            if not isinstance(v, int) or v <= 0:
                raise ValueError('channel_id must be a positive integer')
            # Discord snowflakes are typically 17-19 digits long
            if len(str(v)) < 17 or len(str(v)) > 19:
                raise ValueError('channel_id must be a valid Discord snowflake (17-19 digits)')
        return v

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v):
        """Validate reason content."""
        if not v or not v.strip():
            raise ValueError('reason cannot be empty or whitespace only')
        # Remove excessive whitespace
        v = ' '.join(v.split())
        if len(v) < 5:
            raise ValueError('reason must be at least 5 characters long')
        if len(v) > 500:
            raise ValueError('reason must be at most 500 characters long')
        return v

    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        """Validate category if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 100:
                raise ValueError('category must be at most 100 characters long')
        return v


class TicketResponse(BaseModel):
    """
    Pydantic model for ticket response.
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    channel_id: Optional[int]
    guild_id: int
    creator_id: int
    assigned_to: Optional[int]
    status: str
    category: Optional[str]
    reason: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    close_reason: Optional[str]
    claimed_at: Optional[datetime]
    is_shadow_closed: bool

    model_config = ConfigDict(from_attributes=True)


class TicketCreateResponse(BaseModel):
    """
    Response model for successful ticket creation.
    """
    success: bool = True
    message: str
    ticket: TicketResponse


class ErrorResponse(BaseModel):
    """
    Error response model.
    """
    success: bool = False
    error: str
    detail: Optional[str] = None


class TicketStatusUpdateRequest(BaseModel):
    """
    Pydantic model for ticket status update request.
    """
    new_status: str = Field(..., description="New status for the ticket")
    close_reason: Optional[str] = Field(None, description="Reason for closing the ticket")

    @field_validator('new_status')
    @classmethod
    def validate_new_status(cls, v):
        """Validate new_status is a valid status."""
        try:
            # Validate it's a valid status enum value
            TicketStatus(v.lower())
            return v.lower()
        except ValueError:
            valid_statuses = [status.value for status in TicketStatus]
            raise ValueError(f'new_status must be one of {valid_statuses}')

    @field_validator('close_reason')
    @classmethod
    def validate_close_reason(cls, v, info):
        """Validate close_reason is provided when transitioning to closed."""
        # In Pydantic v2, we access other field values through info.data
        new_status = info.data.get('new_status') if info.data else None
        if new_status == TicketStatus.CLOSED.value and not v:
            raise ValueError('close_reason is required when transitioning to closed status')
        if v and len(v.strip()) < 3:
            raise ValueError('close_reason must be at least 3 characters long')
        if v and len(v) > 200:
            raise ValueError('close_reason must be at most 200 characters long')
        return v.strip() if v else None


class TicketStatusUpdateResponse(BaseModel):
    """
    Response model for successful ticket status update.
    """
    success: bool = True
    message: str
    ticket: TicketResponse
    previous_status: str
    transition_log: dict


class ValidNextStatusesResponse(BaseModel):
    """
    Response model for getting valid next statuses for a ticket.
    """
    current_status: str
    valid_next_statuses: List[str]
    status_descriptions: dict


class UserSummary(BaseModel):
    """
    Summary user information for inclusion in ticket responses.
    """
    id: str  # UUID as string
    discord_id: int
    email: Optional[str]
    role: str
    
    model_config = ConfigDict(from_attributes=True)


class TicketDetailResponse(BaseModel):
    """
    Comprehensive ticket response with related user information.
    """
    id: int
    channel_id: Optional[int]
    guild_id: int
    creator_id: int
    assigned_to: Optional[int]
    status: str
    category: Optional[str]
    reason: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    close_reason: Optional[str]
    is_shadow_closed: bool
    
    # Related user information
    creator: Optional[UserSummary] = None
    assigned_staff: Optional[UserSummary] = None
    
    # Additional metadata
    participants_count: Optional[int] = None
    recent_messages_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TicketUpdateRequest(BaseModel):
    """
    Pydantic model for ticket update request.
    Allows updating multiple fields in a single request.
    """
    status: Optional[str] = Field(None, description="New status for the ticket")
    category: Optional[str] = Field(None, max_length=100, description="New category for the ticket")
    assigned_to: Optional[int] = Field(None, description="Discord user ID to assign ticket to (or null to unassign)")
    close_reason: Optional[str] = Field(None, description="Reason for closing the ticket")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status is a valid ticket status."""
        if v is not None:
            try:
                # Validate it's a valid status enum value
                TicketStatus(v.lower())
                return v.lower()
            except ValueError:
                valid_statuses = [status.value for status in TicketStatus]
                raise ValueError(f'status must be one of {valid_statuses}')
        return v

    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        """Validate category if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) > 100:
                raise ValueError('category must be at most 100 characters long')
        return v

    @field_validator('assigned_to')
    @classmethod
    def validate_assigned_to(cls, v):
        """Validate assigned_to is a valid Discord snowflake if provided."""
        if v is not None:
            if not isinstance(v, int) or v <= 0:
                raise ValueError('assigned_to must be a positive integer')
            # Discord snowflakes are typically 17-19 digits long
            if len(str(v)) < 17 or len(str(v)) > 19:
                raise ValueError('assigned_to must be a valid Discord snowflake (17-19 digits)')
        return v

    @field_validator('close_reason')
    @classmethod
    def validate_close_reason(cls, v, info):
        """Validate close_reason is provided when transitioning to closed."""
        status = info.data.get('status') if info.data else None
        if status == TicketStatus.CLOSED.value and not v:
            raise ValueError('close_reason is required when transitioning to closed status')
        if v and len(v.strip()) < 3:
            raise ValueError('close_reason must be at least 3 characters long')
        if v and len(v) > 200:
            raise ValueError('close_reason must be at most 200 characters long')
        return v.strip() if v else None


class TicketUpdateResponse(BaseModel):
    """
    Response model for successful ticket update.
    """
    success: bool = True
    message: str
    ticket: TicketResponse
    changes_made: List[str]
    transition_log: Optional[dict] = None


class TicketListRequest(BaseModel):
    """
    Pydantic model for ticket list request with filters and pagination.
    """
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    limit: int = Field(default=20, ge=1, le=100, description="Number of tickets per page (max 100)")
    status: Optional[str] = Field(None, description="Filter by ticket status")
    assigned_to: Optional[int] = Field(None, description="Filter by assigned staff member")
    guild_id: Optional[int] = Field(None, description="Filter by guild ID")
    created_after: Optional[datetime] = Field(None, description="Filter tickets created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter tickets created before this date")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status is a valid ticket status if provided."""
        if v is not None:
            try:
                TicketStatus(v.lower())
                return v.lower()
            except ValueError:
                valid_statuses = [status.value for status in TicketStatus]
                raise ValueError(f'status must be one of {valid_statuses}')
        return v

    @field_validator('assigned_to')
    @classmethod
    def validate_assigned_to(cls, v):
        """Validate assigned_to is a valid Discord snowflake if provided."""
        if v is not None:
            if not isinstance(v, int) or v <= 0:
                raise ValueError('assigned_to must be a positive integer')
            # Discord snowflakes are typically 17-19 digits long
            if len(str(v)) < 17 or len(str(v)) > 19:
                raise ValueError('assigned_to must be a valid Discord snowflake (17-19 digits)')
        return v

    @field_validator('guild_id')
    @classmethod
    def validate_guild_id(cls, v):
        """Validate guild_id is a valid Discord snowflake if provided."""
        if v is not None:
            if not isinstance(v, int) or v <= 0:
                raise ValueError('guild_id must be a positive integer')
            # Discord snowflakes are typically 17-19 digits long
            if len(str(v)) < 17 or len(str(v)) > 19:
                raise ValueError('guild_id must be a valid Discord snowflake (17-19 digits)')
        return v


class PaginationMetadata(BaseModel):
    """
    Pagination metadata for list responses.
    """
    page: int
    limit: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[str] = None
    previous_page: Optional[str] = None


class TicketListResponse(BaseModel):
    """
    Response model for ticket list endpoint.
    """
    success: bool = True
    tickets: List[TicketResponse]
    pagination: PaginationMetadata


class TicketClaimResponse(BaseModel):
    """
    Response model for ticket claim endpoint.
    """
    success: bool = True
    message: str
    ticket: TicketResponse


class TicketUnclaimResponse(BaseModel):
    """
    Response model for ticket unclaim endpoint.
    """
    success: bool = True
    message: str
    ticket: TicketResponse
