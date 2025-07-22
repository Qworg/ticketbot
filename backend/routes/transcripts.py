"""API routes for transcript management."""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Response
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from backend.database_service import DatabaseService, get_db_service
from backend.schemas import (
    Transcript, TranscriptCreate, TranscriptUpdate, TranscriptPagination,
    ErrorResponse
)

router = APIRouter(
    prefix="/api",
    tags=["transcripts"],
    responses={
        http_status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        http_status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        http_status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    }
)


@router.get(
    "/tickets/{ticket_id}/transcript",
    response_model=Transcript,
    summary="Get ticket transcript",
    description="Retrieves the transcript for a specific ticket."
)
async def get_ticket_transcript(
    ticket_id: UUID = Path(..., description="Ticket UUID"),
    db: DatabaseService = Depends(get_db_service)
) -> Transcript:
    """Get transcript for a specific ticket.
    
    Args:
        ticket_id: Ticket UUID
        db: Database service dependency
        
    Returns:
        Ticket transcript
        
    Raises:
        HTTPException: If ticket or transcript is not found
    """
    try:
        # Check if ticket exists
        ticket = await db.tickets.get_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        
        # Get transcript
        transcript = await db.transcripts.get_by_ticket_id(ticket_id)
        
        # If transcript doesn't exist, generate it from messages
        if not transcript:
            # Get ticket messages
            ticket_with_messages = await db.tickets.get_with_messages(ticket_id)
            
            if not ticket_with_messages or not ticket_with_messages.messages:
                # No messages to create transcript from
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"No messages found for ticket with ID {ticket_id}"
                )
            
            # Generate transcript content
            content = _generate_transcript_content(ticket_with_messages)
            
            # Generate formatted content (JSON structure with messages) safely
            try:
                # Get ticket attributes safely
                ticket_id_str = str(ticket_id)
                title = getattr(ticket_with_messages, 'title', 'Unknown Ticket')
                status = getattr(ticket_with_messages, 'status', 'unknown')
                created_at = getattr(ticket_with_messages, 'created_at', datetime.now())
                
                # Format created_at as ISO string if it's a datetime
                if not isinstance(created_at, str):
                    try:
                        created_at_str = created_at.isoformat()
                    except:
                        created_at_str = str(created_at)
                else:
                    created_at_str = created_at
                
                # Get messages safely
                messages = getattr(ticket_with_messages, 'messages', [])
                
                # Create formatted content
                formatted_content = {
                    "ticket": {
                        "id": ticket_id_str,
                        "title": title,
                        "status": status,
                        "created_at": created_at_str,
                    },
                    "messages": []
                }
                
                # Add messages safely
                for msg in messages:
                    try:
                        msg_id = getattr(msg, 'id', str(uuid.uuid4()))
                        msg_author_id = getattr(msg, 'author_discord_id', 0)
                        msg_content = getattr(msg, 'content', '[No content]')
                        msg_type = getattr(msg, 'message_type', 'user_message')
                        msg_created_at = getattr(msg, 'created_at', datetime.now())
                        
                        # Format created_at as ISO string if it's a datetime
                        if not isinstance(msg_created_at, str):
                            try:
                                msg_created_at_str = msg_created_at.isoformat()
                            except:
                                msg_created_at_str = str(msg_created_at)
                        else:
                            msg_created_at_str = msg_created_at
                        
                        formatted_content["messages"].append({
                            "id": str(msg_id),
                            "author_discord_id": msg_author_id,
                            "content": msg_content,
                            "message_type": msg_type,
                            "created_at": msg_created_at_str
                        })
                    except Exception:
                        # Skip this message if there's an error
                        continue
            except Exception:
                # If there's an error, create a minimal formatted content
                formatted_content = {
                    "ticket": {
                        "id": str(ticket_id),
                        "title": "Unknown Ticket",
                        "status": "unknown",
                        "created_at": datetime.now().isoformat()
                    },
                    "messages": []
                }
            
            # Create transcript
            transcript = await db.transcripts.create_with_share_token(
                ticket_id=ticket_id,
                content=content,
                formatted_content=formatted_content
            )
        
        return transcript
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transcript: {str(e)}"
        )


