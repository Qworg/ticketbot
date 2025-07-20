"""Tests for ticket API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

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
    return {
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