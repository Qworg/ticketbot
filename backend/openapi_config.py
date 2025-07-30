"""
OpenAPI configuration and documentation enhancements for Discord Ticket Bot API.
"""

from typing import Dict, Any, List
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Custom OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers
    )
    
    # Add custom schema components
    openapi_schema["components"]["schemas"].update(get_custom_schemas())
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for staff authentication"
        },
        "ApiKeyAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "API key for external system authentication"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]
    
    # Add response examples
    add_response_examples(openapi_schema)
    
    # Add request examples
    add_request_examples(openapi_schema)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def get_custom_schemas() -> Dict[str, Any]:
    """
    Get custom schema definitions for OpenAPI documentation.
    
    Returns:
        Dictionary of custom schema definitions
    """
    return {
        "WebSocketMessage": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["ticket_update", "message_new", "transcript_update", "system_notification"],
                    "description": "Type of WebSocket message"
                },
                "data": {
                    "type": "object",
                    "description": "Message payload data"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Message timestamp in ISO format"
                }
            },
            "required": ["type", "data", "timestamp"],
            "example": {
                "type": "ticket_update",
                "data": {
                    "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "in_progress",
                    "updated_by": 123456789
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        },
        "RateLimitInfo": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of requests allowed"
                },
                "remaining": {
                    "type": "integer", 
                    "description": "Number of requests remaining in current window"
                },
                "reset": {
                    "type": "integer",
                    "description": "Unix timestamp when the rate limit resets"
                }
            },
            "example": {
                "limit": 100,
                "remaining": 95,
                "reset": 1640995200
            }
        }
    }


def add_response_examples(openapi_schema: Dict[str, Any]) -> None:
    """
    Add response examples to OpenAPI schema.
    
    Args:
        openapi_schema: OpenAPI schema to modify
    """
    # Add examples for common responses
    paths = openapi_schema.get("paths", {})
    
    # Example for ticket creation
    if "/api/tickets" in paths and "post" in paths["/api/tickets"]:
        paths["/api/tickets"]["post"]["responses"]["201"]["content"]["application/json"]["example"] = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Login Issue",
            "description": "Unable to login to the application",
            "discord_channel_id": 987654321,
            "status": "open",
            "priority": "medium",
            "creator_discord_id": 123456789,
            "assigned_staff_id": None,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
            "closed_at": None
        }
    
    # Example for error responses
    error_example = {
        "detail": "Ticket with ID 123e4567-e89b-12d3-a456-426614174000 not found"
    }
    
    # Add error examples to all endpoints
    for path_data in paths.values():
        for method_data in path_data.values():
            if isinstance(method_data, dict) and "responses" in method_data:
                responses = method_data["responses"]
                if "404" in responses:
                    responses["404"]["content"] = {
                        "application/json": {
                            "example": error_example
                        }
                    }


def add_request_examples(openapi_schema: Dict[str, Any]) -> None:
    """
    Add request examples to OpenAPI schema.
    
    Args:
        openapi_schema: OpenAPI schema to modify
    """
    paths = openapi_schema.get("paths", {})
    
    # Example for ticket creation request
    if "/api/tickets" in paths and "post" in paths["/api/tickets"]:
        request_body = paths["/api/tickets"]["post"].get("requestBody", {})
        if "content" in request_body and "application/json" in request_body["content"]:
            request_body["content"]["application/json"]["example"] = {
                "title": "Login Issue",
                "description": "User cannot login to the application after password reset",
                "priority": "high",
                "creator_discord_id": 123456789,
                "discord_channel_id": 987654321
            }
    
    # Example for ticket update request
    if "/api/tickets/{ticket_id}" in paths and "put" in paths["/api/tickets/{ticket_id}"]:
        request_body = paths["/api/tickets/{ticket_id}"]["put"].get("requestBody", {})
        if "content" in request_body and "application/json" in request_body["content"]:
            request_body["content"]["application/json"]["example"] = {
                "status": "in_progress",
                "assigned_staff_id": 987654321,
                "priority": "high"
            }


def get_openapi_tags() -> List[Dict[str, str]]:
    """
    Get OpenAPI tags with descriptions.
    
    Returns:
        List of tag definitions
    """
    return [
        {
            "name": "tickets",
            "description": """
            **Ticket Management Operations**
            
            Create, read, update, and close support tickets. Tickets represent customer support requests
            that are managed through Discord channels and the web dashboard.
            
            **Key Features:**
            - Create tickets via API or Discord commands
            - Update ticket status, priority, and assignments
            - Close tickets and archive Discord channels
            - Add messages to existing tickets
            - Filter and paginate ticket lists
            """
        },
        {
            "name": "transcripts",
            "description": """
            **Transcript Management Operations**
            
            Generate, search, and share ticket transcripts. Transcripts provide a complete record
            of all messages and interactions within a support ticket.
            
            **Key Features:**
            - Generate transcripts from ticket messages
            - Search transcript content with full-text search
            - Share transcripts via secure tokens
            - Export transcripts in multiple formats
            - Manage transcript access permissions
            """
        },
        {
            "name": "authentication",
            "description": """
            **Authentication and Authorization**
            
            Manage staff authentication and API key access for external systems.
            
            **Authentication Methods:**
            - JWT tokens for staff members
            - API keys for external system integration
            - Role-based access control
            - Permission management
            
            **Supported Roles:**
            - Admin: Full system access
            - Moderator: Ticket management and staff oversight
            - Support: Basic ticket handling
            """
        },
        {
            "name": "health",
            "description": """
            **Health Check and System Status**
            
            Monitor the health and status of the API and its dependencies.
            
            **Monitored Components:**
            - API service status
            - Database connectivity (PostgreSQL)
            - Redis pub/sub system
            - WebSocket connections
            """
        },
        {
            "name": "websocket",
            "description": """
            **Real-time WebSocket Communication**
            
            WebSocket endpoints for real-time updates between Discord, the API, and web dashboard.
            
            **Real-time Features:**
            - Live ticket status updates
            - New message notifications
            - Transcript generation updates
            - System-wide notifications
            
            **Connection Requirements:**
            - Valid JWT token for authentication
            - WebSocket-compatible client
            - Subscription to relevant event channels
            """
        }
    ]