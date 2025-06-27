# Ticket Database Model Documentation

## Overview

The Ticket model represents support tickets created by Discord users within Discord guilds. This model is the core entity for the ticket management system, tracking the lifecycle of each support request from creation to closure.

## Table Schema

### Table Name: `tickets`

### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT, NOT NULL | Unique serial primary key for the ticket |
| `channel_id` | BIGINT | UNIQUE, NOT NULL | Discord channel ID (snowflake) where the ticket exists |
| `guild_id` | BIGINT | NOT NULL | Discord guild ID (snowflake) where the ticket was created |
| `creator_id` | BIGINT | NOT NULL | Discord user ID (snowflake) of the user who created the ticket |
| `assigned_to` | BIGINT | NULLABLE | Discord user ID (snowflake) of the staff member assigned to the ticket |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'open' | Current status of the ticket |
| `category` | VARCHAR(100) | NULLABLE | Optional categorization for ticket organization |
| `reason` | TEXT | NOT NULL | User-provided description of the issue or request |
| `created_at` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Timestamp when the ticket was created |
| `updated_at` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP, ON UPDATE CURRENT_TIMESTAMP | Timestamp when the ticket was last updated |
| `closed_at` | DATETIME | NULLABLE | Timestamp when the ticket was closed |
| `close_reason` | TEXT | NULLABLE | Reason provided when the ticket was closed |
| `is_shadow_closed` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether the ticket is shadow closed (archived but not fully closed) |

## Indexes

The following indexes are created for optimal query performance:

### Primary Indexes
- `ix_tickets_id` - Primary key index
- `ix_tickets_channel_id` - Unique index on channel_id for fast Discord channel lookups

### Performance Indexes
- `idx_tickets_guild_status` - Composite index on (guild_id, status) for efficient guild-specific status filtering
- `idx_tickets_assigned_to` - Index on assigned_to for staff ticket queries
- `idx_tickets_creator_id` - Index on creator_id for user ticket lookups
- `idx_tickets_status` - Index on status for status-based queries
- `idx_tickets_created_at` - Index on created_at for chronological ordering

## Relationships

### Current Relationships
Currently, the ticket model doesn't have explicit foreign key relationships defined in the database schema, but it logically references:

1. **Discord Users** (via `creator_id` and `assigned_to`)
   - References Discord user IDs (snowflakes)
   - No formal foreign key constraint as Discord users may not exist in the local database

2. **Discord Guilds** (via `guild_id`)
   - References Discord guild IDs (snowflakes)
   - Will be formalized when guilds table is implemented

### Future Relationships
When additional tables are implemented, the following relationships will be established:

1. **Guild Relationship**
   - `guild_id` will reference `guilds.id`
   - Foreign key constraint with appropriate cascade behavior

2. **User Relationships**
   - `creator_id` and `assigned_to` may reference `users.discord_id`
   - Foreign key constraints if users table tracks Discord users

3. **Message Relationships**
   - One-to-many relationship with ticket messages
   - `messages.ticket_id` will reference `tickets.id`

## Status Values

The ticket status follows a defined state machine:

- `open` - Initial state when ticket is created
- `in_progress` - Ticket has been claimed by staff and is being worked on
- `resolved` - Issue has been resolved, awaiting closure confirmation
- `closed` - Ticket is fully closed and archived

## Model Methods

### Instance Methods

#### `is_open() -> bool`
Returns `True` if the ticket is in an open state (`open` or `in_progress`).

#### `is_closed() -> bool`
Returns `True` if the ticket status is `closed`.

#### `can_be_assigned() -> bool`
Returns `True` if the ticket can be assigned to staff (status is `open` or `in_progress` and not closed).

#### `to_dict() -> dict`
Converts the ticket instance to a dictionary representation with proper datetime serialization.

## Usage Examples

### Creating a New Ticket
```python
from app.models.ticket import Ticket

ticket = Ticket(
    channel_id=123456789012345678,
    guild_id=987654321098765432,
    creator_id=111222333444555666,
    reason="Unable to access premium features after payment"
)
```

### Querying Tickets
```python
from sqlalchemy.orm import Session
from app.models.ticket import Ticket

# Get all open tickets in a guild
open_tickets = session.query(Ticket).filter_by(
    guild_id=987654321098765432,
    status='open'
).all()

# Get tickets assigned to a specific staff member
staff_tickets = session.query(Ticket).filter_by(
    assigned_to=777888999000111222
).all()

# Get user's tickets
user_tickets = session.query(Ticket).filter_by(
    creator_id=111222333444555666
).all()
```

## Migration Information

- **Migration File**: `2025_06_27_0605-3d0546d0b919_create_tickets_table.py`
- **Created**: 2025-06-27 06:05:37 UTC
- **Dependencies**: Requires users and role_assignments tables

## Performance Considerations

1. **Indexing**: All commonly queried fields are indexed for optimal performance
2. **Composite Index**: The `(guild_id, status)` composite index optimizes the most common query pattern
3. **Unique Constraints**: `channel_id` uniqueness ensures one-to-one mapping with Discord channels
4. **Timestamp Tracking**: Automatic timestamp updates for audit trails

## Security Considerations

1. **Discord ID Validation**: Channel, guild, and user IDs should be validated as proper Discord snowflakes
2. **Access Control**: Ticket access should be controlled based on guild membership and roles
3. **Data Retention**: Consider implementing data retention policies for closed tickets
4. **Audit Logging**: All ticket modifications should be logged for security and compliance

## Future Enhancements

1. **Priority Field**: Add ticket priority levels (low, medium, high, critical)
2. **Tags System**: Implement flexible tagging system for better categorization
3. **SLA Tracking**: Add fields for tracking response and resolution times
4. **Escalation**: Implement automatic escalation based on ticket age and priority
5. **Templates**: Support for ticket templates based on category
