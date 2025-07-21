"""Tests for ticket API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Patch the database modules before importing app
with patch("backend.db.get_db_session"), \
     patch("backend.db.create_async_engine"), \
     patch("backend.db.create_engine"), \
     patch("backend.db.check_db_connection"):
    from backend.main import app
    from backend.models import Ticket, TicketStatus, Priority
    from backend.schemas import TicketCreate
    from backend.database_service import get_db_service


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_db_service():
    """Mock database service fixture."""
    # Create a mock database service
    db_service = AsyncMock()
    db_service.tickets = AsyncMock()
    db_service.messages = AsyncMock()
    
    # Create a dependency override
    app.dependency_overrides[get_db_service] = lambda: db_service
    
    yield db_service
    
    # Clean up the override after the test
    app.dependency_overrides = {}


def create_mock_ticket(ticket_id=None):
    """Create a mock ticket for testing."""
    if not ticket_id:
        ticket_id = uuid.uuid4()
    
    # Create a dictionary that matches the Ticket schema
    ticket_dict = {
        "id": str(ticket_id),
        "discord_channel_id": 123456789,
        "title": "Test Ticket",
        "description": "This is a test ticket",
        "status": TicketStatus.OPEN.value,
        "priority": Priority.MEDIUM.value,
        "creator_discord_id": 987654321,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "closed_at": None,
        "assigned_staff_id": None
    }
    
    # Create a mock object with attributes
    mock_ticket = MagicMock()
    for key, value in ticket_dict.items():
        setattr(mock_ticket, key, value)
    
    # Add dictionary-like access for JSON serialization
    mock_ticket.__getitem__ = lambda self, key: getattr(self, key)
    mock_ticket.copy = lambda: create_mock_ticket(ticket_id)
    mock_ticket.model_dump = lambda: ticket_dict
    
    return mock_ticket


class TestTicketAPI:
    """Test cases for ticket API endpoints."""
    
    def test_create_ticket_success(self, client, mock_db_service):
        """Test successful ticket creation."""
        # Setup
        mock_ticket = create_mock_ticket()
        mock_db_service.tickets.get_by_discord_channel_id.return_value = None
        mock_db_service.tickets.create.return_value = mock_ticket
        
        # Execute
        response = client.post(
            "/api/tickets",
            json={
                "title": "Test Ticket",
                "description": "This is a test ticket",
                "priority": "medium",
                "creator_discord_id": 987654321,
                "discord_channel_id": 123456789
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["title"] == "Test Ticket"
        assert response.json()["description"] == "This is a test ticket"
        assert response.json()["status"] == TicketStatus.OPEN.value
        assert response.json()["priority"] == Priority.MEDIUM.value
        assert response.json()["creator_discord_id"] == 987654321
        assert response.json()["discord_channel_id"] == 123456789
        
        # Verify mock calls
        mock_db_service.tickets.get_by_discord_channel_id.assert_called_once_with(123456789)
        mock_db_service.tickets.create.assert_called_once()
    
    def test_create_ticket_duplicate_channel(self, client, mock_db_service):
        """Test ticket creation with duplicate Discord channel ID."""
        # Setup
        mock_ticket = create_mock_ticket()
        mock_db_service.tickets.get_by_discord_channel_id.return_value = mock_ticket
        
        # Execute
        response = client.post(
            "/api/tickets",
            json={
                "title": "Test Ticket",
                "description": "This is a test ticket",
                "priority": "medium",
                "creator_discord_id": 987654321,
                "discord_channel_id": 123456789
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]
        
        # Verify mock calls
        mock_db_service.tickets.get_by_discord_channel_id.assert_called_once_with(123456789)
        mock_db_service.tickets.create.assert_not_called()
    
    def test_get_tickets_success(self, client, mock_db_service):
        """Test successful retrieval of tickets with pagination."""
        # Setup
        mock_tickets = [create_mock_ticket() for _ in range(3)]
        mock_db_service.tickets.search_tickets.return_value = mock_tickets
        mock_db_service.tickets.count.return_value = 3
        
        # Execute
        response = client.get("/api/tickets?page=1&size=10")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["items"]) == 3
        assert response.json()["total"] == 3
        assert response.json()["page"] == 1
        assert response.json()["size"] == 10
        assert response.json()["pages"] == 1
        
        # Verify mock calls
        mock_db_service.tickets.search_tickets.assert_called_once()
        mock_db_service.tickets.count.assert_called_once()
    
    def test_get_tickets_with_filters(self, client, mock_db_service):
        """Test retrieval of tickets with filters."""
        # Setup
        mock_tickets = [create_mock_ticket()]
        mock_db_service.tickets.search_tickets.return_value = mock_tickets
        mock_db_service.tickets.count.return_value = 1
        
        # Execute
        response = client.get(
            "/api/tickets?status=open&priority=medium&creator_id=987654321&page=1&size=10"
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["items"]) == 1
        
        # Verify mock calls with correct filters
        mock_db_service.tickets.search_tickets.assert_called_once()
        call_kwargs = mock_db_service.tickets.search_tickets.call_args.kwargs
        assert call_kwargs["status"] == TicketStatus.OPEN
        assert call_kwargs["priority"] == "medium"
        assert call_kwargs["creator_discord_id"] == 987654321
    
    def test_get_ticket_by_id_success(self, client, mock_db_service):
        """Test successful retrieval of a ticket by ID."""
        # Setup
        ticket_id = uuid.uuid4()
        mock_ticket = create_mock_ticket(ticket_id)
        # Add messages to the mock ticket
        mock_ticket["messages"] = []
        mock_db_service.tickets.get_with_messages.return_value = mock_ticket
        
        # Execute
        response = client.get(f"/api/tickets/{ticket_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(ticket_id)
        assert response.json()["title"] == "Test Ticket"
        assert "messages" in response.json()
        
        # Verify mock calls
        mock_db_service.tickets.get_with_messages.assert_called_once_with(ticket_id)
    
    def test_get_ticket_by_id_not_found(self, client, mock_db_service):
        """Test retrieval of a non-existent ticket."""
        # Setup
        ticket_id = uuid.uuid4()
        mock_db_service.tickets.get_with_messages.return_value = None
        
        # Execute
        response = client.get(f"/api/tickets/{ticket_id}")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
        
        # Verify mock calls
        mock_db_service.tickets.get_with_messages.assert_called_once_with(ticket_id)
        
    def test_update_ticket_success(self, client, mock_db_service):
        """Test successful ticket update."""
        # Setup
        ticket_id = uuid.uuid4()
        mock_ticket = create_mock_ticket(ticket_id)
        mock_db_service.tickets.get_by_id.return_value = mock_ticket
        
        # Updated ticket with new title and status
        updated_mock_ticket = mock_ticket.copy()
        setattr(updated_mock_ticket, "title", "Updated Ticket Title")
        setattr(updated_mock_ticket, "status", TicketStatus.IN_PROGRESS.value)
        mock_db_service.tickets.update.return_value = updated_mock_ticket
        
        # Execute
        response = client.put(
            f"/api/tickets/{ticket_id}",
            json={
                "title": "Updated Ticket Title",
                "status": "in_progress"
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "Updated Ticket Title"
        assert response.json()["status"] == TicketStatus.IN_PROGRESS.value
        
        # Verify mock calls
        mock_db_service.tickets.get_by_id.assert_called_once_with(ticket_id)
        mock_db_service.tickets.update.assert_called_once()
        update_kwargs = mock_db_service.tickets.update.call_args.kwargs
        assert update_kwargs["title"] == "Updated Ticket Title"
        assert update_kwargs["status"] == "in_progress"
    
    def test_update_ticket_not_found(self, client, mock_db_service):
        """Test updating a non-existent ticket."""
        # Setup
        ticket_id = uuid.uuid4()
        mock_db_service.tickets.get_by_id.return_value = None
        
        # Execute
        response = client.put(
            f"/api/tickets/{ticket_id}",
            json={
                "title": "Updated Ticket Title",
                "status": "in_progress"
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
        
        # Verify mock calls
        mock_db_service.tickets.get_by_id.assert_called_once_with(ticket_id)
        mock_db_service.tickets.update.assert_not_called()
    
    def test_close_ticket_success(self, client, mock_db_service):
        """Test successful ticket closure."""
        # Setup
        ticket_id = uuid.uuid4()
        mock_ticket = create_mock_ticket(ticket_id)
        mock_db_service.tickets.get_by_id.return_value = mock_ticket
        
        # Closed ticket
        closed_mock_ticket = mock_ticket.copy()
        setattr(closed_mock_ticket, "status", TicketStatus.CLOSED.value)
        setattr(closed_mock_ticket, "closed_at", datetime.utcnow().isoformat())
        mock_db_service.tickets.close_ticket.return_value = closed_mock_ticket
        
        # Execute
        response = client.delete(f"/api/tickets/{ticket_id}")
        
        # Debug output
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == TicketStatus.CLOSED.value
        assert response.json()["closed_at"] is not None
        
        # Verify mock calls
        mock_db_service.tickets.get_by_id.assert_called_once_with(ticket_id)
        mock_db_service.tickets.close_ticket.assert_called_once_with(ticket_id)
    
    def test_close_ticket_not_found(self, client, mock_db_service):
        """Test closing a non-existent ticket."""
        # Setup
        ticket_id = uuid.uuid4()
        mock_db_service.tickets.get_by_id.return_value = None
        
        # Execute
        response = client.delete(f"/api/tickets/{ticket_id}")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
        
        # Verify mock calls
        mock_db_service.tickets.get_by_id.assert_called_once_with(ticket_id)
        mock_db_service.tickets.close_ticket.assert_not_called()
    
    def test_close_ticket_already_closed(self, client, mock_db_service):
        """Test closing an already closed ticket."""
        # Setup
        ticket_id = uuid.uuid4()
        mock_ticket = create_mock_ticket(ticket_id)
        setattr(mock_ticket, "status", TicketStatus.CLOSED.value)
        setattr(mock_ticket, "closed_at", datetime.utcnow().isoformat())
        mock_db_service.tickets.get_by_id.return_value = mock_ticket
        
        # Execute
        response = client.delete(f"/api/tickets/{ticket_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == TicketStatus.CLOSED.value
        
        # Verify mock calls
        mock_db_service.tickets.get_by_id.assert_called_once_with(ticket_id)
        mock_db_service.tickets.close_ticket.assert_not_called()
    
    def test_add_message_success(self, client, mock_db_service):
        """Test successful message addition to a ticket."""
        # Setup
        ticket_id = uuid.uuid4()
        message_id = uuid.uuid4()
        
        # Mock ticket
        mock_ticket = create_mock_ticket(ticket_id)
        mock_db_service.tickets.get_by_id.return_value = mock_ticket
        
        # Mock message
        mock_message = MagicMock()
        setattr(mock_message, "id", str(message_id))
        setattr(mock_message, "ticket_id", str(ticket_id))
        setattr(mock_message, "content", "Test message content")
        setattr(mock_message, "author_discord_id", 987654321)
        setattr(mock_message, "discord_message_id", 123456789)
        setattr(mock_message, "message_type", "user_message")
        setattr(mock_message, "created_at", datetime.utcnow().isoformat())
        
        # Add dictionary-like access for JSON serialization
        mock_message.__getitem__ = lambda self, key: getattr(self, key)
        mock_message.model_dump = lambda: {
            "id": str(message_id),
            "ticket_id": str(ticket_id),
            "content": "Test message content",
            "author_discord_id": 987654321,
            "discord_message_id": 123456789,
            "message_type": "user_message",
            "created_at": mock_message.created_at
        }
        
        mock_db_service.messages.create.return_value = mock_message
        
        # Execute
        response = client.post(
            f"/api/tickets/{ticket_id}/messages",
            json={
                "ticket_id": str(ticket_id),
                "content": "Test message content",
                "author_discord_id": 987654321,
                "discord_message_id": 123456789,
                "message_type": "user_message"
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["content"] == "Test message content"
        assert response.json()["ticket_id"] == str(ticket_id)
        assert response.json()["author_discord_id"] == 987654321
        
        # Verify mock calls
        mock_db_service.tickets.get_by_id.assert_called_once_with(ticket_id)
        mock_db_service.messages.create.assert_called_once()
        mock_db_service.tickets.update.assert_called_once()
    
    def test_add_message_ticket_not_found(self, client, mock_db_service):
        """Test adding a message to a non-existent ticket."""
        # Setup
        ticket_id = uuid.uuid4()
        mock_db_service.tickets.get_by_id.return_value = None
        
        # Execute
        response = client.post(
            f"/api/tickets/{ticket_id}/messages",
            json={
                "ticket_id": str(ticket_id),
                "content": "Test message content",
                "author_discord_id": 987654321,
                "discord_message_id": 123456789,
                "message_type": "user_message"
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
        
        # Verify mock calls
        mock_db_service.tickets.get_by_id.assert_called_once_with(ticket_id)
        mock_db_service.messages.create.assert_not_called()
    
    def test_add_message_to_closed_ticket(self, client, mock_db_service):
        """Test adding a message to a closed ticket."""
        # Setup
        ticket_id = uuid.uuid4()
        
        # Mock closed ticket
        mock_ticket = create_mock_ticket(ticket_id)
        setattr(mock_ticket, "status", TicketStatus.CLOSED.value)
        setattr(mock_ticket, "closed_at", datetime.utcnow().isoformat())
        mock_db_service.tickets.get_by_id.return_value = mock_ticket
        
        # Execute
        response = client.post(
            f"/api/tickets/{ticket_id}/messages",
            json={
                "ticket_id": str(ticket_id),
                "content": "Test message content",
                "author_discord_id": 987654321,
                "discord_message_id": 123456789,
                "message_type": "user_message"
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "closed ticket" in response.json()["detail"]
        
        # Verify mock calls
        mock_db_service.tickets.get_by_id.assert_called_once_with(ticket_id)
        mock_db_service.messages.create.assert_not_called()