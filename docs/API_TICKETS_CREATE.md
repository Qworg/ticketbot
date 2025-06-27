# Ticket Creation API Documentation

## POST /api/tickets

Creates a new support ticket for an authenticated user.

### Authentication Required
This endpoint requires a valid JWT token in the Authorization header using the Bearer scheme.

### Request Body

```json
{
    "guild_id": 123456789012345678,
    "creator_id": 987654321098765432,
    "reason": "I need help with my account setup",
    "category": "Support",
    "channel_id": 123456789012345679
}
```

#### Field Descriptions

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `guild_id` | integer | Yes | Discord guild (server) ID where the ticket is created | Must be a valid Discord snowflake (17-19 digits) |
| `creator_id` | integer | Yes | Discord user ID of the ticket creator | Must be a valid Discord snowflake and match authenticated user |
| `reason` | string | Yes | Description of the ticket/issue | 5-500 characters, cannot be empty or whitespace only |
| `category` | string | No | Optional category for ticket organization | Max 100 characters |
| `channel_id` | integer | No | Optional Discord channel ID for the ticket | Must be a valid Discord snowflake if provided |

### Response

#### Success Response (201 Created)

```json
{
    "success": true,
    "message": "Ticket 123 created successfully",
    "ticket": {
        "id": 123,
        "channel_id": 123456789012345679,
        "guild_id": 123456789012345678,
        "creator_id": 987654321098765432,
        "assigned_to": null,
        "status": "open",
        "category": "Support",
        "reason": "I need help with my account setup",
        "created_at": "2025-06-27T10:00:00.000Z",
        "updated_at": "2025-06-27T10:00:00.000Z",
        "closed_at": null,
        "close_reason": null,
        "is_shadow_closed": false
    }
}
```

#### Error Responses

##### 401 Unauthorized
```json
{
    "detail": "Authorization header required"
}
```

##### 403 Forbidden - Insufficient Permissions
```json
{
    "detail": "Insufficient permissions to create tickets"
}
```

##### 403 Forbidden - Creating Ticket for Another User
```json
{
    "detail": "Cannot create ticket for another user"
}
```

##### 409 Conflict - Duplicate Ticket
```json
{
    "detail": "User already has an open ticket in this guild"
}
```

##### 409 Conflict - Duplicate Channel ID
```json
{
    "detail": "A ticket with this channel ID already exists"
}
```

##### 422 Validation Error
```json
{
    "detail": [
        {
            "loc": ["body", "reason"],
            "msg": "reason must be at least 5 characters long",
            "type": "value_error"
        }
    ]
}
```

### Business Rules

1. **One Ticket Per Guild**: Users can only have one open ticket per Discord guild at a time
2. **Self-Creation Only**: Users can only create tickets for themselves (creator_id must match authenticated user)
3. **Permission Required**: Users must have the `CREATE_TICKET` permission
4. **Unique Channel IDs**: If a channel_id is provided, it must be unique across all tickets
5. **Auto Status**: New tickets automatically get status "open"
6. **Audit Logging**: All ticket creation events are logged for audit purposes

### Usage Examples

#### Basic Ticket Creation
```bash
curl -X POST "http://localhost:8000/api/tickets" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "guild_id": 123456789012345678,
    "creator_id": 987654321098765432,
    "reason": "I need help with setting up my account permissions"
  }'
```

#### Ticket with Category
```bash
curl -X POST "http://localhost:8000/api/tickets" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "guild_id": 123456789012345678,
    "creator_id": 987654321098765432,
    "reason": "Server is experiencing lag issues",
    "category": "Technical Support"
  }'
```

### Integration Notes

- This endpoint is designed to be called by Discord bots when users run ticket creation commands
- The `channel_id` field is typically populated when the Discord bot creates a dedicated ticket channel
- Created tickets can be retrieved using the `GET /api/tickets/{ticket_id}` endpoint (when implemented)
- Ticket status can be updated using the `PATCH /api/tickets/{ticket_id}` endpoint (when implemented)

### Error Handling

The endpoint includes comprehensive error handling for:
- Database connection failures
- Constraint violations
- Authentication failures
- Permission checks
- Input validation
- Rate limiting (via middleware)

All errors are logged appropriately for monitoring and debugging purposes.
