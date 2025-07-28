"""FastAPI backend for Discord Ticket Bot."""

import asyncio
import logging
import uuid
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.routes import tickets_router, transcripts_router
from backend.routes.auth import router as auth_router
from backend.routes.metrics import router as metrics_router
from backend.db import check_db_connection
from backend.services.redis_service import get_redis, RedisService
from backend.services.websocket_manager import websocket_endpoint, get_websocket_token
from backend.error_handlers import setup_error_handlers
from backend.logging_config import setup_logging, get_logger
from backend.middleware.monitoring import MonitoringMiddleware

# Set up logging
setup_logging()
logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request IDs for tracing."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


app = FastAPI(
    title="Discord Ticket Bot API",
    description="REST API for Discord ticket management system",
    version="1.0.0"
)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)

# Add request ID middleware
app.add_middleware(RequestIDMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up error handlers
setup_error_handlers(app)

# Include API routers
app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(transcripts_router)
app.include_router(metrics_router)

# Redis service instance for application-wide use
redis_service = None

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(
    websocket: WebSocket,
    redis: RedisService = Depends(get_redis),
    user_id: int = Depends(get_websocket_token)
):
    """WebSocket endpoint for real-time updates.
    
    This endpoint handles WebSocket connections for real-time
    communication with the web dashboard.
    
    Args:
        websocket: WebSocket connection
        redis: Redis service dependency
        user_id: User Discord ID from token authentication
    """
    await websocket_endpoint(websocket, redis, user_id)


@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    global redis_service
    
    # Initialize Redis service
    redis_service = await anext(get_redis().__aiter__())
    
    # Subscribe to Redis channels and start listener
    await redis_service.subscribe([
        "ticket_events", 
        "message_events", 
        "transcript_events", 
        "system_events"
    ])
    await redis_service.start_listener()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    global redis_service
    
    # Stop Redis listener
    if redis_service:
        await redis_service.stop_listener()


@app.get("/health")
async def health_check(redis: RedisService = Depends(get_redis)):
    """Health check endpoint for container monitoring."""
    db_status = await check_db_connection()
    redis_status = await redis.check_health()
    
    # Determine overall status
    is_healthy = (
        db_status["status"] == "connected" and 
        redis_status["status"] == "healthy"
    )
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "discord-ticket-bot-backend",
        "database": db_status,
        "redis": redis_status
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