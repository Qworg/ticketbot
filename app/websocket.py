"""
WebSocket server and connection management for Discord Ticket Bot.

This module provides WebSocket endpoints for real-time communication
between the dashboard and Discord bot.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.websockets import WebSocketState
from pydantic import BaseModel, ValidationError

from .auth import validate_token, TokenData, JWTError, TokenExpiredError, TokenInvalidError
from .database import get_db_session
from .models.user import get_user_by_id

logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """Structure for WebSocket messages."""
    type: str
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None


class ConnectionManager:
    """Manages WebSocket connections and message routing."""
    
    def __init__(self):
        # Active connections by user_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
        # Room subscriptions - maps room_id to set of user_ids
        self.room_subscriptions: Dict[str, Set[str]] = {}
        
        # User room memberships - maps user_id to set of room_ids
        self.user_rooms: Dict[str, Set[str]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, user_data: TokenData):
        """Accept a WebSocket connection and register it."""
        await websocket.accept()
        
        # Initialize user's connection list if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
            
        # Add connection to user's list
        self.active_connections[user_id].append(websocket)
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            'user_id': user_id,
            'user_data': user_data,
            'connected_at': datetime.now(timezone.utc),
            'last_ping': datetime.now(timezone.utc)
        }
        
        logger.info(f"WebSocket connection established for user {user_id}")
        
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket not in self.connection_metadata:
            return
            
        user_id = self.connection_metadata[websocket]['user_id']
        
        # Remove from active connections
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            
            # Clean up empty user entries
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
        # Remove from all rooms
        if user_id in self.user_rooms:
            for room_id in self.user_rooms[user_id].copy():
                self.leave_room(user_id, room_id)
                
        # Remove connection metadata
        del self.connection_metadata[websocket]
        
        logger.info(f"WebSocket connection closed for user {user_id}")
    
    def join_room(self, user_id: str, room_id: str):
        """Add user to a room for targeted messaging."""
        # Initialize room if not exists
        if room_id not in self.room_subscriptions:
            self.room_subscriptions[room_id] = set()
            
        # Initialize user rooms if not exists
        if user_id not in self.user_rooms:
            self.user_rooms[user_id] = set()
            
        # Add user to room
        self.room_subscriptions[room_id].add(user_id)
        self.user_rooms[user_id].add(room_id)
        
        logger.info(f"User {user_id} joined room {room_id}")
    
    def leave_room(self, user_id: str, room_id: str):
        """Remove user from a room."""
        # Remove from room subscriptions
        if room_id in self.room_subscriptions:
            self.room_subscriptions[room_id].discard(user_id)
            
            # Clean up empty rooms
            if not self.room_subscriptions[room_id]:
                del self.room_subscriptions[room_id]
                
        # Remove from user rooms
        if user_id in self.user_rooms:
            self.user_rooms[user_id].discard(room_id)
            
            # Clean up empty user entries
            if not self.user_rooms[user_id]:
                del self.user_rooms[user_id]
                
        logger.info(f"User {user_id} left room {room_id}")
    
    async def send_personal_message(self, user_id: str, message: WebSocketMessage):
        """Send a message to a specific user's connections."""
        if user_id not in self.active_connections:
            return
            
        # Add timestamp if not provided
        if not message.timestamp:
            message.timestamp = datetime.now(timezone.utc)
            
        message_data = message.model_dump()
        
        # Send to all user's connections
        disconnected_connections = []
        for websocket in self.active_connections[user_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message_data)
                else:
                    disconnected_connections.append(websocket)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                disconnected_connections.append(websocket)
        
        # Clean up disconnected connections
        for ws in disconnected_connections:
            self.disconnect(ws)
    
    async def broadcast_to_room(self, room_id: str, message: WebSocketMessage, exclude_user: Optional[str] = None):
        """Broadcast a message to all users in a room."""
        if room_id not in self.room_subscriptions:
            return
            
        # Add timestamp if not provided
        if not message.timestamp:
            message.timestamp = datetime.now(timezone.utc)
            
        # Send to all users in room
        for user_id in self.room_subscriptions[room_id]:
            if exclude_user and user_id == exclude_user:
                continue
                
            await self.send_personal_message(user_id, message)
                
        logger.info(f"Broadcasted message to room {room_id}")
    
    async def send_ping(self, websocket: WebSocket):
        """Send a ping message to keep connection alive."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({
                    'type': 'ping',
                    'data': {'timestamp': datetime.now(timezone.utc).isoformat()}
                })
                
                # Update last ping time
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]['last_ping'] = datetime.now(timezone.utc)
                    
        except Exception as e:
            logger.error(f"Error sending ping: {e}")
            self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a specific user."""
        return len(self.active_connections.get(user_id, []))
    
    def get_room_user_count(self, room_id: str) -> int:
        """Get number of users in a room."""
        return len(self.room_subscriptions.get(room_id, set()))


