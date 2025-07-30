#!/usr/bin/env python3
"""
Simple API testing script for Discord Ticket Bot.
Run this script to test basic API functionality.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional


class APITester:
    """Simple API testing class."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.session = requests.Session()
    
    def login(self, discord_id: int = 123456789, username: str = "test_user") -> bool:
        """Login and get JWT token."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"discord_id": discord_id, "username": username}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                print(f"✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_health(self) -> bool:
        """Test health endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_create_ticket(self) -> Optional[str]:
        """Test ticket creation."""
        try:
            ticket_data = {
                "title": "API Test Ticket",
                "description": "Testing ticket creation via API",
                "priority": "medium",
                "creator_discord_id": 123456789,
                "discord_channel_id": 987654321
            }
            
            response = self.session.post(
                f"{self.base_url}/api/tickets",
                json=ticket_data
            )
            
            if response.status_code == 201:
                data = response.json()
                ticket_id = data.get("id")
                print(f"✅ Ticket created: {ticket_id}")
                return ticket_id
            else:
                print(f"❌ Ticket creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Ticket creation error: {e}")
            return None


def main():
    """Run API tests."""
    print("🚀 Starting Discord Ticket Bot API Tests")
    print("=" * 50)
    
    tester = APITester()
    
    # Test health endpoint
    if not tester.test_health():
        print("❌ Health check failed - is the server running?")
        sys.exit(1)
    
    # Test authentication
    if not tester.login():
        print("❌ Authentication failed")
        sys.exit(1)
    
    # Test ticket creation
    ticket_id = tester.test_create_ticket()
    if not ticket_id:
        print("❌ Ticket creation failed")
        sys.exit(1)
    
    print("=" * 50)
    print("✅ All basic API tests passed!")
    print(f"📖 Visit {tester.base_url}/docs for full API documentation")


if __name__ == "__main__":
    main()