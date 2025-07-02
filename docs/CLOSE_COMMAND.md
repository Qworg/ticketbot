# /close Command Documentation

This document describes the `/close` Discord slash command for closing support tickets in the Discord Ticket Bot.

## Overview

The `/close` command allows authorized users to close open support tickets with optional closure reasons. The command includes a confirmation step to prevent accidental closures and provides comprehensive audit logging.

## Command Syntax

```
/close [reason]
```

### Parameters

| Parameter | Type   | Required | Description                                    |
|-----------|--------|----------|------------------------------------------------|
| `reason`  | String | No       | Reason for closing the ticket (3-200 chars)   |

## Usage Examples

### Basic Usage
```
/close
```
Closes the ticket without specifying a reason.

### With Reason
```
/close reason:Issue has been resolved by updating user permissions
```
Closes the ticket with a specific closure reason for documentation.

### Complex Reason
```
/close reason:User confirmed the database connectivity issue was fixed after server restart
```
Closes the ticket with detailed resolution information.

## Permission Requirements

The `/close` command can be used by:

1. **Ticket Creator**: Can close their own tickets
2. **Assigned Staff**: Can close tickets they are assigned to
3. **Staff Members**: Can close any ticket in their guild
4. **Administrators**: Can close any ticket

### Permission Validation

- Command validates the user's relationship to the ticket
- Checks if user has appropriate staff role in the guild
- Prevents unauthorized closure attempts

## Command Flow

### 1. Initial Validation
- Verifies command is used in a ticket channel
- Checks if ticket exists and is not already closed
- Validates user permissions to close the ticket
- Validates reason parameter if provided

### 2. Confirmation Process
- Displays confirmation embed with ticket details
- Shows closure reason if provided
- Presents "Close Ticket" and "Cancel" buttons
- Sets 5-minute timeout for user response

### 3. Closure Execution
- Updates ticket status to "CLOSED" in database
- Sets `closed_at` timestamp
- Stores closure reason in database
- Creates audit log entry

### 4. Post-Closure Actions
- Sends closure notification embed to channel
- Updates channel permissions to read-only
- Adds "closed-" prefix to channel name
- Schedules channel deletion after 24 hours

## Validation Rules

### Reason Parameter
- **Optional**: Can be omitted for quick closures
- **Minimum Length**: 3 characters if provided
- **Maximum Length**: 200 characters
- **Trimming**: Leading/trailing whitespace removed

### Examples of Valid Reasons
```
"Issue resolved"
"User confirmed fix works"
"Duplicate of ticket #123"
"Problem solved by restarting service"
```

### Examples of Invalid Reasons
```
"ok"                    // Too short (< 3 chars)
"x".repeat(201)         // Too long (> 200 chars)
""                      // Empty string
"   "                   // Only whitespace
```

## Confirmation Embed

The confirmation embed displays:

### Ticket Information
- **Ticket ID**: Unique identifier
- **Current Status**: Current ticket state
- **Created Date**: When ticket was opened

### Request Information
- **Requested By**: User requesting closure
- **Username**: Discord username and discriminator

### Closure Details
- **Reason**: Closure reason if provided
- **Warning**: Notice about irreversible action

### Action Buttons
- **🔒 Close Ticket**: Confirms closure
- **❌ Cancel**: Cancels the operation

## Post-Closure Behavior

### Channel Updates
1. **Permissions**: Updated to read-only for regular users
2. **Name**: Prefixed with "closed-" 
3. **Notification**: Closure embed sent to channel
4. **Deletion**: Scheduled for 24 hours later

### Database Updates
1. **Status**: Set to "CLOSED"
2. **Timestamp**: `closed_at` field updated
3. **Reason**: Stored in `close_reason` field
4. **Audit Log**: Entry created with details

### Notification Embed

The closure notification includes:
- **Ticket Information**: ID, status, closed timestamp
- **Closure Reason**: If provided
- **Archive Notice**: 24-hour deletion warning
- **Thank You Message**: Professional closure message

## Error Handling

### Common Error Scenarios

#### Not a Ticket Channel
```
❌ This command can only be used in a ticket channel.
```

#### Ticket Already Closed
```
❌ This ticket is already closed.
```

#### Insufficient Permissions
```
❌ You don't have permission to close this ticket. 
Only the ticket creator or staff members can close tickets.
```

#### Invalid Reason Length
```
❌ Close reason must be at least 3 characters long.
❌ Close reason must be no more than 200 characters long.
```

### Timeout Handling
- 5-minute timeout for confirmation response
- Automatic embed update when timeout occurs
- Buttons disabled after timeout
- Clear timeout message displayed

## Security Considerations

### Permission Enforcement
- Multi-layered permission checking
- Database-level validation
- Role-based access control

### Audit Trail
- All closure attempts logged
- User identification recorded
- Timestamps and reasons preserved
- IP addresses tracked for security

### Data Retention
- Closed tickets remain in database
- Message history preserved
- Audit logs maintained
- Channel content archived

## Integration Points

### API Endpoints Used
- `GET /api/tickets/by-channel/{channel_id}`: Fetch ticket data
- `PATCH /api/tickets/{ticket_id}`: Update ticket status
- Audit logging system for closure tracking

### Database Tables Affected
- `tickets`: Status, timestamps, closure reason
- `audit_logs`: Closure action recording
- `users`: Permission validation
- `role_assignments`: Staff role checking

### External Services
- **Discord API**: Channel management, permissions
- **Database**: Ticket and audit data storage
- **Logging**: Error and event tracking

## Troubleshooting

### Command Not Responding
1. Check bot permissions in channel
2. Verify ticket channel is properly registered
3. Confirm user has required permissions

### Permission Denied Errors
1. Verify user role assignments in database
2. Check guild staff role configuration
3. Confirm ticket ownership or assignment

### Timeout Issues
1. Check network connectivity
2. Verify Discord API status
3. Review bot rate limiting

## Best Practices

### For Users
- Always provide meaningful closure reasons
- Confirm ticket resolution before closing
- Review ticket history before closure

### For Staff
- Document resolution steps in reason
- Verify user satisfaction before closing
- Use clear, professional language

### For Administrators
- Regularly review closure reasons
- Monitor closure patterns and trends
- Ensure proper staff training on procedures

## Configuration Options

### Channel Deletion Delay
- Default: 24 hours
- Configurable per guild
- Minimum: 1 hour, Maximum: 168 hours (7 days)

### Auto-Transcript Generation
- Can be enabled for automatic transcript creation
- Transcripts generated before channel deletion
- Links sent to ticket creator via DM

### Closure Notifications
- Configurable notification templates
- Custom messages per guild
- Optional email notifications for creators

## Related Commands

- [`/ticket`](TICKET_COMMAND.md): Create new tickets
- [`/claim`](CLAIM_COMMAND.md): Assign tickets to staff
- [`/add`](ADD_COMMAND.md): Add participants to tickets
- [`/transcript`](TRANSCRIPT_COMMAND.md): Generate ticket transcripts

## API Reference

For developers integrating with the ticket system, see:
- [Ticket API Documentation](API_TICKETS_CREATE.md)
- [Ticket Closure Validation](TICKET_CLOSURE_VALIDATION.md)
- [Authentication Middleware](AUTHENTICATION_MIDDLEWARE.md)
