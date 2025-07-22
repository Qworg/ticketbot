"""FastAPI backend for Discord Ticket Bot."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import tickets_router, transcripts_router
from backend.db import check_db_connection

app = FastAPI(
    title="Discord Ticket Bot API",
    description="REST API for Discord ticket management system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(tickets_router)
app.include_router(transcripts_router)


@app.get("/health")
async def health_check():
    """Health check endpoint for container monitoring."""
    db_status = await check_db_connection()
    return {
        "status": "healthy" if db_status["status"] == "connected" else "unhealthy",
        "service": "discord-ticket-bot-backend",
        "database": db_status
    }


@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "Discord Ticket Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }