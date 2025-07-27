"""
Integration tests for API endpoints with test database.
Tests complete API workflows and external system integration.
"""
import pytest
import httpx
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime
import json

from backend.main import app
from .test_database_service import TestDatabaseService, get_test_database_service
from .test_redis_service import TestRedisService


@pytest.fixture
def test_client():
    """Create test client for API integration tests."""
    return TestClient(app)


@pytest.fixture
async def api_integration_setup():
    """Set up API integration test environment."""
    async with get_test_database_service() as db_service:
        # Initialize services
        redis_service = TestRedisService()
        
        # Create test database tables
        await db_service.create_tables()
        
        # Create test staff for authentication
        staff_data = {
            "discord_id": 123456789,
            "username": "api_test_staff",
            "role": "admin",
            "permissions": {"can_close_tickets": True, "can_assign_tickets": True}
        }
        staff = await db_service.create_staff(staff_data)
        
        # Generate test JWT token
        from .mock_services import MockAuthService
        auth_service = MockAuthService(db_service)
        token = await auth_service.create_access_token(staff.discord_id)
        
        yield {
            "db_service": db_service,
            "redis_service": redis_service,
            "staff": staff,
            "token": token
        }
        
        # Cleanup
        await db_service.cleanup()
        await redis_service.cleanup()