@router.post(
    "/tickets/{ticket_id}/transcript/share",
    response_model=Dict[str, str],
    summary="Generate or refresh transcript share token",
    description="Generates a new share token for a ticket transcript or refreshes an existing one."
)
async def generate_share_token(
    ticket_id: UUID = Path(..., description="Ticket UUID"),
    db: DatabaseService = Depends(get_db_service)
) -> Dict[str, str]:
    """Generate or refresh a share token for a ticket transcript.
    
    Args:
        ticket_id: Ticket UUID
        db: Database service dependency
        
    Returns:
        Dictionary with share token
        
    Raises:
        HTTPException: If ticket or transcript is not found
    """
    try:
        # Check if ticket exists
        ticket = await db.tickets.get_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        
        # Get transcript
        transcript = await db.transcripts.get_by_ticket_id(ticket_id)
        
        # If transcript doesn't exist, create it first
        if not transcript:
            # Get ticket with messages to generate transcript
            ticket_with_messages = await db.tickets.get_with_messages(ticket_id)
            
            if not ticket_with_messages or not ticket_with_messages.messages:
                # No messages to create transcript from
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"No messages found for ticket with ID {ticket_id}"
                )
            
            # Generate transcript content
            content = _generate_transcript_content(ticket_with_messages)
            
            # Generate formatted content (JSON structure with messages) safely
            try:
                # Get ticket attributes safely
                ticket_id_str = str(ticket_id)
                title = getattr(ticket_with_messages, 'title', 'Unknown Ticket')
                status = getattr(ticket_with_messages, 'status', 'unknown')
                created_at = getattr(ticket_with_messages, 'created_at', datetime.now())
                
                # Format created_at as ISO string if it's a datetime
                if not isinstance(created_at, str):
                    try:
                        created_at_str = created_at.isoformat()
                    except:
                        created_at_str = str(created_at)
                else:
                    created_at_str = created_at
                
                # Get messages safely
                messages = getattr(ticket_with_messages, 'messages', [])
                
                # Create formatted content
                formatted_content = {
                    "ticket": {
                        "id": ticket_id_str,
                        "title": title,
                        "status": status,
                        "created_at": created_at_str,
                    },
                    "messages": []
                }
                
                # Add messages safely
                for msg in messages:
                    try:
                        msg_id = getattr(msg, 'id', str(uuid.uuid4()))
                        msg_author_id = getattr(msg, 'author_discord_id', 0)
                        msg_content = getattr(msg, 'content', '[No content]')
                        msg_type = getattr(msg, 'message_type', 'user_message')
                        msg_created_at = getattr(msg, 'created_at', datetime.now())
                        
                        # Format created_at as ISO string if it's a datetime
                        if not isinstance(msg_created_at, str):
                            try:
                                msg_created_at_str = msg_created_at.isoformat()
                            except:
                                msg_created_at_str = str(msg_created_at)
                        else:
                            msg_created_at_str = msg_created_at
                        
                        formatted_content["messages"].append({
                            "id": str(msg_id),
                            "author_discord_id": msg_author_id,
                            "content": msg_content,
                            "message_type": msg_type,
                            "created_at": msg_created_at_str
                        })
                    except Exception:
                        # Skip this message if there's an error
                        continue
            except Exception:
                # If there's an error, create a minimal formatted content
                formatted_content = {
                    "ticket": {
                        "id": str(ticket_id),
                        "title": "Unknown Ticket",
                        "status": "unknown",
                        "created_at": datetime.now().isoformat()
                    },
                    "messages": []
                }
            
            # Create transcript with share token
            transcript = await db.transcripts.create_with_share_token(
                ticket_id=ticket_id,
                content=content,
                formatted_content=formatted_content
            )
            
            return {"share_token": transcript.share_token}
        
        # If transcript exists but has no share token, generate one
        if not transcript.share_token:
            try:
                # Try to use the transcript ID directly
                share_token = await db.transcripts.generate_new_share_token(transcript.id)
            except Exception as e:
                # If that fails, try to convert the ID to a UUID
                try:
                    transcript_id = UUID(str(transcript.id))
                    share_token = await db.transcripts.generate_new_share_token(transcript_id)
                except Exception as e:
                    raise HTTPException(
                        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to generate share token: {str(e)}"
                    )
            return {"share_token": share_token}
        
        # If transcript already has a share token, refresh it
        try:
            # Try to use the transcript ID directly
            share_token = await db.transcripts.generate_new_share_token(transcript.id)
        except Exception as e:
            # If that fails, try to convert the ID to a UUID
            try:
                transcript_id = UUID(str(transcript.id))
                share_token = await db.transcripts.generate_new_share_token(transcript_id)
            except Exception as e:
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate share token: {str(e)}"
                )
        return {"share_token": share_token}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate share token: {str(e)}"
        )


@router.delete(
    "/tickets/{ticket_id}/transcript/share",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Revoke transcript share token",
    description="Revokes the share token for a ticket transcript."
)
async def revoke_share_token(
    ticket_id: UUID = Path(..., description="Ticket UUID"),
    db: DatabaseService = Depends(get_db_service)
) -> Response:
    """Revoke the share token for a ticket transcript.
    
    Args:
        ticket_id: Ticket UUID
        db: Database service dependency
        
    Returns:
        Empty response with 204 status code
        
    Raises:
        HTTPException: If ticket or transcript is not found
    """
    try:
        # Check if ticket exists
        ticket = await db.tickets.get_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found"
            )
        
        # Get transcript
        transcript = await db.transcripts.get_by_ticket_id(ticket_id)
        
        if not transcript:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Transcript for ticket with ID {ticket_id} not found"
            )
        
        # Revoke share token
        try:
            # Try to use the transcript ID directly
            success = await db.transcripts.revoke_share_token(transcript.id)
        except Exception as e:
            # If that fails, try to convert the ID to a UUID
            try:
                transcript_id = UUID(str(transcript.id))
                success = await db.transcripts.revoke_share_token(transcript_id)
            except Exception as e:
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to revoke share token: {str(e)}"
                )
        
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke share token"
            )
        
        return Response(status_code=http_status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke share token: {str(e)}"
        )


