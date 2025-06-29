# Ticket Closure Validation

This document describes the comprehensive ticket closure validation system implemented in the Discord Ticket Bot.

## Overview

The ticket closure validation system ensures that tickets can only be closed under appropriate conditions, with proper permissions, and with adequate documentation of the closure reason.

## Validation Rules

### 1. Close Reason Requirements

When closing a ticket, a `close_reason` must be provided that meets the following criteria:

- **Required**: Cannot be `null`, empty, or whitespace only
- **Minimum Length**: Must be at least 3 characters long
- **Maximum Length**: Cannot exceed 200 characters
- **Trimming**: Leading and trailing whitespace is automatically trimmed

#### Examples

```json
// Valid close reasons
{
  "close_reason": "Issue has been resolved"
}

{
  "close_reason": "User requested closure after solution was provided"
}

// Invalid close reasons
{
  "close_reason": null  // ❌ Required
}

{
  "close_reason": "Hi"  // ❌ Too short (minimum 3 characters)
}

{
  "close_reason": "x".repeat(201)  // ❌ Too long (maximum 200 characters)
}
```

### 2. Permission Requirements

Users can only close tickets based on their role and relationship to the ticket:

#### User (Regular Users)
- ✅ Can close their own tickets (where `creator_id` matches their Discord ID)
- ❌ Cannot close tickets created by other users

#### Staff
- ✅ Can close tickets assigned to them (where `assigned_to` matches their Discord ID)
- ✅ Can close any ticket (staff have `MANAGE_TICKETS` permission)

#### Admin
- ✅ Can close any ticket in the system

### 3. Dependency Validation

Before closing a ticket, the system checks for any unresolved dependencies:

#### Current Checks
- **Already Closed**: Cannot close a ticket that is already in `closed` status
- **Future Extensions**: The system is designed to support additional dependency checks such as:
  - Related tickets that must be closed first
  - Required approvals or sign-offs
  - Pending external integrations

## API Usage

### Close Ticket Endpoint

```http
PATCH /api/tickets/{ticket_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "status": "closed",
  "close_reason": "Issue has been resolved successfully"
}
```

### Response Codes

| Code | Description | Example Scenario |
|------|-------------|------------------|
| 200 | Success | Ticket closed successfully |
| 400 | Bad Request | Invalid close reason, permission denied, or dependency issue |
| 401 | Unauthorized | Invalid or missing JWT token |
| 403 | Forbidden | User lacks necessary permissions |
| 404 | Not Found | Ticket does not exist |
| 409 | Conflict | Concurrency issue (ticket modified by another user) |
| 500 | Server Error | Database or unexpected error |

### Error Examples

```json
// Missing close reason
{
  "detail": "Ticket 123: Close reason is required when closing a ticket"
}

// Insufficient permissions
{
  "detail": "Ticket 123: You do not have permission to close this ticket"
}

// Already closed
{
  "detail": "Ticket 123: Cannot close ticket due to unresolved dependencies: Ticket is already closed"
}

// Invalid reason length
{
  "detail": "Ticket 123: Close reason must be at least 3 characters long"
}
```

## Implementation Details

### Validation Flow

1. **Basic Validation**: Check close reason format and length
2. **Permission Check**: Verify user has permission to close the ticket
3. **Dependency Check**: Ensure no unresolved dependencies prevent closure
4. **Status Transition**: Validate the status transition using the state machine
5. **Database Update**: Set `closed_at` timestamp and `close_reason`
6. **Audit Logging**: Create audit log entry for the closure

### Code Components

#### Core Functions

- `validate_close_reason(close_reason)`: Validates close reason format
- `validate_ticket_closure_permission(ticket, user_id, user_role)`: Checks user permissions
- `check_ticket_dependencies(ticket)`: Checks for blocking dependencies
- `validate_ticket_closure(ticket, user_id, user_role, close_reason)`: Main validation function
- `create_closure_audit_entry(ticket_id, user_id, close_reason, closed_at)`: Creates audit log

#### Exception Classes

- `TicketClosureError`: Raised when closure validation fails
- `StatusTransitionError`: Raised for invalid status transitions
- `ValueError`: Raised for format validation failures

### Database Changes

When a ticket is successfully closed:

- `status` is set to `"closed"`
- `closed_at` is set to the current timestamp
- `close_reason` is set to the provided reason
- `updated_at` is automatically updated by the database

## Testing

### Unit Tests

The closure validation system includes comprehensive unit tests covering:

- Valid and invalid close reason formats
- Permission validation for all user roles
- Dependency checking scenarios
- Error handling and exception messages
- Audit log entry creation

### Integration Tests

Integration tests verify the complete closure flow:

- End-to-end API requests with various scenarios
- Authentication and authorization integration
- Database transaction handling
- Error response formatting

### Test Coverage

Run tests with coverage reporting:

```bash
# Run closure-specific tests
pytest tests/test_status_state_machine.py::TestTicketClosureValidation -v
pytest tests/test_ticket_update.py::TestTicketClosureIntegration -v

# Run with coverage
pytest --cov=app.status --cov-report=html tests/
```

## Security Considerations

1. **Authorization**: All closure operations require valid JWT authentication
2. **Permission Enforcement**: Strict role-based access control prevents unauthorized closures
3. **Audit Trail**: All closure attempts are logged for security monitoring
4. **Input Validation**: Close reasons are validated to prevent injection attacks
5. **Concurrency Control**: Database constraints prevent race conditions

## Monitoring and Logging

The system logs the following events:

- Successful ticket closures with user and reason
- Failed closure attempts with specific validation errors
- Permission violations for security monitoring
- Database errors for operational troubleshooting

### Log Examples

```
INFO: Ticket 123 closure validation passed for user 456789012345678901
INFO: Updated ticket 123 status from open to closed
ERROR: Ticket closure validation failed: Ticket 123: Close reason must be at least 3 characters long
WARN: User 456789012345678901 attempted to close ticket 123 without permission
```

## Future Enhancements

The closure validation system is designed to be extensible:

1. **Advanced Dependencies**: Support for related ticket dependencies
2. **Approval Workflows**: Multi-step approval processes for certain ticket types
3. **Custom Validation Rules**: Guild-specific closure requirements
4. **Integration Hooks**: Webhook notifications for closure events
5. **Bulk Closure**: Support for closing multiple tickets with batch validation

## Migration Guide

For existing installations upgrading to include closure validation:

1. **Database**: No migration required (uses existing fields)
2. **API Changes**: Existing closure endpoints now enforce validation
3. **Error Handling**: Update client applications to handle new error codes
4. **Testing**: Verify existing automation works with new validation rules

## Related Documentation

- [Ticket Status State Machine](TICKET_STATUS_STATE_MACHINE.md)
- [Permissions System](PERMISSIONS.md)
- [API Documentation](API_TICKETS_CREATE.md)
- [Authentication Middleware](AUTHENTICATION_MIDDLEWARE.md)
