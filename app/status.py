"""
Ticket status state machine implementation.

This module defines ticket status constants, valid transitions, and validation logic.
"""
from enum import Enum
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TicketStatus(str, Enum):
    """Ticket status enumeration with valid status values."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class StatusTransitionError(Exception):
    """Exception raised when an invalid status transition is attempted."""
    
    def __init__(self, current_status: str, new_status: str, message: Optional[str] = None):
        self.current_status = current_status
        self.new_status = new_status
        if message is None:
            message = f"Invalid transition from '{current_status}' to '{new_status}'"
        super().__init__(message)


# Status transition matrix - defines valid transitions
# Key is current status, value is set of allowed next statuses
STATUS_TRANSITIONS: Dict[TicketStatus, Set[TicketStatus]] = {
    TicketStatus.OPEN: {
        TicketStatus.IN_PROGRESS,  # Staff claims/works on ticket
        TicketStatus.CLOSED,       # Direct close without resolution
    },
    TicketStatus.IN_PROGRESS: {
        TicketStatus.RESOLVED,     # Issue is resolved
        TicketStatus.CLOSED,       # Direct close without resolution
        TicketStatus.OPEN,         # Unclaim/return to open state
    },
    TicketStatus.RESOLVED: {
        TicketStatus.CLOSED,       # Close after resolution confirmation
        TicketStatus.IN_PROGRESS,  # Reopen if issue persists
    },
    TicketStatus.CLOSED: set(),  # Closed tickets cannot transition to other states
}


def validate_status_transition(current_status: str, new_status: str) -> bool:
    """
    Validate if a status transition is allowed.
    
    Args:
        current_status: Current ticket status
        new_status: Desired new status
        
    Returns:
        True if transition is valid, False otherwise
    """
    try:
        current = TicketStatus(current_status.lower())
        new = TicketStatus(new_status.lower())
        
        # Check if the transition is allowed
        allowed_transitions = STATUS_TRANSITIONS.get(current, set())
        return new in allowed_transitions
        
    except ValueError:
        # Invalid status value
        logger.warning(f"Invalid status value: current='{current_status}', new='{new_status}'")
        return False


def get_valid_next_statuses(current_status: str) -> List[str]:
    """
    Get list of valid next statuses for the current status.
    
    Args:
        current_status: Current ticket status
        
    Returns:
        List of valid next status values
    """
    try:
        current = TicketStatus(current_status.lower())
        allowed_transitions = STATUS_TRANSITIONS.get(current, set())
        return [status.value for status in allowed_transitions]
        
    except ValueError:
        logger.warning(f"Invalid status value: '{current_status}'")
        return []


def enforce_status_transition(current_status: str, new_status: str) -> str:
    """
    Enforce status transition validation and return normalized new status.
    
    Args:
        current_status: Current ticket status
        new_status: Desired new status
        
    Returns:
        Normalized new status value
        
    Raises:
        StatusTransitionError: If transition is invalid
    """
    if not validate_status_transition(current_status, new_status):
        raise StatusTransitionError(current_status, new_status)
    
    # Return normalized status
    return TicketStatus(new_status.lower()).value


def is_terminal_status(status: str) -> bool:
    """
    Check if a status is terminal (no further transitions allowed).
    
    Args:
        status: Ticket status to check
        
    Returns:
        True if status is terminal, False otherwise
    """
    try:
        ticket_status = TicketStatus(status.lower())
        allowed_transitions = STATUS_TRANSITIONS.get(ticket_status, set())
        return len(allowed_transitions) == 0
        
    except ValueError:
        return False


def get_status_description(status: str) -> str:
    """
    Get human-readable description for a status.
    
    Args:
        status: Ticket status
        
    Returns:
        Human-readable status description
    """
    descriptions = {
        TicketStatus.OPEN: "Open - Waiting for staff response",
        TicketStatus.IN_PROGRESS: "In Progress - Being worked on by staff",
        TicketStatus.RESOLVED: "Resolved - Issue has been addressed",
        TicketStatus.CLOSED: "Closed - Ticket is completed and archived",
    }
    
    try:
        ticket_status = TicketStatus(status.lower())
        return descriptions.get(ticket_status, f"Unknown status: {status}")
        
    except ValueError:
        return f"Invalid status: {status}"


class StatusTransitionLog:
    """Class to represent a status transition log entry."""
    
    def __init__(
        self,
        ticket_id: int,
        previous_status: str,
        new_status: str,
        changed_by: int,
        reason: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.ticket_id = ticket_id
        self.previous_status = previous_status
        self.new_status = new_status
        self.changed_by = changed_by
        self.reason = reason
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "ticket_id": self.ticket_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


def log_status_transition(
    ticket_id: int,
    previous_status: str,
    new_status: str,
    changed_by: int,
    reason: Optional[str] = None
) -> StatusTransitionLog:
    """
    Create a status transition log entry.
    
    Args:
        ticket_id: ID of the ticket
        previous_status: Previous status value
        new_status: New status value
        changed_by: User ID who made the change
        reason: Optional reason for the change
        
    Returns:
        StatusTransitionLog object
    """
    transition_log = StatusTransitionLog(
        ticket_id=ticket_id,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=changed_by,
        reason=reason
    )
    
    logger.info(
        f"Status transition: ticket_id={ticket_id}, "
        f"{previous_status} -> {new_status}, "
        f"changed_by={changed_by}, "
        f"reason='{reason or 'N/A'}'"
    )
    
    return transition_log


# Utility functions for status checks

def is_open_status(status: str) -> bool:
    """Check if status represents an open/active ticket."""
    try:
        ticket_status = TicketStatus(status.lower())
        return ticket_status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]
    except ValueError:
        return False


def is_closed_status(status: str) -> bool:
    """Check if status represents a closed ticket."""
    try:
        ticket_status = TicketStatus(status.lower())
        return ticket_status == TicketStatus.CLOSED
    except ValueError:
        return False


def is_resolved_status(status: str) -> bool:
    """Check if status represents a resolved ticket."""
    try:
        ticket_status = TicketStatus(status.lower())
        return ticket_status == TicketStatus.RESOLVED
    except ValueError:
        return False


def can_be_assigned(status: str) -> bool:
    """Check if ticket with this status can be assigned to staff."""
    try:
        ticket_status = TicketStatus(status.lower())
        return ticket_status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]
    except ValueError:
        return False


def requires_close_reason(current_status: str, new_status: str) -> bool:
    """Check if transitioning to new status requires a close reason."""
    try:
        new_ticket_status = TicketStatus(new_status.lower())
        return new_ticket_status == TicketStatus.CLOSED
    except ValueError:
        return False


class TicketClosureError(Exception):
    """Exception raised when ticket closure validation fails."""
    
    def __init__(self, ticket_id: int, message: str):
        self.ticket_id = ticket_id
        self.message = message
        super().__init__(f"Ticket {ticket_id}: {message}")


def validate_close_reason(close_reason: Optional[str]) -> None:
    """
    Validate close reason meets requirements.
    
    Args:
        close_reason: The reason provided for closing the ticket
        
    Raises:
        ValueError: If close reason is invalid
    """
    if not close_reason:
        raise ValueError("Close reason is required when closing a ticket")
    
    close_reason = close_reason.strip()
    if not close_reason:  # Check again after trimming
        raise ValueError("Close reason is required when closing a ticket")
    
    if len(close_reason) < 3:
        raise ValueError("Close reason must be at least 3 characters long")
    
    if len(close_reason) > 200:
        raise ValueError("Close reason cannot exceed 200 characters")


def validate_ticket_closure_permission(ticket, user_id: int, user_role: str) -> bool:
    """
    Validate if user has permission to close the specified ticket.
    
    Args:
        ticket: Ticket object to check permissions for
        user_id: Discord user ID of the user attempting closure
        user_role: Role of the user (ADMIN, STAFF, USER)
        
    Returns:
        True if user can close the ticket, False otherwise
    """
    from .permissions import Role
    
    # Admins can close any ticket
    if user_role == Role.ADMIN:
        return True
    
    # Staff can close assigned tickets or any ticket if they have MANAGE_TICKETS permission
    if user_role == Role.STAFF:
        # Staff can always close tickets assigned to them
        if hasattr(ticket, 'assigned_to') and ticket.assigned_to == user_id:
            return True
        # Staff with MANAGE_TICKETS can close any ticket
        return True
    
    # Users can only close their own tickets
    if user_role == Role.USER:
        return hasattr(ticket, 'creator_id') and ticket.creator_id == user_id
    
    return False


def check_ticket_dependencies(ticket) -> List[str]:
    """
    Check if ticket has any unresolved dependencies that prevent closure.
    
    Args:
        ticket: Ticket object to check
        
    Returns:
        List of dependency issues (empty if no issues)
    """
    issues = []
    
    # For now, we don't have complex dependencies implemented
    # This is a placeholder for future dependency checking
    # Examples could include:
    # - Related tickets that must be closed first
    # - Required approvals or sign-offs
    # - Pending external integrations
    
    # Check if ticket is in a state that allows closure
    if hasattr(ticket, 'status'):
        current_status = ticket.status
        if current_status == TicketStatus.CLOSED:
            issues.append("Ticket is already closed")
    
    return issues


def validate_ticket_closure(
    ticket,
    user_id: int,
    user_role: str,
    close_reason: Optional[str] = None
) -> None:
    """
    Comprehensive ticket closure validation function.
    
    Args:
        ticket: Ticket object to validate for closure
        user_id: Discord user ID of the user attempting closure
        user_role: Role of the user (ADMIN, STAFF, USER)
        close_reason: Reason for closing the ticket
        
    Raises:
        TicketClosureError: If closure validation fails
        ValueError: If close_reason format is invalid
    """
    # Get ticket ID, default to 0 if not available
    ticket_id = getattr(ticket, 'id', 0)
    if not isinstance(ticket_id, int):
        ticket_id = 0
    
    # Validate close reason
    try:
        validate_close_reason(close_reason)
    except ValueError as e:
        raise TicketClosureError(ticket_id, str(e))
    
    # Check user permissions
    if not validate_ticket_closure_permission(ticket, user_id, user_role):
        raise TicketClosureError(
            ticket_id,
            "You do not have permission to close this ticket"
        )
    
    # Check for unresolved dependencies
    dependency_issues = check_ticket_dependencies(ticket)
    if dependency_issues:
        raise TicketClosureError(
            ticket_id,
            f"Cannot close ticket due to unresolved dependencies: {', '.join(dependency_issues)}"
        )
    
    # All validations passed
    logger.info(f"Ticket {ticket_id} closure validation passed for user {user_id}")


def create_closure_audit_entry(
    ticket_id: int,
    user_id: int,
    close_reason: str,
    closed_at: datetime
) -> Dict[str, Any]:
    """
    Create audit log entry for ticket closure.
    
    Args:
        ticket_id: ID of the closed ticket
        user_id: Discord user ID who closed the ticket
        close_reason: Reason for closure
        closed_at: Timestamp when ticket was closed
        
    Returns:
        Audit log entry dictionary
    """
    return {
        "action": "ticket_closed",
        "ticket_id": ticket_id,
        "user_id": user_id,
        "timestamp": closed_at.isoformat(),
        "details": {
            "close_reason": close_reason,
            "closed_by": user_id
        }
    }
