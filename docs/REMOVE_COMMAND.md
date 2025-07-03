# Remove Command Documentation

## Overview
The `/remove` command allows staff members to remove users from existing support tickets, revoking their access to participate in the conversation.

## Usage
```
/remove user:@username
```

## Parameters
- `user` (required): The Discord user to remove from the ticket

## Permissions
- **Staff Only**: This command can only be used by users with STAFF or ADMIN roles
- **Ticket Channel**: Must be used within an active ticket channel

## Functionality

### User Removal Process
1. **Validation**: Verifies the command is used in a ticket channel by staff
2. **Participant Check**: Ensures the user is currently a participant in the ticket
3. **Creator Protection**: Prevents removal of the ticket creator
4. **Permission Revocation**: Removes channel permissions for the user
5. **Database Update**: Soft-deletes the participant record (sets removed_at timestamp)
6. **Notifications**: Sends notifications to the channel and user via DM

### Channel Permissions
When a user is removed from a ticket, their permissions are revoked:
- Channel permissions are reset to inherit from @everyone (typically no access)
- User can no longer see or send messages in the ticket channel

### Notifications
- **Channel Notification**: An embed message is posted in the ticket channel announcing the participant removal
- **Direct Message**: The removed user receives a DM with:
  - Notification of removal from the ticket
  - Ticket information (ID, reason, status)
  - Original creation timestamp
  - Guild information

### Database Changes
The participant record in the `ticket_participants` table is soft-deleted:
- `removed_at`: Set to current timestamp
- Record remains in database for audit purposes
- User is no longer considered an active participant

## Restrictions

### Ticket Creator Protection
- The ticket creator cannot be removed from their own ticket
- This prevents accidentally locking out the person who reported the issue
- Only applies to the original creator (not staff who may have been assigned)

### Permission Requirements
- Only STAFF and ADMIN roles can use this command
- Regular users cannot remove participants, even from their own tickets

## Error Handling

### Common Error Messages
- `❌ This command can only be used in a server.` - Command used outside a guild
- `❌ This command can only be used by server members.` - Author is not a guild member
- `❌ This command can only be used in a ticket channel.` - Not used in a ticket channel
- `❌ Only staff members can remove users from tickets.` - User lacks required permissions
- `❌ [User] is not a participant in this ticket.` - Target user is not in the ticket
- `❌ Cannot remove the ticket creator from their own ticket.` - Attempted creator removal
- `❌ Failed to remove [User] from the ticket.` - Database removal failed
- `❌ An error occurred while removing the user. Please try again.` - Unexpected error

### Error Recovery
- If Discord permission removal fails, the database removal still succeeds
- Channel notifications are sent even if DM delivery fails
- Partial failures are logged but don't prevent the core removal operation

## Implementation Details

### Database Integration
- Uses `remove_participant_from_ticket()` function for soft deletion
- Maintains audit trail by preserving removed participant records
- Checks participant status with `is_participant_in_ticket()`

### Discord Integration
- Removes channel permission overwrites for the target user
- Sends formatted embed messages for notifications
- Handles DM failures gracefully (user may have DMs disabled)

### Security Considerations
- Staff-only access prevents abuse
- Creator protection prevents service disruption
- Audit trail maintained for accountability
- Permission validation at multiple levels

## Usage Examples

### Successful Removal
```
Staff: /remove user:@problemuser
Bot: ✅ Successfully removed @problemuser from the ticket.
[Channel notification embed appears]
[User receives DM notification]
```

### Creator Protection
```
Staff: /remove user:@ticketcreator
Bot: ❌ Cannot remove the ticket creator from their own ticket.
```

### Non-Participant
```
Staff: /remove user:@randomuser
Bot: ❌ @randomuser is not a participant in this ticket.
```

## Related Commands
- `/add` - Add users to tickets (opposite operation)
- `/close` - Close tickets (ends participation for all users)
- `/ticket` - Create new tickets

## Audit Trail
All removal actions are logged with:
- Timestamp of removal
- Staff member who performed the removal
- Target user who was removed
- Ticket ID and context

This information is available in application logs for administrative review and troubleshooting.
