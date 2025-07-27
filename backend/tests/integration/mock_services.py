"""
Mock services for integration testing.
Provides mock implementations of services that may not be fully implemented.
"""
from unittest.mock import AsyncMock
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid


class MockTicketService:
    """Mock ticket service for integration testing."""
    
    def __init__(self, db_service, redis_service):
        self.db_service = db_service
        self.redis_service = redis_service
        self._tickets = {}
        self._messages = {}
    
    async def create_ticket(self, ticket_data):
        """Mock create ticket."""
        ticket_id = str(uuid.uuid4())
        ticket = {
            "id": ticket_id,
            "discord_channel_id": ticket_data.discord_channel_id,
            "title": ticket_data.title,
            "description": ticket_data.description,
            "creator_discord_id": ticket_data.creator_discord_id,
            "status": "open",
            "priority": getattr(ticket_data, 'priority', 'medium'),
            "assigned_staff_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "closed_at": None,
            "messages": []
        }
        self._tickets[ticket_id] = ticket
        
        # Publish event
        await self.redis_service.publish("ticket_events", f'{{"type": "ticket_created", "data": {{"ticket_id": "{ticket_id}"}}}}')
        
        return type('Ticket', (), ticket)
    
    async def get_ticket(self, ticket_id: str):
        """Mock get ticket."""
        if ticket_id in self._tickets:
            ticket_data = self._tickets[ticket_id]
            ticket_data["messages"] = [self._messages[msg_id] for msg_id in ticket_data.get("message_ids", [])]
            return type('Ticket', (), ticket_data)
        return None
    
    async def update_ticket(self, ticket_id: str, update_data):
        """Mock update ticket."""
        if ticket_id not in self._tickets:
            return None
        
        ticket = self._tickets[ticket_id]
        
        if hasattr(update_data, 'status'):
            ticket["status"] = update_data.status
            if update_data.status == "closed":
                ticket["closed_at"] = datetime.utcnow()
        
        if hasattr(update_data, 'assigned_staff_id'):
            ticket["assigned_staff_id"] = update_data.assigned_staff_id
        
        if hasattr(update_data, 'priority'):
            ticket["priority"] = update_data.priority
        
        ticket["updated_at"] = datetime.utcnow()
        
        # Publish event
        await self.redis_service.publish("ticket_events", f'{{"type": "ticket_updated", "data": {{"ticket_id": "{ticket_id}"}}}}')
        
        return type('Ticket', (), ticket)
    
    async def add_message(self, message_data):
        """Mock add message."""
        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "ticket_id": message_data.ticket_id,
            "author_discord_id": message_data.author_discord_id,
            "content": message_data.content,
            "message_type": message_data.message_type,
            "discord_message_id": getattr(message_data, 'discord_message_id', None),
            "created_at": datetime.utcnow()
        }
        self._messages[message_id] = message
        
        # Add to ticket
        if message_data.ticket_id in self._tickets:
            if "message_ids" not in self._tickets[message_data.ticket_id]:
                self._tickets[message_data.ticket_id]["message_ids"] = []
            self._tickets[message_data.ticket_id]["message_ids"].append(message_id)
        
        # Publish event
        await self.redis_service.publish("ticket_events", f'{{"type": "message_added", "data": {{"message_id": "{message_id}"}}}}')
        
        return type('Message', (), message)
    
    async def get_ticket_history(self, ticket_id: str):
        """Mock get ticket history."""
        return [
            {"action": "created", "timestamp": datetime.utcnow()},
            {"action": "updated", "timestamp": datetime.utcnow()}
        ]


class MockTranscriptService:
    """Mock transcript service for integration testing."""
    
    def __init__(self, db_service):
        self.db_service = db_service
        self._transcripts = {}
    
    async def generate_transcript(self, ticket_id: str):
        """Mock generate transcript."""
        transcript_id = str(uuid.uuid4())
        transcript = {
            "id": transcript_id,
            "ticket_id": ticket_id,
            "content": f"Transcript content for ticket {ticket_id}",
            "formatted_content": {"messages": []},
            "created_at": datetime.utcnow()
        }
        self._transcripts[transcript_id] = transcript
        return type('Transcript', (), transcript)
    
    async def search_transcripts(self, query: str, limit: int = 10):
        """Mock search transcripts."""
        results = []
        for transcript in self._transcripts.values():
            if query.lower() in transcript["content"].lower():
                results.append(type('TranscriptSearchResult', (), {
                    "ticket_id": transcript["ticket_id"],
                    "content": transcript["content"],
                    "highlight": transcript["content"].replace(query, f"<mark>{query}</mark>")
                }))
        return results[:limit]


class MockAuthService:
    """Mock auth service for integration testing."""
    
    def __init__(self, db_service):
        self.db_service = db_service
    
    async def create_access_token(self, user_id: int, expires_delta: Optional[int] = None):
        """Mock create access token."""
        if expires_delta and expires_delta < 0:
            # Return expired token
            return "expired_token_12345"
        return f"test_token_{user_id}"
    
    async def validate_api_key(self, api_key: str):
        """Mock validate API key."""
        return api_key == "test_api_key_12345"
    
    async def can_access_ticket(self, user_id: int, ticket_id: str):
        """Mock can access ticket."""
        # Admin can access all tickets
        if user_id == 123456790:  # admin_staff from tests
            return True
        # Regular staff can only access assigned tickets
        return False
    
    async def has_permission(self, user_id: int, permission: str):
        """Mock has permission."""
        # Admin has all permissions
        if user_id == 123456790:  # admin_staff from tests
            return True
        # Regular staff has limited permissions
        if user_id == 123456791:  # regular_staff from tests
            return permission not in ["can_close_tickets", "can_assign_tickets"]
        return True