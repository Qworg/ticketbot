"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
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

    @validator('guild_id')
    def validate_guild_id(cls, v):
        """Validate guild_id is a valid Discord snowflake."""
        if not isinstance(v, int) or v <= 0:
            raise ValueError('guild_id must be a positive integer')
        # Discord snowflakes are typically 17-19 digits long
        if len(str(v)) < 17 or len(str(v)) > 19:
            raise ValueError('guild_id must be a valid Discord snowflake (17-19 digits)')
        return v

    @validator('creator_id')
    def validate_creator_id(cls, v):
        """Validate creator_id is a valid Discord snowflake."""
        if not isinstance(v, int) or v <= 0:
            raise ValueError('creator_id must be a positive integer')
        # Discord snowflakes are typically 17-19 digits long
        if len(str(v)) < 17 or len(str(v)) > 19:
            raise ValueError('creator_id must be a valid Discord snowflake (17-19 digits)')
        return v

    @validator('channel_id')
    def validate_channel_id(cls, v):
        """Validate channel_id is a valid Discord snowflake if provided."""
        if v is not None:
            if not isinstance(v, int) or v <= 0:
                raise ValueError('channel_id must be a positive integer')
            # Discord snowflakes are typically 17-19 digits long
            if len(str(v)) < 17 or len(str(v)) > 19:
                raise ValueError('channel_id must be a valid Discord snowflake (17-19 digits)')
        return v

    @validator('reason')
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

    @validator('category')
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

    class Config:
        from_attributes = True


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
