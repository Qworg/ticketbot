#!/usr/bin/env python3
"""
Manual test for ticket creation endpoint.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.main import app
from fastapi.testclient import TestClient

def test_ticket_endpoint():
    """Test that the ticket endpoint exists and responds correctly."""
    client = TestClient(app)
    
    print("Testing ticket creation endpoint...")
    
    # Test health endpoint first
    health_response = client.get('/health')
    print(f"Health check: {health_response.status_code} - {health_response.json()}")
    
    # Test ticket endpoint without auth (should return 401)
    ticket_response = client.post('/api/tickets', json={
        "guild_id": 123456789012345678,
        "creator_id": 987654321098765432,
        "reason": "I need help with my account",
        "category": "Support"
    })
    print(f"Ticket endpoint (no auth): {ticket_response.status_code}")
    
    if ticket_response.status_code == 401:
        print("✓ Endpoint exists and correctly requires authentication")
    elif ticket_response.status_code == 422:
        print("✓ Endpoint exists and is validating request data")
    else:
        print(f"? Unexpected response: {ticket_response.text}")
    
    # Test with invalid data to check validation
    invalid_response = client.post('/api/tickets', json={
        "guild_id": 123,  # Too short
        "creator_id": 987654321098765432,
        "reason": "Hi",  # Too short
    })
    print(f"Invalid data test: {invalid_response.status_code}")
    
    if invalid_response.status_code == 422:
        print("✓ Request validation is working")
    elif invalid_response.status_code == 401:
        print("✓ Authentication happens before validation (also correct)")
    
    print("Ticket endpoint tests completed!")

if __name__ == "__main__":
    test_ticket_endpoint()
