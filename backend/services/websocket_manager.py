"""WebSocket manager for real-time communication with web dashboard.

This module provides a WebSocket manager for:
1. Managing WebSocket connections with clients
2. Broadcasting real-time events to connected clients
3. Handling connection management and reconnection
4. Authenticating WebSocket connections
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional, List, Callable, Awaitable
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from backend.services.redis_service import RedisService, EventType

# Configure logger
logger = logging.getLogger(__name__)

# WebSocket authentication header
ws_token_header = APIKeyHeader(name="X-WebSocket-Token", auto_error=False)


class ConnectionManager:
    """WebSocket connection manager for real-time communication.
    
    This class manages WebSocket connections with clients and handles
    broadcasting events to connected clients.
    
    Attributes:
        active_connections: Dictionary of active WebSocket connections
        user_connections: Dictionary mapping user IDs to connection IDs
        ticket_subscribers: Dictionary mapping ticket IDs to connection IDs
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, Set[str]] = {}  # Discord ID -> connection IDs
        self.ticket_subscribers: Dict[UUID, Set[str]] = {}  # Ticket ID -> connection IDs
        self.redis_handlers_registered = False
    
    async def connect(
        self, 
        websocket: WebSocket, 
        connection_id: str,
        user_id: Optional[int] = None
    ) -> None:
        """Accept a WebSocket connection and store it.
        
        Args:
            websocket: WebSocket connection
            connection_id: Unique connection identifier
            user_id: Optional Discord user ID
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        # Associate connection with user if provided
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        # Send welcome message
        await self.send_personal_message(
            {"type": "connection_established", "connection_id": connection_id},
            connection_id
        )
        
        logger.info(f"WebSocket connection established: {connection_id}, user: {user_id}")
    
    def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection.
        
        Args:
            connection_id: Connection identifier to remove
        """
        # Remove from active connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from user connections
        for user_id, connections in list(self.user_connections.items()):
            if connection_id in connections:
                connections.remove(connection_id)
                if not connections:
                    del self.user_connections[user_id]
        
        # Remove from ticket subscribers
        for ticket_id, subscribers in list(self.ticket_subscribers.items()):
            if connection_id in subscribers:
                subscribers.remove(connection_id)
                if not subscribers:
                    del self.ticket_subscribers[ticket_id]
        
        logger.info(f"WebSocket connection disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str) -> bool:
        """Send a message to a specific connection.
        
        Args:
            message: Message to send
            connection_id: Connection identifier to send to
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if connection_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {str(e)}")
            # Connection might be dead, remove it
            self.disconnect(connection_id)
            return False
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast
        """
        disconnected = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {str(e)}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def broadcast_to_users(self, message: Dict[str, Any], user_ids: List[int]) -> None:
        """Broadcast a message to specific users.
        
        Args:
            message: Message to broadcast
            user_ids: List of user Discord IDs to send to
        """
        connection_ids = set()
        for user_id in user_ids:
            if user_id in self.user_connections:
                connection_ids.update(self.user_connections[user_id])
        
        disconnected = []
        for connection_id in connection_ids:
            try:
                if connection_id in self.active_connections:
                    await self.active_connections[connection_id].send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user connection {connection_id}: {str(e)}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def broadcast_to_ticket_subscribers(
        self, 
        message: Dict[str, Any], 
        ticket_id: UUID
    ) -> None:
        """Broadcast a message to subscribers of a specific ticket.
        
        Args:
            message: Message to broadcast
            ticket_id: Ticket UUID
        """
        if ticket_id not in self.ticket_subscribers:
            return
        
        disconnected = []
        for connection_id in self.ticket_subscribers[ticket_id]:
            try:
                if connection_id in self.active_connections:
                    await self.active_connections[connection_id].send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to ticket subscriber {connection_id}: {str(e)}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    def subscribe_to_ticket(self, connection_id: str, ticket_id: UUID) -> bool:
        """Subscribe a connection to a specific ticket's updates.
        
        Args:
            connection_id: Connection identifier
            ticket_id: Ticket UUID to subscribe to
            
        Returns:
            bool: True if subscribed successfully, False otherwise
        """
        if connection_id not in self.active_connections:
            return False
        
        if ticket_id not in self.ticket_subscribers:
            self.ticket_subscribers[ticket_id] = set()
        
        self.ticket_subscribers[ticket_id].add(connection_id)
        return True
    
    def unsubscribe_from_ticket(self, connection_id: str, ticket_id: UUID) -> bool:
        """Unsubscribe a connection from a specific ticket's updates.
        
        Args:
            connection_id: Connection identifier
            ticket_id: Ticket UUID to unsubscribe from
            
        Returns:
            bool: True if unsubscribed successfully, False otherwise
        """
        if ticket_id not in self.ticket_subscribers:
            return False
        
        if connection_id in self.ticket_subscribers[ticket_id]:
            self.ticket_subscribers[ticket_id].remove(connection_id)
            if not self.ticket_subscribers[ticket_id]:
                del self.ticket_subscribers[ticket_id]
            return True
        
        return False
    
    async def register_redis_handlers(self, redis: RedisService) -> None:
        """Register handlers for Redis events.
        
        Args:
            redis: Redis service instance
        """
        if self.redis_handlers_registered:
            return
        
        # Register ticket event handler
        await redis.register_handler(
            "ticket_events", 
            self.handle_ticket_event
        )
        
        # Register message event handler
        await redis.register_handler(
            "message_events",
            self.handle_message_event
        )
        
        # Register transcript event handler
        await redis.register_handler(
            "transcript_events",
            self.handle_transcript_event
        )
        
        self.redis_handlers_registered = True
        logger.info("Registered Redis event handlers for WebSocket manager")
    
    async def handle_ticket_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle ticket events from Redis.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        # Create WebSocket message
        message = {
            "type": event_type,
            "data": data
        }
        
        # Broadcast to ticket subscribers if ticket ID is available
        if "id" in data:
            try:
                ticket_id = UUID(data["id"])
                await self.broadcast_to_ticket_subscribers(message, ticket_id)
            except (ValueError, KeyError):
                pass
        
        # Broadcast to specific users
        users_to_notify = []
        if "creator_discord_id" in data:
            users_to_notify.append(data["creator_discord_id"])
        if "assigned_staff_id" in data and data["assigned_staff_id"]:
            users_to_notify.append(data["assigned_staff_id"])
        if "updated_by_discord_id" in data:
            users_to_notify.append(data["updated_by_discord_id"])
        
        if users_to_notify:
            await self.broadcast_to_users(message, users_to_notify)
    
    async def handle_message_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle message events from Redis.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        # Create WebSocket message
        message = {
            "type": event_type,
            "data": data
        }
        
        # Broadcast to ticket subscribers if ticket ID is available
        if "ticket_id" in data:
            try:
                ticket_id = UUID(data["ticket_id"])
                await self.broadcast_to_ticket_subscribers(message, ticket_id)
            except (ValueError, KeyError):
                pass
        
        # Broadcast to message author
        if "author_discord_id" in data:
            await self.broadcast_to_users(message, [data["author_discord_id"]])
    
    async def handle_transcript_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle transcript events from Redis.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        # Create WebSocket message
        message = {
            "type": event_type,
            "data": data
        }
        
        # Broadcast to ticket subscribers if ticket ID is available
        if "ticket_id" in data:
            try:
                ticket_id = UUID(data["ticket_id"])
                await self.broadcast_to_ticket_subscribers(message, ticket_id)
            except (ValueError, KeyError):
                pass


# Create a global connection manager instance
manager = ConnectionManager()


async def get_websocket_token(
    token: str = Depends(ws_token_header)
) -> Optional[int]:
    """Validate WebSocket token and return user ID.
    
    This function validates the WebSocket authentication token
    and returns the associated user ID.
    
    Args:
        token: WebSocket authentication token
        
    Returns:
        int: User Discord ID if token is valid
        
    Raises:
        HTTPException: If token is invalid
    """
    # For now, we'll use a simple token validation
    # In a real implementation, this would validate against a database or JWT
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket authentication token required"
        )
    
    # TODO: Implement proper token validation
    # For now, we'll assume the token is the user's Discord ID
    try:
        user_id = int(token)
        return user_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WebSocket authentication token"
        )


