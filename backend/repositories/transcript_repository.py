"""Repository for transcript database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import secrets
import string

from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Transcript
from backend.repositories.base import BaseRepository


class TranscriptRepository(BaseRepository[Transcript]):
    """Repository for transcript-specific database operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize transcript repository."""
        super().__init__(Transcript, session)
    
    async def get_by_ticket_id(self, ticket_id: UUID) -> Optional[Transcript]:
        """Get transcript for a specific ticket.
        
        Args:
            ticket_id: Ticket UUID
            
        Returns:
            Transcript instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_share_token(self, share_token: str) -> Optional[Transcript]:
        """Get transcript by share token.
        
        Args:
            share_token: Share token string
            
        Returns:
            Transcript instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.share_token == share_token)
        )
        return result.scalar_one_or_none()
    
    async def create_with_share_token(self, ticket_id: UUID, content: str, formatted_content: Optional[Dict[str, Any]] = None) -> Transcript:
        """Create a new transcript with a generated share token.
        
        Args:
            ticket_id: Ticket UUID
            content: Transcript content
            formatted_content: Optional formatted content
            
        Returns:
            Created transcript instance
        """
        share_token = self._generate_share_token()
        
        # Ensure token is unique
        while await self.get_by_share_token(share_token):
            share_token = self._generate_share_token()
        
        return await self.create(
            ticket_id=ticket_id,
            content=content,
            formatted_content=formatted_content,
            share_token=share_token
        )
    
    async def update_content(self, ticket_id: UUID, content: str, formatted_content: Optional[Dict[str, Any]] = None) -> Optional[Transcript]:
        """Update transcript content for a ticket.
        
        Args:
            ticket_id: Ticket UUID
            content: New transcript content
            formatted_content: Optional new formatted content
            
        Returns:
            Updated transcript instance or None if not found
        """
        transcript = await self.get_by_ticket_id(ticket_id)
        if not transcript:
            return None
        
        return await self.update(
            transcript.id,
            content=content,
            formatted_content=formatted_content,
            updated_at=datetime.utcnow()
        )
    
    async def search_transcripts(
        self,
        search_term: str,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search_mode: str = "basic"
    ) -> List[Transcript]:
        """Search transcripts by content.
        
        Args:
            search_term: Search term for transcript content
            created_after: Optional created after date filter
            created_before: Optional created before date filter
            limit: Maximum number of transcripts to return
            offset: Number of transcripts to skip
            search_mode: Search mode ("basic", "fuzzy", "advanced")
            
        Returns:
            List of matching transcripts
        """
        if not search_term:
            # If no search term, just return recent transcripts
            return await self.get_recent_transcripts(limit, offset)
        
        # Basic search with ILIKE
        if search_mode == "basic":
            query = select(self.model).where(
                self.model.content.ilike(f"%{search_term}%")
            )
        # Fuzzy search with multiple terms
        elif search_mode == "fuzzy":
            # Split search term into words
            search_words = search_term.split()
            conditions = []
            
            # Create OR conditions for each word
            for word in search_words:
                if len(word) >= 3:  # Only search for words with at least 3 characters
                    conditions.append(self.model.content.ilike(f"%{word}%"))
            
            # Combine conditions with OR
            if conditions:
                query = select(self.model).where(or_(*conditions))
            else:
                query = select(self.model).where(
                    self.model.content.ilike(f"%{search_term}%")
                )
        # Advanced search with full-text search capabilities
        elif search_mode == "advanced":
            # Use PostgreSQL full-text search if available
            # This is a simplified version - in a real implementation,
            # we would use PostgreSQL's to_tsvector and to_tsquery functions
            query = select(self.model).where(
                self.model.content.ilike(f"%{search_term}%")
            )
        else:
            # Default to basic search
            query = select(self.model).where(
                self.model.content.ilike(f"%{search_term}%")
            )
        
        # Apply date filters
        if created_after:
            query = query.where(self.model.created_at >= created_after)
        
        if created_before:
            query = query.where(self.model.created_at <= created_before)
        
        # Order by relevance (updated_at for now)
        query = query.order_by(desc(self.model.updated_at))
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
        
    async def count_search_results(
        self,
        search_term: str,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None
    ) -> int:
        """Count transcripts matching search criteria.
        
        Args:
            search_term: Search term for transcript content
            created_after: Optional created after date filter
            created_before: Optional created before date filter
            
        Returns:
            Number of matching transcripts
        """
        query = select(func.count(self.model.id)).where(
            self.model.content.ilike(f"%{search_term}%")
        )
        
        if created_after:
            query = query.where(self.model.created_at >= created_after)
        
        if created_before:
            query = query.where(self.model.created_at <= created_before)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
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
        query = select(self.model).order_by(desc(self.model.updated_at))
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_transcript_stats(self) -> Dict[str, Any]:
        """Get transcript statistics.
        
        Returns:
            Dictionary with transcript statistics
        """
        # Total transcripts
        total_result = await self.session.execute(
            select(func.count(self.model.id))
        )
        total_transcripts = total_result.scalar()
        
        # Transcripts with share tokens
        shared_result = await self.session.execute(
            select(func.count(self.model.id)).where(
                self.model.share_token.is_not(None)
            )
        )
        shared_transcripts = shared_result.scalar()
        
        # Average content length
        avg_length_result = await self.session.execute(
            select(func.avg(func.length(self.model.content)))
        )
        avg_content_length = avg_length_result.scalar()
        
        # Transcripts created today
        today = datetime.now().date()
        today_result = await self.session.execute(
            select(func.count(self.model.id)).where(
                func.date(self.model.created_at) == today
            )
        )
        transcripts_today = today_result.scalar()
        
        return {
            "total_transcripts": total_transcripts,
            "shared_transcripts": shared_transcripts,
            "transcripts_today": transcripts_today,
            "avg_content_length": int(avg_content_length) if avg_content_length else 0
        }
    
    async def generate_new_share_token(self, transcript_id: UUID) -> Optional[str]:
        """Generate a new share token for an existing transcript.
        
        Args:
            transcript_id: Transcript UUID
            
        Returns:
            New share token or None if transcript not found
        """
        share_token = self._generate_share_token()
        
        # Ensure token is unique
        while await self.get_by_share_token(share_token):
            share_token = self._generate_share_token()
        
        transcript = await self.update(transcript_id, share_token=share_token)
        return transcript.share_token if transcript else None
    
    async def revoke_share_token(self, transcript_id: UUID) -> bool:
        """Revoke the share token for a transcript.
        
        Args:
            transcript_id: Transcript UUID
            
        Returns:
            True if token was revoked, False if transcript not found
        """
        transcript = await self.update(transcript_id, share_token=None)
        return transcript is not None
    
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
        query = select(self.model).where(
            self.model.share_token.is_not(None)
        ).order_by(desc(self.model.updated_at))
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    def _generate_share_token(self, length: int = 32) -> str:
        """Generate a random share token.
        
        Args:
            length: Length of the token
            
        Returns:
            Random token string
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))