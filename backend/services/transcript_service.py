"""Transcript service for generating and managing ticket transcripts.

This service implements functionality for:
1. Generating and storing transcripts of ticket conversations
2. Full-text search across transcripts
3. Sharing transcripts with secure tokens
4. Transcript lifecycle management
"""

import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Set
from uuid import UUID

from backend.database_service import DatabaseService
from backend.models import Transcript, Ticket, Message, MessageType
from backend.schemas import TranscriptCreate, TranscriptUpdate

# Configure logger
logger = logging.getLogger(__name__)


class TranscriptService:
    """Service class for transcript operations."""
    
    def __init__(self, db_service: DatabaseService):
        """Initialize transcript service with database service.
        
        Args:
            db_service: Database service instance
        """
        self.db = db_service
    
    async def generate_transcript(
        self, 
        ticket_id: UUID,
        include_system_messages: bool = True
    ) -> Transcript:
        """Generate a transcript for a ticket.
        
        Args:
            ticket_id: Ticket UUID
            include_system_messages: Whether to include system messages
            
        Returns:
            Generated transcript instance
            
        Raises:
            ValueError: If ticket not found
        """
        # Get the ticket with messages
        ticket = await self.db.tickets.get_with_messages(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Generate transcript content
        content = await self._generate_transcript_content(
            ticket, include_system_messages
        )
        
        # Generate formatted content
        formatted_content = await self._generate_formatted_content(
            ticket, include_system_messages
        )
        
        # Check if transcript already exists
        existing_transcript = await self.db.transcripts.get_by_ticket_id(ticket_id)
        
        if existing_transcript:
            # Update existing transcript
            updated_transcript = await self.db.transcripts.update_content(
                ticket_id, content, formatted_content
            )
            await self.db.commit()
            return updated_transcript
        else:
            # Create new transcript with share token
            transcript = await self.db.transcripts.create_with_share_token(
                ticket_id=ticket_id,
                content=content,
                formatted_content=formatted_content
            )
            await self.db.commit()
            return transcript
    
    async def get_transcript(self, transcript_id: UUID) -> Optional[Transcript]:
        """Get a transcript by ID.
        
        Args:
            transcript_id: Transcript UUID
            
        Returns:
            Transcript instance or None if not found
        """
        return await self.db.transcripts.get_by_id(transcript_id)
    
    async def get_transcript_by_ticket(self, ticket_id: UUID) -> Optional[Transcript]:
        """Get a transcript by ticket ID.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Transcript instance or None if not found
        """
        return await self.db.transcripts.get_by_ticket_id(ticket_id)
    
    async def get_transcript_by_share_token(self, share_token: str) -> Optional[Transcript]:
        """Get a transcript by share token.
        
        Args:
            share_token: Share token string
            
        Returns:
            Transcript instance or None if not found
        """
        return await self.db.transcripts.get_by_share_token(share_token)
    
    async def update_transcript(
        self, 
        transcript_id: UUID, 
        transcript_data: TranscriptUpdate
    ) -> Optional[Transcript]:
        """Update a transcript.
        
        Args:
            transcript_id: Transcript UUID
            transcript_data: Transcript update data
            
        Returns:
            Updated transcript instance or None if not found
        """
        update_data = {}
        if transcript_data.content is not None:
            update_data['content'] = transcript_data.content
        if transcript_data.formatted_content is not None:
            update_data['formatted_content'] = transcript_data.formatted_content
        if transcript_data.share_token is not None:
            update_data['share_token'] = transcript_data.share_token
        
        if not update_data:
            return await self.get_transcript(transcript_id)
        
        updated_transcript = await self.db.transcripts.update(
            transcript_id, **update_data
        )
        
        if updated_transcript:
            await self.db.commit()
        
        return updated_transcript
    
    async def search_transcripts(
        self,
        search_term: str,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        ticket_status: Optional[str] = None,
        staff_discord_id: Optional[int] = None,
        creator_discord_id: Optional[int] = None,
        highlight_results: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        exact_match: bool = False,
        include_closed: bool = True,
        sort_by: str = "relevance",
        search_mode: str = "basic"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search transcripts by content with full-text search.
        
        This method implements advanced full-text search across transcripts,
        with filtering options and result highlighting.
        
        Args:
            search_term: Search term for transcript content
            created_after: Optional created after date filter
            created_before: Optional created before date filter
            ticket_status: Optional ticket status filter
            staff_discord_id: Optional staff Discord ID filter
            creator_discord_id: Optional creator Discord ID filter
            highlight_results: Whether to highlight search matches in results
            limit: Maximum number of transcripts to return
            offset: Number of transcripts to skip
            exact_match: Whether to require exact phrase matching
            include_closed: Whether to include closed tickets in results
            sort_by: How to sort results ("relevance", "date_asc", "date_desc")
            search_mode: Search mode ("basic", "fuzzy", "advanced")
            
        Returns:
            Tuple of (list of transcript results with metadata, total count)
        """
        # Get matching transcripts
        transcripts = await self.db.transcripts.search_transcripts(
            search_term=search_term,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset,
            search_mode=search_mode
        )
        
        # Get total count for pagination
        total_count = await self.db.transcripts.count_search_results(
            search_term=search_term,
            created_after=created_after,
            created_before=created_before
        )
        
        # Prepare enhanced results with additional metadata and highlighting
        results = []
        for transcript in transcripts:
            # Get ticket for additional filtering and metadata
            ticket = await self.db.tickets.get_by_id(transcript.ticket_id)
            if not ticket:
                continue
                
            # Apply additional filters
            if ticket_status and ticket.status != ticket_status:
                continue
                
            if creator_discord_id and ticket.creator_discord_id != creator_discord_id:
                continue
                
            if staff_discord_id and ticket.assigned_staff_id != staff_discord_id:
                continue
                
            # Filter out closed tickets if requested
            if not include_closed and ticket.status in ["closed", "archived"]:
                continue
                
            # For exact match, verify the exact phrase is in content
            if exact_match and search_term and search_term.lower() not in transcript.content.lower():
                continue
            
            # Prepare result with metadata
            result = {
                "transcript_id": str(transcript.id),
                "ticket_id": str(transcript.ticket_id),
                "ticket_title": ticket.title,
                "ticket_status": ticket.status,
                "creator_discord_id": ticket.creator_discord_id,
                "assigned_staff_id": ticket.assigned_staff_id,
                "created_at": ticket.created_at.isoformat(),
                "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
                "share_token": transcript.share_token,
                "updated_at": transcript.updated_at.isoformat()
            }
            
            # Calculate relevance score based on number of matches
            if search_term:
                match_count = transcript.content.lower().count(search_term.lower())
                result["relevance_score"] = match_count
            else:
                result["relevance_score"] = 0
            
            # Add content with optional highlighting
            if highlight_results:
                result["content"] = self._highlight_search_matches(
                    transcript.content, search_term
                )
                
                # Extract context around matches
                result["context_snippets"] = self._extract_context_snippets(
                    transcript.content, search_term
                )
            else:
                # Truncate content for preview
                max_preview_length = 300
                content = transcript.content
                if len(content) > max_preview_length:
                    content = content[:max_preview_length] + "..."
                result["content"] = content
            
            results.append(result)
        
        # Sort results based on sort_by parameter
        if sort_by == "date_asc":
            results.sort(key=lambda x: x["created_at"])
        elif sort_by == "date_desc":
            results.sort(key=lambda x: x["created_at"], reverse=True)
        elif sort_by == "relevance" and search_term:
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return results, total_count
        
    async def advanced_search(
        self,
        query: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Perform advanced search with complex query parameters.
        
        Args:
            query: Dictionary with search parameters:
                - search_term: Main search term
                - date_range: Dict with start_date and end_date
                - ticket_status: List of statuses to include
                - staff_ids: List of staff Discord IDs
                - creator_ids: List of creator Discord IDs
                - exact_match: Whether to require exact phrase matching
                - highlight: Whether to highlight matches
                - limit: Maximum results to return
                - offset: Number of results to skip
                
        Returns:
            Tuple of (list of transcript results with metadata, total count)
        """
        search_term = query.get("search_term", "")
        date_range = query.get("date_range", {})
        created_after = date_range.get("start_date")
        created_before = date_range.get("end_date")
        ticket_statuses = query.get("ticket_status", [])
        staff_ids = query.get("staff_ids", [])
        creator_ids = query.get("creator_ids", [])
        exact_match = query.get("exact_match", False)
        highlight = query.get("highlight", True)
        limit = query.get("limit", 20)
        offset = query.get("offset", 0)
        
        # Get all matching transcripts first
        transcripts = await self.db.transcripts.search_transcripts(
            search_term=search_term,
            created_after=created_after,
            created_before=created_before,
            limit=None,  # We'll handle pagination after filtering
            offset=None
        )
        
        # Get tickets for all transcripts to apply additional filters
        ticket_ids = [t.ticket_id for t in transcripts]
        tickets = {}
        
        for ticket_id in ticket_ids:
            ticket = await self.db.tickets.get_by_id(ticket_id)
            if ticket:
                tickets[ticket_id] = ticket
        
        # Apply additional filters
        filtered_results = []
        for transcript in transcripts:
            ticket = tickets.get(transcript.ticket_id)
            if not ticket:
                continue
                
            # Filter by ticket status
            if ticket_statuses and ticket.status not in ticket_statuses:
                continue
                
            # Filter by staff ID
            if staff_ids and (not ticket.assigned_staff_id or ticket.assigned_staff_id not in staff_ids):
                continue
                
            # Filter by creator ID
            if creator_ids and ticket.creator_discord_id not in creator_ids:
                continue
                
            # For exact match, verify the exact phrase is in content
            if exact_match and search_term and search_term.lower() not in transcript.content.lower():
                continue
                
            # Prepare result with metadata
            result = {
                "transcript_id": str(transcript.id),
                "ticket_id": str(transcript.ticket_id),
                "ticket_title": ticket.title,
                "ticket_status": ticket.status,
                "creator_discord_id": ticket.creator_discord_id,
                "assigned_staff_id": ticket.assigned_staff_id,
                "created_at": ticket.created_at.isoformat(),
                "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
                "share_token": transcript.share_token,
                "updated_at": transcript.updated_at.isoformat()
            }
            
            # Add content with optional highlighting
            if highlight and search_term:
                result["content"] = self._highlight_search_matches(
                    transcript.content, search_term
                )
                
                # Extract context around matches
                result["context_snippets"] = self._extract_context_snippets(
                    transcript.content, search_term
                )
            else:
                # Truncate content for preview
                max_preview_length = 300
                content = transcript.content
                if len(content) > max_preview_length:
                    content = content[:max_preview_length] + "..."
                result["content"] = content
            
            filtered_results.append(result)
        
        # Apply pagination
        total_count = len(filtered_results)
        paginated_results = filtered_results[offset:offset + limit] if limit else filtered_results
        
        return paginated_results, total_count
    
    async def generate_share_token(self, transcript_id: UUID) -> Optional[str]:
        """Generate a new share token for a transcript.
        
        Args:
            transcript_id: Transcript UUID
            
        Returns:
            New share token or None if transcript not found
        """
        share_token = await self.db.transcripts.generate_new_share_token(transcript_id)
        if share_token:
            await self.db.commit()
        return share_token
    
    async def revoke_share_token(self, transcript_id: UUID) -> bool:
        """Revoke the share token for a transcript.
        
        Args:
            transcript_id: Transcript UUID
            
        Returns:
            True if token was revoked, False if transcript not found
        """
        success = await self.db.transcripts.revoke_share_token(transcript_id)
        if success:
            await self.db.commit()
        return success
    
    async def get_shared_transcripts(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Transcript]:
        """Get transcripts that have share tokens.
        
        Args:
            limit: Maximum number of transcripts to return
            offset: Number of transcripts to skip
            
        Returns:
            List of shared transcripts
        """
        return await self.db.transcripts.get_shared_transcripts(limit, offset)
    
    async def get_recent_transcripts(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Transcript]:
        """Get recently updated transcripts.
        
        Args:
            limit: Maximum number of transcripts to return
            offset: Number of transcripts to skip
            
        Returns:
            List of recent transcripts
        """
        return await self.db.transcripts.get_recent_transcripts(limit, offset)
    
    async def get_transcript_statistics(self) -> Dict[str, Any]:
        """Get comprehensive transcript statistics.
        
        Returns:
            Dictionary with transcript statistics
        """
        return await self.db.transcripts.get_transcript_stats()
    
    async def regenerate_transcript(
        self, 
        ticket_id: UUID,
        include_system_messages: bool = True
    ) -> Optional[Transcript]:
        """Regenerate a transcript for a ticket.
        
        Args:
            ticket_id: Ticket UUID
            include_system_messages: Whether to include system messages
            
        Returns:
            Regenerated transcript instance or None if ticket not found
        """
        try:
            # First, get the ticket with all messages to ensure we have the latest data
            ticket = await self.db.tickets.get_with_messages(ticket_id)
            if not ticket:
                return None
                
            # Get existing transcript
            existing_transcript = await self.db.transcripts.get_by_ticket_id(ticket_id)
            if not existing_transcript:
                # If no transcript exists, create a new one
                return await self.generate_transcript(ticket_id, include_system_messages)
            
            # Generate new content
            content = await self._generate_transcript_content(
                ticket, include_system_messages
            )
            
            # Generate new formatted content
            formatted_content = await self._generate_formatted_content(
                ticket, include_system_messages
            )
            
            # Update existing transcript
            updated_transcript = await self.db.transcripts.update_content(
                ticket_id, content, formatted_content
            )
            
            if updated_transcript:
                await self.db.commit()
                
            return updated_transcript
        except ValueError:
            return None
    
    async def _generate_transcript_content(
        self, 
        ticket: Ticket, 
        include_system_messages: bool = True
    ) -> str:
        """Generate plain text transcript content.
        
        Args:
            ticket: Ticket instance with messages
            include_system_messages: Whether to include system messages
            
        Returns:
            Plain text transcript content
        """
        lines = []
        
        # Header
        lines.append(f"Ticket Transcript: {ticket.title}")
        lines.append(f"Ticket ID: {ticket.id}")
        lines.append(f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"Status: {ticket.status}")
        lines.append(f"Priority: {ticket.priority}")
        lines.append("-" * 50)
        lines.append("")
        
        # Description
        if ticket.description:
            lines.append("Description:")
            lines.append(ticket.description)
            lines.append("")
        
        # Messages
        lines.append("Messages:")
        lines.append("")
        
        # Get the ticket with fresh messages
        # This ensures we have the latest messages, including any added after the ticket was loaded
        ticket_with_messages = await self.db.tickets.get_with_messages(ticket.id)
        if not ticket_with_messages:
            # Fall back to the provided ticket if we can't get a fresh one
            ticket_with_messages = ticket
        
        # Sort messages by creation time
        messages = sorted(ticket_with_messages.messages, key=lambda m: m.created_at)
        
        for message in messages:
            # Skip system messages if not included
            if not include_system_messages and message.message_type == MessageType.SYSTEM_MESSAGE.value:
                continue
            
            timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            author_type = self._get_author_type_display(message.message_type)
            
            lines.append(f"[{timestamp}] {author_type} (ID: {message.author_discord_id}):")
            lines.append(message.content)
            lines.append("")
        
        # Footer
        lines.append("-" * 50)
        lines.append(f"Transcript generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return "\n".join(lines)
    
    async def _generate_formatted_content(
        self, 
        ticket: Ticket, 
        include_system_messages: bool = True
    ) -> Dict[str, Any]:
        """Generate structured transcript content.
        
        Args:
            ticket: Ticket instance with messages
            include_system_messages: Whether to include system messages
            
        Returns:
            Structured transcript content
        """
        # Get the ticket with fresh messages
        # This ensures we have the latest messages, including any added after the ticket was loaded
        ticket_with_messages = await self.db.tickets.get_with_messages(ticket.id)
        if not ticket_with_messages:
            # Fall back to the provided ticket if we can't get a fresh one
            ticket_with_messages = ticket
        
        # Sort messages by creation time
        messages = sorted(ticket_with_messages.messages, key=lambda m: m.created_at)
        
        # Filter messages if needed
        if not include_system_messages:
            messages = [m for m in messages if m.message_type != MessageType.SYSTEM_MESSAGE.value]
        
        formatted_messages = []
        for message in messages:
            formatted_messages.append({
                "id": str(message.id),
                "timestamp": message.created_at.isoformat(),
                "author_discord_id": message.author_discord_id,
                "content": message.content,
                "message_type": message.message_type,
                "discord_message_id": message.discord_message_id
            })
        
        return {
            "ticket": {
                "id": str(ticket.id),
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status,
                "priority": ticket.priority,
                "creator_discord_id": ticket.creator_discord_id,
                "assigned_staff_id": ticket.assigned_staff_id,
                "discord_channel_id": ticket.discord_channel_id,
                "created_at": ticket.created_at.isoformat(),
                "updated_at": ticket.updated_at.isoformat(),
                "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None
            },
            "messages": formatted_messages,
            "metadata": {
                "total_messages": len(formatted_messages),
                "include_system_messages": include_system_messages,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    
    def _highlight_search_matches(self, text: str, search_term: str) -> str:
        """Highlight search term matches in text.
        
        Args:
            text: Text to search in
            search_term: Search term to highlight
            
        Returns:
            Text with search term matches highlighted with HTML tags
        """
        if not search_term:
            return text
            
        # Escape special regex characters in search term
        escaped_term = re.escape(search_term)
        
        # Create regex pattern for case-insensitive search
        pattern = re.compile(f"({escaped_term})", re.IGNORECASE)
        
        # Replace matches with highlighted version
        highlighted = pattern.sub(r"<mark>\1</mark>", text)
        
        return highlighted
    
    def _extract_context_snippets(self, text: str, search_term: str, context_chars: int = 50) -> List[str]:
        """Extract snippets of text around search term matches.
        
        Args:
            text: Text to search in
            search_term: Search term to find
            context_chars: Number of characters to include before and after match
            
        Returns:
            List of text snippets with context around matches
        """
        if not search_term or not text:
            return []
            
        # Escape special regex characters in search term
        escaped_term = re.escape(search_term)
        
        # Create regex pattern for case-insensitive search
        pattern = re.compile(f"({escaped_term})", re.IGNORECASE)
        
        # Find all matches
        matches = list(pattern.finditer(text))
        if not matches:
            return []
            
        # Extract snippets with context
        snippets = []
        for match in matches:
            start_pos = max(0, match.start() - context_chars)
            end_pos = min(len(text), match.end() + context_chars)
            
            # Extract snippet
            snippet = text[start_pos:end_pos]
            
            # Add ellipsis if snippet doesn't start/end at text boundaries
            if start_pos > 0:
                snippet = "..." + snippet
            if end_pos < len(text):
                snippet = snippet + "..."
                
            # Highlight the match in the snippet using regex to ensure exact match
            # This prevents issues with case sensitivity or partial replacements
            highlighted_snippet = re.sub(
                f"({re.escape(match.group(0))})",
                r"<mark>\1</mark>",
                snippet,
                flags=re.IGNORECASE
            )
            
            snippets.append(highlighted_snippet)
            
        return snippets
    
    def _get_author_type_display(self, message_type: str) -> str:
        """Get display name for message author type.
        
        Args:
            message_type: Message type
            
        Returns:
            Display name for the author type
        """
        type_mapping = {
            MessageType.USER_MESSAGE.value: "User",
            MessageType.STAFF_MESSAGE.value: "Staff",
            MessageType.SYSTEM_MESSAGE.value: "System",
            MessageType.BOT_MESSAGE.value: "Bot"
        }
        return type_mapping.get(message_type, "Unknown")