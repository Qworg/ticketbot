"""FastAPI backend for Discord Ticket Bot."""

import asyncio
import logging
import uuid
from datetime import datetime
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
from backend.openapi_config import custom_openapi, get_openapi_tags

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
    description="""
    ## Discord Ticket Bot REST API
    
    A comprehensive support ticket management system that integrates Discord channels with a FastAPI backend and React-based web dashboard.
    
    ### Features
    
    * **Ticket Management**: Create, update, and close support tickets
    * **Real-time Synchronization**: Bidirectional sync between Discord and web dashboard
    * **Transcript Management**: Generate, search, and share ticket transcripts
    * **Authentication**: JWT tokens for staff and API keys for external systems
    * **Permission Control**: Role-based access control for staff members
    * **WebSocket Support**: Real-time updates via WebSocket connections
    
    ### Authentication
    
    This API supports two authentication methods:
    
    1. **JWT Bearer Tokens**: For staff members accessing the web dashboard
    2. **API Keys**: For external systems integrating with the ticket system
    
    Include the token in the `Authorization` header: `Bearer <token>`
    
    ### Rate Limiting
    
    API endpoints are rate-limited to prevent abuse. Rate limit information is included in response headers.
    
    ### Error Handling
    
    All endpoints return structured error responses with appropriate HTTP status codes and detailed error messages.
    """,
    version="1.0.0",
    contact={
        "name": "Discord Ticket Bot Support",
        "url": "https://github.com/your-org/discord-ticket-bot",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=get_openapi_tags(),
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.ticketbot.example.com",
            "description": "Production server"
        }
    ]
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

# Set up custom OpenAPI schema
app.openapi = lambda: custom_openapi(app)

# Redis service instance for application-wide use
redis_service = None

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(
    websocket: WebSocket,
    redis: RedisService = Depends(get_redis),
    user_id: int = Depends(get_websocket_token)
):
    """
    WebSocket endpoint for real-time updates.
    
    This endpoint handles WebSocket connections for real-time communication with the web dashboard.
    Clients can connect to receive live updates about:
    
    - Ticket status changes
    - New messages in tickets
    - Transcript updates
    - System notifications
    
    **Authentication**: Requires a valid JWT token passed as a query parameter or in the WebSocket headers.
    
    **Connection Flow**:
    1. Client connects with authentication token
    2. Server validates token and establishes connection
    3. Client subscribes to relevant channels (tickets, messages, etc.)
    4. Server broadcasts real-time updates to subscribed clients
    
    **Message Format**:
    ```json
    {
        "type": "ticket_update|message_new|transcript_update|system_notification",
        "data": { ... },
        "timestamp": "2024-01-01T12:00:00Z"
    }
    ```
    
    Args:
        websocket: WebSocket connection instance
        redis: Redis service for pub/sub messaging
        user_id: Authenticated user's Discord ID from token
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


@app.get(
    "/health",
    tags=["health"],
    summary="Health Check",
    description="Check the health status of the API and its dependencies",
    response_description="Health status of the service and its dependencies"
)
async def health_check(redis: RedisService = Depends(get_redis)):
    """
    Health check endpoint for container monitoring and load balancers.
    
    Returns the health status of:
    - The API service itself
    - Database connection (PostgreSQL)
    - Redis connection and pub/sub system
    
    Returns:
        dict: Health status information including service status and dependency health
    """
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
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "redis": redis_status
    }


@app.get(
    "/",
    tags=["health"],
    summary="API Information",
    description="Get basic information about the Discord Ticket Bot API",
    response_description="Basic API information and available endpoints"
)
async def root():
    """
    Root endpoint providing basic API information and navigation links.
    
    Returns:
        dict: API information including version, documentation links, and available endpoints
    """
    return {
        "message": "Discord Ticket Bot API",
        "version": "1.0.0",
        "description": "REST API for Discord ticket management system",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "tickets": "/api/tickets",
            "transcripts": "/api/tickets/{ticket_id}/transcript",
            "search": "/api/search/transcripts",
            "auth": "/api/auth",
            "websocket": "/ws"
        },
        "timestamp": datetime.now().isoformat()
    }