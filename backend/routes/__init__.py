"""API route modules for the Discord Ticket Bot system."""

from .tickets import router as tickets_router
from .transcripts import router as transcripts_router

__all__ = ["tickets_router", "transcripts_router"]