@pytest.mark.asyncio
async def test_api_ticket_crud_workflow(test_client, api_integration_setup):
    """Test complete CRUD workflow through API endpoints."""
    setup = api_integration_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Step 1: Create ticket via API
    ticket_data = {
        "discord_channel_id": 987654321,
        "title": "API Test Ticket",
        "description": "Testing API integration",
        "creator_discord_id": 111222333,
        "priority": "medium"
    }
    
    response = test_client.post("/api/tickets", json=ticket_data, headers=headers)
    assert response.status_code == 201
    created_ticket = response.json()
    ticket_id = created_ticket["id"]
    
    assert created_ticket["title"] == "API Test Ticket"
    assert created_ticket["status"] == "open"
    assert created_ticket["priority"] == "medium"
    
    # Step 2: Get ticket via API
    response = test_client.get(f"/api/tickets/{ticket_id}", headers=headers)
    assert response.status_code == 200
    retrieved_ticket = response.json()
    assert retrieved_ticket["id"] == ticket_id
    assert retrieved_ticket["title"] == "API Test Ticket"
    
    # Step 3: Update ticket via API
    update_data = {
        "status": "in_progress",
        "assigned_staff_id": setup["staff"].discord_id,
        "priority": "high"
    }
    
    response = test_client.put(f"/api/tickets/{ticket_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    updated_ticket = response.json()
    assert updated_ticket["status"] == "in_progress"
    assert updated_ticket["assigned_staff_id"] == setup["staff"].discord_id
    assert updated_ticket["priority"] == "high"
    
    # Step 4: Add message via API
    message_data = {
        "author_discord_id": 111222333,
        "content": "This is a test message via API",
        "message_type": "user_message"
    }
    
    response = test_client.post(f"/api/tickets/{ticket_id}/messages", json=message_data, headers=headers)
    assert response.status_code == 201
    created_message = response.json()
    assert created_message["content"] == "This is a test message via API"
    assert created_message["ticket_id"] == ticket_id
    
    # Step 5: Get updated ticket with messages
    response = test_client.get(f"/api/tickets/{ticket_id}", headers=headers)
    assert response.status_code == 200
    ticket_with_messages = response.json()
    assert len(ticket_with_messages["messages"]) == 1
    assert ticket_with_messages["messages"][0]["content"] == "This is a test message via API"
    
    # Step 6: List tickets with filtering
    response = test_client.get("/api/tickets?status=in_progress", headers=headers)
    assert response.status_code == 200
    tickets_list = response.json()
    assert len(tickets_list["tickets"]) >= 1
    assert any(ticket["id"] == ticket_id for ticket in tickets_list["tickets"])
    
    # Step 7: Close ticket via API
    close_data = {"status": "closed"}
    response = test_client.put(f"/api/tickets/{ticket_id}", json=close_data, headers=headers)
    assert response.status_code == 200
    closed_ticket = response.json()
    assert closed_ticket["status"] == "closed"
    assert closed_ticket["closed_at"] is not None


@pytest.mark.asyncio
async def test_api_transcript_workflow(test_client, api_integration_setup):
    """Test transcript generation and search through API."""
    setup = api_integration_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Create ticket with messages
    ticket_data = {
        "discord_channel_id": 987654322,
        "title": "Transcript Test Ticket",
        "description": "Testing transcript API",
        "creator_discord_id": 111222334
    }
    
    response = test_client.post("/api/tickets", json=ticket_data, headers=headers)
    ticket_id = response.json()["id"]
    
    # Add multiple messages
    messages = [
        {"author_discord_id": 111222334, "content": "I need help with billing", "message_type": "user_message"},
        {"author_discord_id": setup["staff"].discord_id, "content": "I can help with billing issues", "message_type": "staff_message"},
        {"author_discord_id": 111222334, "content": "My invoice is incorrect", "message_type": "user_message"}
    ]
    
    for msg_data in messages:
        response = test_client.post(f"/api/tickets/{ticket_id}/messages", json=msg_data, headers=headers)
        assert response.status_code == 201
    
    # Generate transcript
    response = test_client.get(f"/api/tickets/{ticket_id}/transcript", headers=headers)
    assert response.status_code == 200
    transcript = response.json()
    assert "I need help with billing" in transcript["content"]
    assert "I can help with billing issues" in transcript["content"]
    assert "My invoice is incorrect" in transcript["content"]
    
    # Search transcripts
    response = test_client.get("/api/search/transcripts?query=billing", headers=headers)
    assert response.status_code == 200
    search_results = response.json()
    assert len(search_results["results"]) >= 1
    assert any(result["ticket_id"] == ticket_id for result in search_results["results"])
    
    # Test transcript sharing
    share_data = {"expires_in_hours": 24}
    response = test_client.post(f"/api/tickets/{ticket_id}/transcript/share", json=share_data, headers=headers)
    assert response.status_code == 200
    share_response = response.json()
    assert "share_token" in share_response
    assert "share_url" in share_response
    
    # Access shared transcript (no auth required)
    share_token = share_response["share_token"]
    response = test_client.get(f"/api/transcripts/shared/{share_token}")
    assert response.status_code == 200
    shared_transcript = response.json()
    assert "I need help with billing" in shared_transcript["content"]


@pytest.mark.asyncio
async def test_api_authentication_and_authorization(test_client, api_integration_setup):
    """Test API authentication and authorization workflows."""
    setup = api_integration_setup
    valid_headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Test valid authentication
    response = test_client.get("/api/tickets", headers=valid_headers)
    assert response.status_code == 200
    
    # Test missing authentication
    response = test_client.get("/api/tickets")
    assert response.status_code == 401
    
    # Test invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    response = test_client.get("/api/tickets", headers=invalid_headers)
    assert response.status_code == 401
    
    # Test expired token
    from .mock_services import MockAuthService
    auth_service = MockAuthService(setup["db_service"])
    expired_token = await auth_service.create_access_token(setup["staff"].discord_id, expires_delta=-3600)  # Expired 1 hour ago
    expired_headers = {"Authorization": f"Bearer {expired_token}"}
    response = test_client.get("/api/tickets", headers=expired_headers)
    assert response.status_code == 401
    
    # Test API key authentication
    api_key = "test_api_key_12345"
    api_key_headers = {"X-API-Key": api_key}
    
    # Mock API key validation
    with patch('backend.services.auth_service.AuthService.validate_api_key', return_value=True):
        response = test_client.get("/api/tickets", headers=api_key_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_error_handling(test_client, api_integration_setup):
    """Test API error handling and response formats."""
    setup = api_integration_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Test 404 for non-existent ticket
    response = test_client.get("/api/tickets/non-existent-id", headers=headers)
    assert response.status_code == 404
    error_response = response.json()
    assert "detail" in error_response
    assert "not found" in error_response["detail"].lower()
    
    # Test 400 for invalid data
    invalid_ticket_data = {
        "discord_channel_id": "invalid_id",  # Should be integer
        "title": "",  # Should not be empty
        "creator_discord_id": "invalid"  # Should be integer
    }
    
    response = test_client.post("/api/tickets", json=invalid_ticket_data, headers=headers)
    assert response.status_code == 422  # Validation error
    error_response = response.json()
    assert "detail" in error_response
    
    # Test 409 for duplicate channel ID
    ticket_data = {
        "discord_channel_id": 987654323,
        "title": "First Ticket",
        "description": "First ticket",
        "creator_discord_id": 111222335
    }
    
    # Create first ticket
    response = test_client.post("/api/tickets", json=ticket_data, headers=headers)
    assert response.status_code == 201
    
    # Try to create duplicate
    response = test_client.post("/api/tickets", json=ticket_data, headers=headers)
    assert response.status_code == 409  # Conflict
    error_response = response.json()
    assert "already exists" in error_response["detail"].lower()


@pytest.mark.asyncio
async def test_api_pagination_and_filtering(test_client, api_integration_setup):
    """Test API pagination and filtering functionality."""
    setup = api_integration_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Create multiple tickets with different statuses
    tickets_data = [
        {"discord_channel_id": 987654330 + i, "title": f"Test Ticket {i}", "description": f"Description {i}", 
         "creator_discord_id": 111222340 + i, "priority": "high" if i % 2 == 0 else "low"}
        for i in range(10)
    ]
    
    created_tickets = []
    for ticket_data in tickets_data:
        response = test_client.post("/api/tickets", json=ticket_data, headers=headers)
        assert response.status_code == 201
        created_tickets.append(response.json())
    
    # Update some tickets to different statuses
    for i, ticket in enumerate(created_tickets[:5]):
        update_data = {"status": "in_progress" if i % 2 == 0 else "closed"}
        response = test_client.put(f"/api/tickets/{ticket['id']}", json=update_data, headers=headers)
        assert response.status_code == 200
    
    # Test pagination
    response = test_client.get("/api/tickets?page=1&limit=5", headers=headers)
    assert response.status_code == 200
    page1_response = response.json()
    assert len(page1_response["tickets"]) == 5
    assert page1_response["pagination"]["page"] == 1
    assert page1_response["pagination"]["limit"] == 5
    assert page1_response["pagination"]["total"] >= 10
    
    # Test filtering by status
    response = test_client.get("/api/tickets?status=open", headers=headers)
    assert response.status_code == 200
    open_tickets = response.json()
    assert all(ticket["status"] == "open" for ticket in open_tickets["tickets"])
    
    # Test filtering by priority
    response = test_client.get("/api/tickets?priority=high", headers=headers)
    assert response.status_code == 200
    high_priority_tickets = response.json()
    assert all(ticket["priority"] == "high" for ticket in high_priority_tickets["tickets"])
    
    # Test combined filtering
    response = test_client.get("/api/tickets?status=in_progress&priority=high", headers=headers)
    assert response.status_code == 200
    filtered_tickets = response.json()
    assert all(ticket["status"] == "in_progress" and ticket["priority"] == "high" 
              for ticket in filtered_tickets["tickets"])


@pytest.mark.asyncio
async def test_api_rate_limiting(test_client, api_integration_setup):
    """Test API rate limiting functionality."""
    setup = api_integration_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Mock rate limiting
    with patch('backend.middleware.rate_limit.RateLimiter.is_allowed', side_effect=[True] * 5 + [False] * 5):
        # First 5 requests should succeed
        for i in range(5):
            response = test_client.get("/api/tickets", headers=headers)
            assert response.status_code == 200
        
        # Next 5 requests should be rate limited
        for i in range(5):
            response = test_client.get("/api/tickets", headers=headers)
            assert response.status_code == 429  # Too Many Requests
            assert "rate limit" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_websocket_integration(test_client, api_integration_setup):
    """Test WebSocket integration with API operations."""
    setup = api_integration_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # Mock WebSocket manager
    websocket_events = []
    
    async def mock_broadcast(event_type, data):
        websocket_events.append({"type": event_type, "data": data})
    
    with patch('backend.services.websocket_manager.WebSocketManager.broadcast', side_effect=mock_broadcast):
        # Create ticket (should trigger WebSocket event)
        ticket_data = {
            "discord_channel_id": 987654350,
            "title": "WebSocket Test Ticket",
            "description": "Testing WebSocket integration",
            "creator_discord_id": 111222350
        }
        
        response = test_client.post("/api/tickets", json=ticket_data, headers=headers)
        assert response.status_code == 201
        ticket_id = response.json()["id"]
        
        # Add message (should trigger WebSocket event)
        message_data = {
            "author_discord_id": 111222350,
            "content": "WebSocket test message",
            "message_type": "user_message"
        }
        
        response = test_client.post(f"/api/tickets/{ticket_id}/messages", json=message_data, headers=headers)
        assert response.status_code == 201
        
        # Verify WebSocket events were triggered
        assert len(websocket_events) >= 2
        event_types = [event["type"] for event in websocket_events]
        assert "ticket_created" in event_types
        assert "message_added" in event_types