@router.get(
    "/transcripts/shared/{share_token}",
    response_model=Transcript,
    summary="Get transcript by share token",
    description="Retrieves a transcript using a share token."
)
async def get_transcript_by_share_token(
    share_token: str = Path(..., description="Share token"),
    db: DatabaseService = Depends(get_db_service)
) -> Transcript:
    """Get transcript by share token.
    
    Args:
        share_token: Share token
        db: Database service dependency
        
    Returns:
        Transcript
        
    Raises:
        HTTPException: If transcript is not found
    """
    try:
        # Get transcript by share token
        transcript = await db.transcripts.get_by_share_token(share_token)
        
        if not transcript:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired share token"
            )
        
        return transcript
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transcript: {str(e)}"
        )


@router.get(
    "/search/transcripts",
    response_model=TranscriptPagination,
    summary="Search transcripts",
    description="Searches transcripts by content with filtering and pagination."
)
async def search_transcripts(
    search: str = Query(..., description="Search term for transcript content"),
    created_after: Optional[datetime] = Query(None, description="Filter by created after date"),
    created_before: Optional[datetime] = Query(None, description="Filter by created before date"),
    search_mode: str = Query("basic", description="Search mode (basic, fuzzy, advanced)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: DatabaseService = Depends(get_db_service)
) -> TranscriptPagination:
    """Search transcripts by content.
    
    Args:
        search: Search term for transcript content
        created_after: Optional filter by created after date
        created_before: Optional filter by created before date
        search_mode: Search mode (basic, fuzzy, advanced)
        page: Page number (1-indexed)
        size: Items per page
        db: Database service dependency
        
    Returns:
        Paginated list of matching transcripts
        
    Raises:
        HTTPException: If search fails
    """
    try:
        # Calculate offset for pagination
        offset = (page - 1) * size
        
        # Search transcripts
        transcripts = await db.transcripts.search_transcripts(
            search_term=search,
            created_after=created_after,
            created_before=created_before,
            limit=size,
            offset=offset,
            search_mode=search_mode
        )
        
        # Get total count for pagination
        total_count = await db.transcripts.count_search_results(
            search_term=search,
            created_after=created_after,
            created_before=created_before
        )
        
        # Calculate total pages
        total_pages = (total_count + size - 1) // size if total_count > 0 else 1
        
        return TranscriptPagination(
            items=transcripts,
            total=total_count,
            page=page,
            size=size,
            pages=total_pages
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search transcripts: {str(e)}"
        )


def _generate_transcript_content(ticket_with_messages) -> str:
    """Generate plain text transcript content from ticket messages.
    
    Args:
        ticket_with_messages: Ticket with messages
        
    Returns:
        Plain text transcript content
    """
    try:
        # Get ticket attributes safely
        title = getattr(ticket_with_messages, 'title', 'Unknown Ticket')
        ticket_id = getattr(ticket_with_messages, 'id', 'Unknown ID')
        status = getattr(ticket_with_messages, 'status', 'unknown')
        created_at = getattr(ticket_with_messages, 'created_at', datetime.now())
        
        lines = [
            f"Ticket: {title}",
            f"ID: {ticket_id}",
            f"Status: {status}",
            f"Created: {_format_datetime(created_at)}",
            "",
            "--- Transcript ---",
            ""
        ]
        
        # Get messages safely
        messages = getattr(ticket_with_messages, 'messages', [])
        if not messages:
            lines.append("[No messages found]")
            return "\n".join(lines)
        
        # Sort messages by created_at, handling potential errors
        try:
            sorted_messages = sorted(messages, key=lambda m: getattr(m, 'created_at', datetime.now()))
        except Exception:
            # If sorting fails, use the original order
            sorted_messages = messages
        
        for msg in sorted_messages:
            try:
                # Get message attributes safely
                msg_created_at = getattr(msg, 'created_at', datetime.now())
                msg_content = getattr(msg, 'content', '[No content]')
                msg_author_id = getattr(msg, 'author_discord_id', 0)
                message_type = getattr(msg, 'message_type', 'user_message')
                
                timestamp = _format_datetime(msg_created_at)
                author_type = "User" if message_type == "user_message" else "Staff" if message_type == "staff_message" else "System" if message_type == "system_message" else "Bot"
                lines.append(f"[{timestamp}] {author_type} ({msg_author_id}): {msg_content}")
            except Exception as e:
                # If there's an error processing a message, add a placeholder
                lines.append(f"[Error processing message: {str(e)}]")
        
        return "\n".join(lines)
    except Exception as e:
        # If there's a general error, return a basic transcript
        return f"Ticket Transcript (Error: {str(e)})"


def _format_datetime(dt) -> str:
    """Format datetime object or string to a consistent format.
    
    Args:
        dt: Datetime object or ISO format string
        
    Returns:
        Formatted datetime string
    """
    if isinstance(dt, str):
        try:
            # Try to parse ISO format string
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            # If parsing fails, return the original string
            return dt
    
    try:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (AttributeError, TypeError):
        # If formatting fails, return a default string
        return str(dt)