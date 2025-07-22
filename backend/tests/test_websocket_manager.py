"""Tests for WebSocket manager."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from fastapi import WebSocket, WebSocketDisconnect

from backend.services.websocket_manager import ConnectionManager
from backend.services.redis_service import EventType


@pytest.fixture
def websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def connection_manager():
    """Create a connection manager."""
    return ConnectionManager()


@pytest.mark.asyncio
async def test_connect(connection_manager, websocket):
    """Test connecting a WebSocket."""
    # Arrange
    connection_id = "test_connection"
    user_id = 123456789
    
    # Act
    await connection_manager.connect(websocket, connection_id, user_id)
    
    # Assert
    assert connection_id in connection_manager.active_connections
    assert user_id in connection_manager.user_connections
    assert connection_id in connection_manager.user_connections[user_id]
    websocket.accept.assert_called_once()
    websocket.send_json.assert_called_once()


def test_disconnect(connection_manager, websocket):
    """Test disconnecting a WebSocket."""
    # Arrange
    connection_id = "test_connection"
    user_id = 123456789
    ticket_id = uuid4()
    
    # Setup connections
    connection_manager.active_connections[connection_id] = websocket
    connection_manager.user_connections[user_id] = {connection_id}
    connection_manager.ticket_subscribers[ticket_id] = {connection_id}
    
    # Act
    connection_manager.disconnect(connection_id)
    
    # Assert
    assert connection_id not in connection_manager.active_connections
    assert user_id not in connection_manager.user_connections
    assert ticket_id not in connection_manager.ticket_subscribers


@pytest.mark.asyncio
async def test_send_personal_message(connection_manager, websocket):
    """Test sending a personal message."""
    # Arrange
    connection_id = "test_connection"
    message = {"type": "test", "data": "test_data"}
    connection_manager.active_connections[connection_id] = websocket
    
    # Act
    result = await connection_manager.send_personal_message(message, connection_id)
    
    # Assert
    assert result is True
    websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast(connection_manager):
    """Test broadcasting a message to all connections."""
    # Arrange
    message = {"type": "test", "data": "test_data"}
    
    # Create multiple mock WebSockets
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    ws3 = AsyncMock()
    
    connection_manager.active_connections = {
        "conn1": ws1,
        "conn2": ws2,
        "conn3": ws3
    }
    
    # Act
    await connection_manager.broadcast(message)
    
    # Assert
    ws1.send_json.assert_called_once_with(message)
    ws2.send_json.assert_called_once_with(message)
    ws3.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_to_users(connection_manager):
    """Test broadcasting a message to specific users."""
    # Arrange
    message = {"type": "test", "data": "test_data"}
    user_ids = [123, 456]
    
    # Create mock WebSockets
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    ws3 = AsyncMock()
    
    # Setup connections
    connection_manager.active_connections = {
        "conn1": ws1,
        "conn2": ws2,
        "conn3": ws3
    }
    connection_manager.user_connections = {
        123: {"conn1"},
        456: {"conn2"},
        789: {"conn3"}
    }
    
    # Act
    await connection_manager.broadcast_to_users(message, user_ids)
    
    # Assert
    ws1.send_json.assert_called_once_with(message)
    ws2.send_json.assert_called_once_with(message)
    ws3.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_to_ticket_subscribers(connection_manager):
    """Test broadcasting a message to ticket subscribers."""
    # Arrange
    message = {"type": "test", "data": "test_data"}
    ticket_id = uuid4()
    other_ticket_id = uuid4()
    
    # Create mock WebSockets
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    ws3 = AsyncMock()
    
    # Setup connections
    connection_manager.active_connections = {
        "conn1": ws1,
        "conn2": ws2,
        "conn3": ws3
    }
    connection_manager.ticket_subscribers = {
        ticket_id: {"conn1", "conn2"},
        other_ticket_id: {"conn3"}
    }
    
    # Act
    await connection_manager.broadcast_to_ticket_subscribers(message, ticket_id)
    
    # Assert
    ws1.send_json.assert_called_once_with(message)
    ws2.send_json.assert_called_once_with(message)
    ws3.send_json.assert_not_called()


def test_subscribe_to_ticket(connection_manager, websocket):
    """Test subscribing to a ticket."""
    # Arrange
    connection_id = "test_connection"
    ticket_id = uuid4()
    connection_manager.active_connections[connection_id] = websocket
    
    # Act
    result = connection_manager.subscribe_to_ticket(connection_id, ticket_id)
    
    # Assert
    assert result is True
    assert ticket_id in connection_manager.ticket_subscribers
    assert connection_id in connection_manager.ticket_subscribers[ticket_id]


def test_unsubscribe_from_ticket(connection_manager, websocket):
    """Test unsubscribing from a ticket."""
    # Arrange
    connection_id = "test_connection"
    ticket_id = uuid4()
    connection_manager.active_connections[connection_id] = websocket
    connection_manager.ticket_subscribers[ticket_id] = {connection_id}
    
    # Act
    result = connection_manager.unsubscribe_from_ticket(connection_id, ticket_id)
    
    # Assert
    assert result is True
    assert ticket_id not in connection_manager.ticket_subscribers


@pytest.mark.asyncio
async def test_handle_ticket_event(connection_manager):
    """Test handling a ticket event."""
    # Arrange
    event_type = EventType.TICKET_CREATED
    ticket_id = uuid4()
    data = {
        "id": str(ticket_id),
        "title": "Test Ticket",
        "creator_discord_id": 123456789,
        "assigned_staff_id": 987654321
    }
    
    # Mock methods
    connection_manager.broadcast_to_ticket_subscribers = AsyncMock()
    connection_manager.broadcast_to_users = AsyncMock()
    
    # Act
    await connection_manager.handle_ticket_event(event_type, data)
    
    # Assert
    connection_manager.broadcast_to_ticket_subscribers.assert_called_once()
    connection_manager.broadcast_to_users.assert_called_once()
    
    # Verify the message format
    ticket_call = connection_manager.broadcast_to_ticket_subscribers.call_args
    assert ticket_call[0][0]["type"] == event_type
    assert ticket_call[0][0]["data"] == data
    assert ticket_call[0][1] == ticket_id
    
    # Verify user IDs
    user_call = connection_manager.broadcast_to_users.call_args
    assert user_call[0][1] == [123456789, 987654321]


@pytest.mark.asyncio
async def test_handle_message_event(connection_manager):
    """Test handling a message event."""
    # Arrange
    event_type = EventType.MESSAGE_CREATED
    ticket_id = uuid4()
    data = {
        "id": str(uuid4()),
        "ticket_id": str(ticket_id),
        "content": "Test message",
        "author_discord_id": 123456789
    }
    
    # Mock methods
    connection_manager.broadcast_to_ticket_subscribers = AsyncMock()
    connection_manager.broadcast_to_users = AsyncMock()
    
    # Act
    await connection_manager.handle_message_event(event_type, data)
    
    # Assert
    connection_manager.broadcast_to_ticket_subscribers.assert_called_once()
    connection_manager.broadcast_to_users.assert_called_once()
    
    # Verify the message format
    ticket_call = connection_manager.broadcast_to_ticket_subscribers.call_args
    assert ticket_call[0][0]["type"] == event_type
    assert ticket_call[0][0]["data"] == data
    assert ticket_call[0][1] == ticket_id
    
    # Verify user IDs
    user_call = connection_manager.broadcast_to_users.call_args
    assert user_call[0][1] == [123456789]