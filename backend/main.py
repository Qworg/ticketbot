"""FastAPI backend for Discord Ticket Bot."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
async def health_check():
    """Health check endpoint for container monitoring."""
    return {"status": "healthy", "service": "discord-ticket-bot-backend"}


@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "Discord Ticket Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }