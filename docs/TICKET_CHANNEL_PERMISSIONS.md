# Ticket Channel Permission Structure

This document describes the permission structure for Discord ticket channels and how to configure guild-specific role permissions.

## Permission Overview

When a ticket channel is created, the following permission structure is applied:

### 1. @everyone Role (DENY ALL)
- **VIEW_CHANNEL**: Denied
- **SEND_MESSAGES**: Denied
- **Purpose**: Ensures tickets are private by default

### 2. Ticket Creator (ALLOW)
- **VIEW_CHANNEL**: Allowed
- **SEND_MESSAGES**: Allowed  
- **READ_MESSAGE_HISTORY**: Allowed
- **Purpose**: Creator can participate in their ticket

### 3. Bot (FULL ACCESS)
- **VIEW_CHANNEL**: Allowed
- **SEND_MESSAGES**: Allowed
- **READ_MESSAGE_HISTORY**: Allowed
- **MANAGE_CHANNELS**: Allowed
- **Purpose**: Bot needs full access to manage tickets

### 4. Staff Roles (CONFIGURABLE)
Based on guild configuration in database:

#### Staff Roles
- **VIEW_CHANNEL**: Allowed
- **SEND_MESSAGES**: Allowed
- **READ_MESSAGE_HISTORY**: Allowed
- **Purpose**: Staff can help with tickets

#### Admin Roles  
- **VIEW_CHANNEL**: Allowed
- **SEND_MESSAGES**: Allowed
- **READ_MESSAGE_HISTORY**: Allowed
- **MANAGE_CHANNELS**: Allowed
- **MANAGE_MESSAGES**: Allowed
- **Purpose**: Admins can fully manage tickets

## Guild Configuration

### Database Configuration
Guild-specific role configurations are stored in the `guilds` table:

```sql
CREATE TABLE guilds (
    id BIGINT PRIMARY KEY,           -- Discord guild ID
    name VARCHAR(100) NOT NULL,      -- Guild name
    staff_role_ids JSON,             -- Array of staff role IDs
    admin_role_ids JSON,             -- Array of admin role IDs
    ticket_category_id BIGINT,       -- Ticket category channel ID
    ticket_category_name VARCHAR(100) DEFAULT '🎫 Tickets',
    auto_archive_hours BIGINT DEFAULT 24,
    auto_transcript BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

### Adding Staff/Admin Roles
To configure staff and admin roles for a guild:

```python
from app.models.guild import create_or_update_guild

# Example: Configure roles for a guild
guild_config = create_or_update_guild(
    db=session,
    guild_id=123456789012345678,
    name="My Discord Server",
    staff_role_ids=[111111111111111111, 222222222222222222],  # Support, Moderator
    admin_role_ids=[333333333333333333],                      # Administrator
    ticket_category_name="🎫 Support Tickets"
)
```

### Fallback Role Detection
If no roles are configured in the database, the system falls back to detecting common role names:

- `staff`
- `support` 
- `moderator`
- `admin`
- `administrator`

This detection is **case-insensitive**.

## Permission Update Functions

### Adding Users to Tickets
```python
# Grant channel access to a user
success = await ticket_command.update_channel_permissions_for_user(
    channel=ticket_channel,
    user=discord_user,
    grant_access=True
)
```

### Removing Users from Tickets
```python
# Revoke channel access from a user
success = await ticket_command.update_channel_permissions_for_user(
    channel=ticket_channel,
    user=discord_user,
    grant_access=False
)
```

### Adding Roles to Tickets
```python
# Grant channel access to a role
success = await ticket_command.update_channel_permissions_for_role(
    channel=ticket_channel,
    role=discord_role,
    grant_access=True,
    is_admin=False  # Set to True for admin permissions
)
```

## Error Handling

### Insufficient Bot Permissions
If the bot lacks the required permissions to modify channel permissions:
- The function returns `False`
- Error is logged with details
- Ticket creation continues with basic permissions

### Database Query Failures
If guild configuration cannot be retrieved:
- System falls back to role name detection
- Error is logged for monitoring
- Ticket creation continues with fallback permissions

### Permission Update Failures
If permission updates fail during ticket management:
- Function returns `False` to indicate failure
- Detailed error logging for troubleshooting
- User receives appropriate error message

## Monitoring and Logging

All permission operations are logged with the following information:
- Guild ID and channel ID
- User/role being modified
- Permission changes applied
- Success/failure status
- Error details if applicable

Log levels:
- `INFO`: Successful permission operations
- `DEBUG`: Detailed permission calculations
- `ERROR`: Permission failures and database errors

## Security Considerations

1. **Principle of Least Privilege**: Users only get necessary permissions
2. **Private by Default**: @everyone is always denied access
3. **Role Validation**: Only configured roles get automatic access
4. **Audit Trail**: All permission changes are logged
5. **Fallback Safety**: System degrades gracefully on failures

## Testing

The permission system includes comprehensive test coverage:

### Unit Tests
- Permission calculation logic
- Database integration
- Error handling scenarios
- Fallback mechanisms

### Integration Tests  
- End-to-end permission setup
- Guild configuration workflows
- Permission update operations
- Database failure scenarios

Run tests with:
```bash
pytest tests/test_ticket_command.py::TestTicketCommand -v
pytest tests/test_ticket_permission_integration.py -v
```