async def websocket_endpoint(
    websocket: WebSocket,
    redis: RedisService,
    user_id: Optional[int] = None
):
    """WebSocket endpoint for real-time communication.
    
    This endpoint handles WebSocket connections and message processing.
    
    Args:
        websocket: WebSocket connection
        redis: Redis service instance
        user_id: Optional user Discord ID from token authentication
    """
    # Generate a unique connection ID
    connection_id = f"{id(websocket)}_{asyncio.get_event_loop().time()}"
    
    # Register Redis handlers if not already registered
    await manager.register_redis_handlers(redis)
    
    try:
        # Accept the connection
        await manager.connect(websocket, connection_id, user_id)
        
        # Process messages
        while True:
            try:
                # Wait for messages from the client
                data = await websocket.receive_json()
                
                # Process client messages
                message_type = data.get("type")
                
                if message_type == "ping":
                    # Respond to ping with pong
                    await manager.send_personal_message({"type": "pong"}, connection_id)
                
                elif message_type == "subscribe_ticket":
                    # Subscribe to ticket updates
                    ticket_id_str = data.get("ticket_id")
                    if ticket_id_str:
                        try:
                            ticket_id = UUID(ticket_id_str)
                            success = manager.subscribe_to_ticket(connection_id, ticket_id)
                            await manager.send_personal_message(
                                {
                                    "type": "subscription_result",
                                    "ticket_id": ticket_id_str,
                                    "success": success
                                },
                                connection_id
                            )
                        except ValueError:
                            await manager.send_personal_message(
                                {
                                    "type": "error",
                                    "message": "Invalid ticket ID format"
                                },
                                connection_id
                            )
                
                elif message_type == "unsubscribe_ticket":
                    # Unsubscribe from ticket updates
                    ticket_id_str = data.get("ticket_id")
                    if ticket_id_str:
                        try:
                            ticket_id = UUID(ticket_id_str)
                            success = manager.unsubscribe_from_ticket(connection_id, ticket_id)
                            await manager.send_personal_message(
                                {
                                    "type": "unsubscription_result",
                                    "ticket_id": ticket_id_str,
                                    "success": success
                                },
                                connection_id
                            )
                        except ValueError:
                            await manager.send_personal_message(
                                {
                                    "type": "error",
                                    "message": "Invalid ticket ID format"
                                },
                                connection_id
                            )
            
            except WebSocketDisconnect:
                manager.disconnect(connection_id)
                break
            
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON format"
                    },
                    connection_id
                )
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Internal server error"
                    },
                    connection_id
                )
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        manager.disconnect(connection_id)