"""Tests for transcript service business logic."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from backend.services.transcript_service import TranscriptService
from backend.database_service import DatabaseService
from backend.models import TicketStatus, MessageType, StaffRole
from backend.tests.test_database_service import test_engine, test_session, db_service


@pytest.fixture
async def transcript_service(db_service: DatabaseService) -> TranscriptService:
    """Create transcript service for testing."""
    return TranscriptService(db_service)


@pytest.fixture
async def sample_ticket(db_service: DatabaseService):
    """Create a sample ticket with messages for testing."""
    # Create a ticket
    ticket = await db_service.tickets.create(
        discord_channel_id=123456789,
        title="Test Ticket",
        description="This is a test ticket",
        creator_discord_id=987654321,
        status=TicketStatus.OPEN.value
    )
    
    # Add messages to the ticket
    await db_service.messages.create(
        ticket_id=ticket.id,
        author_discord_id=987654321,
        content="Hello, I need help with something",
        message_type=MessageType.USER_MESSAGE.value
    )
    
    await db_service.messages.create(
        ticket_id=ticket.id,
        author_discord_id=111222333,
        content="I'll help you with that",
        message_type=MessageType.STAFF_MESSAGE.value
    )
    
    await db_service.messages.create(
        ticket_id=ticket.id,
        author_discord_id=0,
        content="Ticket status changed from open to in_progress",
        message_type=MessageType.SYSTEM_MESSAGE.value
    )
    
    await db_service.commit()
    return ticket


class TestTranscriptService:
    """Test transcript service business logic."""
    
    async def test_generate_transcript(self, transcript_service: TranscriptService, sample_ticket):
        """Test generating a transcript for a ticket."""
        transcript = await transcript_service.generate_transcript(sample_ticket.id)
        
        assert transcript is not None
        assert transcript.ticket_id == sample_ticket.id
        assert transcript.content is not None
        assert "Test Ticket" in transcript.content
        assert "Hello, I need help with something" in transcript.content
        assert "I'll help you with that" in transcript.content
        assert "Ticket status changed" in transcript.content
        assert transcript.share_token is not None
    
    async def test_generate_transcript_without_system_messages(self, transcript_service: TranscriptService, sample_ticket):
        """Test generating a transcript without system messages."""
        transcript = await transcript_service.generate_transcript(
            sample_ticket.id, include_system_messages=False
        )
        
        assert transcript is not None
        assert "Hello, I need help with something" in transcript.content
        assert "I'll help you with that" in transcript.content
        assert "Ticket status changed" not in transcript.content
    
    async def test_get_transcript_by_ticket(self, transcript_service: TranscriptService, sample_ticket):
        """Test getting a transcript by ticket ID."""
        # First generate a transcript
        await transcript_service.generate_transcript(sample_ticket.id)
        
        # Then retrieve it
        transcript = await transcript_service.get_transcript_by_ticket(sample_ticket.id)
        
        assert transcript is not None
        assert transcript.ticket_id == sample_ticket.id
    
    async def test_get_transcript_by_share_token(self, transcript_service: TranscriptService, sample_ticket):
        """Test getting a transcript by share token."""
        # First generate a transcript
        created_transcript = await transcript_service.generate_transcript(sample_ticket.id)
        
        # Then retrieve it by share token
        transcript = await transcript_service.get_transcript_by_share_token(created_transcript.share_token)
        
        assert transcript is not None
        assert transcript.id == created_transcript.id
        assert transcript.share_token == created_transcript.share_token
    
    async def test_regenerate_transcript(self, transcript_service: TranscriptService, sample_ticket, db_service: DatabaseService):
        """Test regenerating a transcript after adding new messages."""
        # First generate a transcript
        original_transcript = await transcript_service.generate_transcript(sample_ticket.id)
        
        # Add a new message
        new_message = await db_service.messages.create(
            ticket_id=sample_ticket.id,
            author_discord_id=987654321,
            content="I have another question",
            message_type=MessageType.USER_MESSAGE.value
        )
        await db_service.commit()
        
        # Regenerate the transcript
        updated_transcript = await transcript_service.regenerate_transcript(sample_ticket.id)
        
        assert updated_transcript is not None
        assert updated_transcript.id == original_transcript.id
    
    async def test_generate_share_token(self, transcript_service: TranscriptService, sample_ticket):
        """Test generating a new share token for a transcript."""
        # First generate a transcript
        transcript = await transcript_service.generate_transcript(sample_ticket.id)
        original_token = transcript.share_token
        
        # Generate a new share token
        new_token = await transcript_service.generate_share_token(transcript.id)
        
        assert new_token is not None
        assert new_token != original_token
        
        # Verify the token was updated in the database
        updated_transcript = await transcript_service.get_transcript(transcript.id)
        assert updated_transcript.share_token == new_token
    
    async def test_revoke_share_token(self, transcript_service: TranscriptService, sample_ticket):
        """Test revoking a share token."""
        # First generate a transcript
        transcript = await transcript_service.generate_transcript(sample_ticket.id)
        assert transcript.share_token is not None
        
        # Revoke the share token
        success = await transcript_service.revoke_share_token(transcript.id)
        
        assert success is True
        
        # Verify the token was revoked
        updated_transcript = await transcript_service.get_transcript(transcript.id)
        assert updated_transcript.share_token is None
    
    async def test_highlight_search_matches(self, transcript_service: TranscriptService):
        """Test highlighting search matches in text."""
        text = "This is a test message with important information."
        search_term = "important"
        
        highlighted = transcript_service._highlight_search_matches(text, search_term)
        
        assert highlighted == "This is a test message with <mark>important</mark> information."
    
    async def test_extract_context_snippets(self, transcript_service: TranscriptService):
        """Test extracting context snippets around search matches."""
        text = "This is the first paragraph with important information.\n\nThis is the second paragraph with more important details."
        search_term = "important"
        
        snippets = transcript_service._extract_context_snippets(text, search_term, context_chars=20)
        
        assert len(snippets) == 2
        assert "<mark>important</mark>" in snippets[0]
        assert "<mark>important</mark>" in snippets[1]
        # Check for partial matches since we're using context_chars
        assert "paragraph with" in snippets[0]
        assert "paragraph with" in snippets[1]
    
    async def test_search_transcripts(self, transcript_service: TranscriptService, sample_ticket):
        """Test searching transcripts."""
        # First generate a transcript
        await transcript_service.generate_transcript(sample_ticket.id)
        
        # Search for a term that should be in the transcript
        results, count = await transcript_service.search_transcripts(
            search_term="help",
            highlight_results=True
        )
        
        assert count > 0
        assert len(results) > 0
        assert "<mark>help</mark>" in results[0]["content"]
        assert "context_snippets" in results[0]
        assert len(results[0]["context_snippets"]) > 0
    
    async def test_advanced_search(self, transcript_service: TranscriptService, sample_ticket):
        """Test advanced search with complex query parameters."""
        # First generate a transcript
        await transcript_service.generate_transcript(sample_ticket.id)
        
        # Perform advanced search
        query = {
            "search_term": "help",
            "date_range": {
                "start_date": datetime.utcnow() - timedelta(days=1),
                "end_date": datetime.utcnow() + timedelta(days=1)
            },
            "ticket_status": [TicketStatus.OPEN.value],
            "highlight": True,
            "exact_match": False
        }
        
        results, count = await transcript_service.advanced_search(query)
        
        assert count > 0
        assert len(results) > 0
        assert "<mark>help</mark>" in results[0]["content"]
        assert "context_snippets" in results[0]