# Global connection manager instance
connection_manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket) -> Optional[TokenData]:
    """
    Authenticate WebSocket connection using JWT token.
    
    Args:
        websocket: WebSocket connection
        
    Returns:
        TokenData if authentication successful, None otherwise
    """
    try:
        # Get token from query parameter or header
        token = None
        
        # Try query parameter first
        if 'token' in websocket.query_params:
            token = websocket.query_params['token']
        
        # Try Authorization header
        elif 'Authorization' in websocket.headers:
            auth_header = websocket.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
            return None
        
        # Validate token
        try:
            token_data = validate_token(token)
        except TokenExpiredError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
            return None
        except TokenInvalidError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return None
        
        # Verify user exists in database
        with get_db_session() as db:
            user = get_user_by_id(db, token_data.user_id)
            if not user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                return None
        
        return token_data
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Authentication failed")
        return None


async def handle_websocket_message(websocket: WebSocket, message_data: Dict[str, Any]):
    """
    Handle incoming WebSocket messages.
    
    Args:
        websocket: WebSocket connection
        message_data: Parsed message data
    """
    try:
        # Get connection metadata
        if websocket not in connection_manager.connection_metadata:
            await websocket.close(code=status.WS_1002_PROTOCOL_ERROR, reason="Connection not registered")
            return
        
        user_id = connection_manager.connection_metadata[websocket]['user_id']
        message_type = message_data.get('type')
        
        if message_type == 'join_room':
            room_id = message_data.get('data', {}).get('room_id')
            if room_id:
                connection_manager.join_room(user_id, room_id)
                await websocket.send_json({
                    'type': 'room_joined',
                    'data': {'room_id': room_id},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        elif message_type == 'leave_room':
            room_id = message_data.get('data', {}).get('room_id')
            if room_id:
                connection_manager.leave_room(user_id, room_id)
                await websocket.send_json({
                    'type': 'room_left',
                    'data': {'room_id': room_id},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        elif message_type == 'pong':
            # Update last ping time
            connection_manager.connection_metadata[websocket]['last_ping'] = datetime.now(timezone.utc)
        
        else:
            # Unknown message type
            await websocket.send_json({
                'type': 'error',
                'data': {'message': f'Unknown message type: {message_type}'},
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await websocket.send_json({
            'type': 'error',
            'data': {'message': 'Internal server error'},
            'timestamp': datetime.now(timezone.utc).isoformat()
        })


async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint handler.
    
    Args:
        websocket: WebSocket connection
    """
    # Authenticate connection
    token_data = await authenticate_websocket(websocket)
    if not token_data:
        return
    
    # Register connection
    await connection_manager.connect(websocket, token_data.user_id, token_data)
    
    try:
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(heartbeat_loop(websocket))
        
        # Main message loop
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                
                # Parse message
                try:
                    message_data = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        'type': 'error',
                        'data': {'message': 'Invalid JSON format'},
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    continue
                
                # Handle message
                await handle_websocket_message(websocket, message_data)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket message loop: {e}")
                break
                
    finally:
        # Clean up
        heartbeat_task.cancel()
        connection_manager.disconnect(websocket)


async def heartbeat_loop(websocket: WebSocket):
    """
    Send periodic ping messages to keep connection alive.
    
    Args:
        websocket: WebSocket connection
    """
    try:
        while True:
            await asyncio.sleep(30)  # Send ping every 30 seconds
            await connection_manager.send_ping(websocket)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in heartbeat loop: {e}")
