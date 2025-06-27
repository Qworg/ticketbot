# Ticket Status State Machine

This document describes the ticket status state machine implementation for the Discord Ticket Bot.

## Overview

The ticket status state machine enforces valid status transitions and provides audit logging for all status changes. This ensures data integrity and provides a clear workflow for ticket lifecycle management.

## Status Values

The system supports four ticket statuses:

| Status | Value | Description |
|--------|--------|-------------|
| Open | `open` | Newly created ticket, waiting for staff response |
| In Progress | `in_progress` | Ticket is being actively worked on by staff |
| Resolved | `resolved` | Issue has been addressed, awaiting closure confirmation |
| Closed | `closed` | Ticket is completed and archived |

## State Transitions

The following state transitions are valid:

### From OPEN
- → **IN_PROGRESS**: Staff claims and begins working on the ticket
- → **CLOSED**: Direct closure without resolution (e.g., spam, duplicate)

### From IN_PROGRESS
- → **RESOLVED**: Issue has been addressed and resolved
- → **CLOSED**: Direct closure without resolution
- → **OPEN**: Staff unclaims ticket, returns to open state

### From RESOLVED
- → **CLOSED**: Final closure after resolution confirmation
- → **IN_PROGRESS**: Reopen if issue persists or needs additional work

### From CLOSED
- **No transitions allowed** - Closed tickets are terminal

## State Transition Matrix

```
Current Status    → Valid Next Statuses
─────────────────────────────────────────
OPEN             → IN_PROGRESS, CLOSED
IN_PROGRESS      → RESOLVED, CLOSED, OPEN
RESOLVED         → CLOSED, IN_PROGRESS
CLOSED           → (none)
```

## Implementation

### Status Constants

```python
from app.status import TicketStatus

# Access status values
TicketStatus.OPEN.value          # "open"
TicketStatus.IN_PROGRESS.value   # "in_progress"
TicketStatus.RESOLVED.value      # "resolved"
TicketStatus.CLOSED.value        # "closed"
```

### Validation Functions

```python
from app.status import validate_status_transition, get_valid_next_statuses

# Validate a transition
is_valid = validate_status_transition("open", "in_progress")  # True
is_valid = validate_status_transition("open", "resolved")    # False

# Get valid next statuses
next_statuses = get_valid_next_statuses("open")  # ["in_progress", "closed"]
```

### Ticket Model Integration

```python
from app.models.ticket import Ticket

# Create ticket with default status
ticket = Ticket(guild_id=123, creator_id=456, reason="Help needed")
print(ticket.status)  # "open"

# Check status states
ticket.is_open()        # True
ticket.is_closed()      # False
ticket.can_be_assigned() # True

# Validate transitions
ticket.validate_status_transition("in_progress")  # True
ticket.validate_status_transition("resolved")     # False

# Update status with validation and logging
ticket.update_status(
    new_status="in_progress",
    changed_by=789,
    db_session=session
)
```

### Status Update Requirements

#### Close Reason Requirement
When transitioning to `CLOSED` status, a close reason must be provided:

```python
# This will raise ValueError: Close reason is required
ticket.update_status("closed", changed_by=123)

# Correct usage
ticket.update_status(
    new_status="closed",
    changed_by=123,
    close_reason="Issue resolved by user"
)
```

#### Database Session
For persistent status updates, provide a database session:

```python
from app.database import get_db_session

with get_db_session() as session:
    ticket.update_status(
        new_status="in_progress",
        changed_by=staff_id,
        db_session=session
    )
```

## Error Handling

### StatusTransitionError
Raised when attempting an invalid status transition:

```python
from app.status import StatusTransitionError

try:
    ticket.update_status("resolved", changed_by=123)
except StatusTransitionError as e:
    print(f"Invalid transition: {e.current_status} → {e.new_status}")
    print(f"Valid options: {get_valid_next_statuses(e.current_status)}")
```

### Validation Errors
Raised when required parameters are missing:

```python
try:
    ticket.update_status("closed", changed_by=123)  # Missing close_reason
except ValueError as e:
    print("Close reason is required when transitioning to closed status")
```

## Audit Logging

All status transitions are automatically logged with:

- Ticket ID
- Previous status
- New status
- User who made the change
- Reason (optional)
- Timestamp

```python
from app.status import log_status_transition

# Manual logging (automatic in update_status)
log_entry = log_status_transition(
    ticket_id=123,
    previous_status="open",
    new_status="in_progress",
    changed_by=456,
    reason="Staff member claimed ticket"
)

# Convert to dictionary for storage/API responses
log_dict = log_entry.to_dict()
```

## API Integration

### Status Update Request Schema

```python
from app.schemas import TicketStatusUpdateRequest

# Valid request
request = TicketStatusUpdateRequest(
    new_status="closed",
    close_reason="Issue resolved"
)

# Validation errors
request = TicketStatusUpdateRequest(
    new_status="closed"  # Missing close_reason - validation error
)
```

### Response Schema

```python
from app.schemas import TicketStatusUpdateResponse

response = TicketStatusUpdateResponse(
    success=True,
    message="Status updated successfully",
    ticket=ticket_data,
    previous_status="open",
    transition_log=log_entry.to_dict()
)
```

## Utility Functions

### Status Checking
```python
from app.status import (
    is_open_status, is_closed_status, is_resolved_status,
    can_be_assigned, is_terminal_status
)

is_open_status("in_progress")    # True
is_closed_status("closed")       # True
can_be_assigned("resolved")      # False
is_terminal_status("closed")     # True
```

### Status Information
```python
from app.status import get_status_description

description = get_status_description("in_progress")
# "In Progress - Being worked on by staff"
```

## Best Practices

1. **Always validate transitions** before updating status in the database
2. **Provide close reasons** when closing tickets for audit purposes
3. **Use database sessions** for persistent updates with proper error handling
4. **Log all status changes** for compliance and debugging
5. **Check permissions** before allowing status updates in API endpoints
6. **Handle validation errors** gracefully in user interfaces

## Testing

### Unit Tests
- `tests/test_status_state_machine.py` - Core state machine logic
- `tests/test_ticket_status_integration.py` - Ticket model integration

### Running Tests
```bash
python -m pytest tests/test_status_state_machine.py -v
python -m pytest tests/test_ticket_status_integration.py -v
```

## Migration Considerations

When updating existing tickets to use the new status system:

1. Existing `'open'` and `'closed'` statuses are compatible
2. Add new `'in_progress'` and `'resolved'` statuses as needed
3. Update any hardcoded status checks to use the new constants
4. Ensure all status updates go through the validation system

## Future Enhancements

Potential future improvements:

1. **Custom Status Workflows** - Allow guilds to define custom status flows
2. **Automatic Transitions** - Timer-based transitions (e.g., auto-close after resolution)
3. **Status Change Notifications** - Discord/email notifications for status changes
4. **Bulk Status Updates** - Mass update operations with validation
5. **Status Analytics** - Metrics on status transition patterns and timing
