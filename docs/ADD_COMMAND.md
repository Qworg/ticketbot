# Add Command Documentation

## Overview
The `/add` command allows staff members to add users to existing support tickets, giving them access to participate in the conversation.

## Usage
```
/add user:@username
```

## Parameters
- `user` (required): The Discord user to add to the ticket

## Permissions
- **Staff Only**: This command can only be used by users with STAFF or ADMIN roles
- **Ticket Channel**: Must be used within an active ticket channel

## Functionality

### User Addition Process
1. **Validation**: Verifies the command is used in a ticket channel by staff
2. **Duplicate Check**: Ensures the user isn't already a participant
3. **Permission Grant**: Adds channel read/send permissions for the user
4. **Database Update**: Records the participant in the ticket_participants table
5. **Notifications**: Sends notifications to the channel and user via DM

### Channel Permissions
When a user is added to a ticket, they receive:
- `VIEW_CHANNEL` - Can see the ticket channel
- `SEND_MESSAGES` - Can send messages in the channel

### Notifications
- **Channel Notification**: An embed message is posted in the ticket channel announcing the new participant
- **Direct Message**: The added user receives a DM with:
  - Ticket information (ID, reason, status)
  - Creation timestamp
  - Guild information

### Database Changes
A new record is created in the `ticket_participants` table with:
- `ticket_id`: ID of the ticket
- `user_id`: Discord ID of the added user
- `role`: Set to 'participant'
- `added_at`: Current timestamp
- `removed_at`: NULL (active participant)

## Error Handling

### Common Error Messages
- `❌ This command can only be used in a server.` - Command used outside a guild
- `❌ This command can only be used by server members.` - Author is not a member
- `❌ This command can only be used in a ticket channel.` - Not in a ticket channel
- `❌ Only staff members can add users to tickets.` - Insufficient permissions
- `❌ {user} is already a participant in this ticket.` - User already added
- `❌ Please specify a valid user to add.` - Invalid user parameter

### Permission Failures
If the bot lacks permissions to modify channel permissions, the operation will fail gracefully with an error message.

## Rate Limiting
- **Cooldown**: 3 seconds between uses
- **Rate Limit**: Maximum 20 add operations per minute per user

## Audit Logging
All successful participant additions are logged with:
- User ID of the added participant
- Ticket ID
- Staff member who performed the action
- Timestamp of the action

## Examples

### Successful Addition
```
/add user:@johndoe
```
Response: `✅ Successfully added @johndoe to the ticket.`

### User Already Participant
```
/add user:@janedoe
```
Response: `❌ @janedoe is already a participant in this ticket.`

### Insufficient Permissions
```
/add user:@someone
```
Response: `❌ Only staff members can add users to tickets.`

## Related Commands
- `/remove` - Remove a user from the ticket
- `/close` - Close the ticket
- `/ticket` - Create a new ticket

## Technical Implementation
- **Command Class**: `AddCommand` in `app/commands/implementations/add.py`
- **Database Model**: `TicketParticipant` in `app/models/ticket_participant.py`
- **Permissions**: Uses role-based permission system
- **Testing**: Comprehensive unit tests in `tests/test_add_command.py`
