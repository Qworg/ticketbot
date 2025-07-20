"""
Pydantic models for the Discord Ticket Bot system.
These models are used for validation, serialization, and API responses.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, field_validator, model_validator, UUID4
from typing_extensions import Annotated


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


class TicketBase(BaseModel):
    """Base model for ticket data."""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    
    @field_validator('title')
    @classmethod
    def title_must_not_be_empty(cls, v):
        """Validate that the title is not empty."""
        v = v.strip()
        if not v:
            raise ValueError('Title must not be empty')
        return v


class TicketCreate(TicketBase):
    """Model for creating a new ticket."""
    creator_discord_id: int = Field(..., gt=0)
    discord_channel_id: int = Field(..., gt=0)


class TicketUpdate(BaseModel):
    """Model for updating an existing ticket."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[Priority] = None
    assigned_staff_id: Optional[int] = Field(None, gt=0)
    
    @field_validator('title')
    @classmethod
    def title_must_not_be_empty(cls, v):
        """Validate that the title is not empty if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Title must not be empty')
        return v
    
    @model_validator(mode='after')
    def check_at_least_one_field(self):
        """Validate that at least one field is provided for update."""
        values = {k: v for k, v in self.__dict__.items() if v is not None}
        if not any(values.values()):
            raise ValueError('At least one field must be provided for update')
        return self


class Ticket(TicketBase):
    """Complete ticket model with all fields."""
    id: UUID4
    discord_channel_id: int
    status: TicketStatus
    creator_discord_id: int
    assigned_staff_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }


class MessageBase(BaseModel):
    """Base model for message data."""
    content: str = Field(..., min_length=1)
    message_type: MessageType = MessageType.USER_MESSAGE
    
    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        """Validate that the content is not empty."""
        v = v.strip()
        if not v:
            raise ValueError('Message content must not be empty')
        return v


class MessageCreate(MessageBase):
    """Model for creating a new message."""
    ticket_id: UUID4
    author_discord_id: int = Field(..., gt=0)
    discord_message_id: Optional[int] = Field(None, gt=0)


class Message(MessageBase):
    """Complete message model with all fields."""
    id: UUID4
    ticket_id: UUID4
    author_discord_id: int
    discord_message_id: Optional[int] = None
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class TranscriptBase(BaseModel):
    """Base model for transcript data."""
    content: str
    formatted_content: Optional[Dict[str, Any]] = None


class TranscriptCreate(TranscriptBase):
    """Model for creating a new transcript."""
    ticket_id: UUID4


class TranscriptUpdate(BaseModel):
    """Model for updating an existing transcript."""
    content: Optional[str] = None
    formatted_content: Optional[Dict[str, Any]] = None
    share_token: Optional[str] = None


class Transcript(TranscriptBase):
    """Complete transcript model with all fields."""
    id: UUID4
    ticket_id: UUID4
    share_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class StaffBase(BaseModel):
    """Base model for staff data."""
    discord_id: int = Field(..., gt=0)
    username: str = Field(..., min_length=1, max_length=255)
    role: StaffRole = StaffRole.SUPPORT
    permissions: Dict[str, bool] = Field(default_factory=dict)
    active: bool = True


class StaffCreate(StaffBase):
    """Model for creating a new staff member."""
    pass


class StaffUpdate(BaseModel):
    """Model for updating an existing staff member."""
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[StaffRole] = None
    permissions: Optional[Dict[str, bool]] = None
    active: Optional[bool] = None


class Staff(StaffBase):
    """Complete staff model with all fields."""
    id: UUID4
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class TicketWithMessages(Ticket):
    """Ticket model with included messages."""
    messages: List[Message] = []


class TicketWithTranscript(Ticket):
    """Ticket model with included transcript."""
    transcript: Optional[Transcript] = None


class PaginatedResponse(BaseModel):
    """Generic paginated response model."""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


class TicketPagination(PaginatedResponse):
    """Paginated response for tickets."""
    items: List[Ticket]


class MessagePagination(PaginatedResponse):
    """Paginated response for messages."""
    items: List[Message]


class TranscriptPagination(PaginatedResponse):
    """Paginated response for transcripts."""
    items: List[Transcript]


class StaffPagination(PaginatedResponse):
    """Paginated response for staff members."""
    items: List[Staff]


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: Union[str, List[Dict[str, Any]]]


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    database: Dict[str, Any]
    redis: Dict[str, Any]