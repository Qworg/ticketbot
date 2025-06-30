# Ticket Command Documentation

## Overview

The `/ticket` command allows users to create new support tickets in Discord. When executed, it creates a private channel where the user can communicate with staff members about their issue.

## Usage

```
/ticket reason: <reason for creating the ticket>
```

## Parameters

### reason (Required)
- **Type**: String
- **Length**: 5-500 characters
- **Description**: A brief description of why you're creating the ticket
- **Examples**: 
  - "Need help with my account settings"
  - "Experiencing technical issues with the bot"
  - "Request for server permissions"

## Behavior

### Command Execution Flow

1. **Validation**: The command validates that:
   - The user is in a server (not DM)
   - The user is a server member
   - The reason meets length requirements (5-500 characters)
   - The user doesn't already have an open ticket in the server

2. **User Management**: 
   - Creates a user record in the database if it doesn't exist
   - Associates the Discord user with a database user

3. **Category Management**:
   - Looks for existing ticket categories named "tickets", "support", or "help"
   - Creates a new "🎫 Tickets" category if none exists

4. **Channel Creation**:
   - Generates a unique channel name: `ticket-{username}-{last4digits}`
   - Creates a private text channel with proper permissions
   - Places the channel in the ticket category

5. **Permission Setup**:
   - Denies @everyone from viewing the channel
   - Grants the ticket creator view and send permissions
   - Grants the bot full channel management permissions
   - Grants staff roles (Staff, Support, Moderator, Admin, Administrator) access

6. **Database Storage**:
   - Creates a ticket record in the database
   - Links the ticket to the Discord channel
   - Sets initial status to "open"

7. **Initial Messages**:
   - Sends a welcome embed in the ticket channel with ticket details
   - Adds action buttons for claiming and closing the ticket
   - Sends a confirmation DM to the user

## Permissions

- **Required Permission**: `CREATE_TICKET`
- **Rate Limiting**: 2 tickets per minute per user
- **Cooldown**: 30 seconds between uses

## Error Handling

The command handles various error scenarios:

- **Already Has Ticket**: "❌ You already have an open ticket in this server. Please close your existing ticket before creating a new one."
- **DM Usage**: "❌ This command can only be used in a server."
- **Invalid User**: "❌ This command can only be used by server members."
- **Validation Errors**: Specific messages for reason length requirements
- **System Errors**: Generic error message with logging for debugging

## Examples

### Valid Usage
```
/ticket reason: I need help setting up my Discord bot
```

### Invalid Usage
```
/ticket reason: hi
// Error: Ticket reason must be at least 5 characters long

/ticket reason: [500+ character message]
// Error: Ticket reason must not exceed 500 characters
```

## Technical Details

### Database Schema
The command interacts with:
- `users` table: For user management
- `tickets` table: For ticket tracking

### Discord API Usage
- Creates channels and categories
- Sets permission overwrites
- Sends embeds and components
- Handles direct messages

### Security Features
- Permission validation
- Rate limiting and cooldowns
- Proper channel isolation
- Audit logging

## Troubleshooting

### Common Issues

1. **"User not found in database"**: The user needs to go through OAuth2 authentication first, or the command will create a basic user record.

2. **Channel creation fails**: Ensure the bot has `Manage Channels` permission in the server.

3. **Permission errors**: Verify the bot has the required permissions and the user has the `CREATE_TICKET` permission.

4. **Category creation fails**: The bot needs `Manage Channels` permission to create categories.

### Logs
All ticket creation events are logged with:
- Ticket ID
- User ID  
- Guild ID
- Channel ID
- Timestamp

Error events include full stack traces for debugging.
