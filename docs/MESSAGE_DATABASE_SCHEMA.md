# Message Database Model Documentation

## Overview

The Message model represents Discord messages stored in ticket channels. It provides functionality for tracking, storing, and managing all messages within the ticket system.

## Database Schema

### Table: messages

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PRIMARY KEY | Discord message ID (snowflake) |
| ticket_id | INTEGER | NOT NULL, FK to tickets.id | Reference to parent ticket |
| author_id | BIGINT | NOT NULL | Discord user ID of message author |
| content | TEXT | NOT NULL | Message text content |
| attachments | JSON | NULL | Metadata for file attachments |
| is_staff_only | BOOLEAN | NOT NULL, DEFAULT false | Whether message is staff-only |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Message creation timestamp |
| edited_at | TIMESTAMP | NULL | Message edit timestamp |
| is_deleted | BOOLEAN | NOT NULL, DEFAULT false | Soft deletion flag |

### Indexes

- `ix_messages_id`: Primary key index on id
- `ix_messages_ticket_id`: Index on ticket_id for ticket message queries
- `ix_messages_author_id`: Index on author_id for user message queries
- `ix_messages_is_staff_only`: Index on is_staff_only for filtering
- `ix_messages_ticket_created`: Composite index on (ticket_id, created_at) for ordering
- `ix_messages_ticket_staff_only`: Composite index on (ticket_id, is_staff_only) for filtering

### Foreign Key Constraints

- `ticket_id` → `tickets.id` with CASCADE DELETE

## Model Features

### Message Creation

```python
from app.models import Message
from datetime import datetime

# Basic message
message = Message(
    id=123456789012345678,  # Discord message ID
    ticket_id=1,
    author_id=987654321098765432,
    content="Hello, this is a test message"
)

# Message with attachments
message = Message(
    id=123456789012345679,
    ticket_id=1,
    author_id=987654321098765432,
    content="Here's a file attachment",
    attachments=[
        {
            "filename": "screenshot.png",
            "size": 1024,
            "content_type": "image/png",
            "url": "https://cdn.discordapp.com/attachments/..."
        }
    ]
)

# Staff-only message
staff_message = Message(
    id=123456789012345680,
    ticket_id=1,
    author_id=111222333444555666,
    content="Internal staff note",
    is_staff_only=True
)
```

### Relationships

```python
# Access ticket from message
ticket = message.ticket

# Access messages from ticket
messages = ticket.messages
```

### Serialization

```python
# Convert to dictionary for API responses
message_dict = message.to_dict()
# Returns:
# {
#     "id": "123456789012345678",
#     "ticket_id": 1,
#     "author_id": "987654321098765432",
#     "content": "Hello, this is a test message",
#     "attachments": null,
#     "is_staff_only": false,
#     "created_at": "2025-07-08T01:53:05.131066",
#     "edited_at": null,
#     "is_deleted": false
# }
```

## Usage Patterns

### Filtering Messages

```python
from sqlalchemy.orm import Session
from app.models import Message

# Get all messages for a ticket
messages = session.query(Message).filter_by(ticket_id=1).all()

# Get only public messages
public_messages = session.query(Message).filter(
    Message.ticket_id == 1,
    Message.is_staff_only == False,
    Message.is_deleted == False
).order_by(Message.created_at).all()

# Get staff-only messages
staff_messages = session.query(Message).filter(
    Message.ticket_id == 1,
    Message.is_staff_only == True
).all()
```

### Message Editing

```python
from datetime import datetime

# Update message content and edit timestamp
message.content = "Updated message content"
message.edited_at = datetime.utcnow()
session.commit()
```

### Soft Deletion

```python
# Soft delete a message
message.is_deleted = True
session.commit()

# The message remains in database but is marked as deleted
```

## Attachment Handling

The `attachments` field stores JSON metadata about file attachments:

```json
[
    {
        "filename": "document.pdf",
        "size": 2048576,
        "content_type": "application/pdf",
        "url": "https://cdn.discordapp.com/attachments/channel_id/message_id/document.pdf",
        "proxy_url": "https://media.discordapp.net/attachments/channel_id/message_id/document.pdf",
        "width": null,
        "height": null
    }
]
```

For images, additional metadata may be included:

```json
[
    {
        "filename": "image.png",
        "size": 512000,
        "content_type": "image/png",
        "url": "https://cdn.discordapp.com/attachments/channel_id/message_id/image.png",
        "proxy_url": "https://media.discordapp.net/attachments/channel_id/message_id/image.png",
        "width": 800,
        "height": 600
    }
]
```

## Data Retention

- Messages are kept indefinitely by default
- Soft deletion preserves message content for audit purposes
- When tickets are deleted, all associated messages are cascade deleted
- Consider implementing data retention policies for compliance

## Performance Considerations

- Use composite indexes for efficient querying
- Filter by `is_deleted = false` to exclude deleted messages
- Use pagination for large message lists
- Consider archiving old messages to separate tables

## Security

- Staff-only messages should only be visible to users with staff permissions
- Message content should be validated for length and content
- Attachment URLs should be proxied through secure endpoints
- Consider implementing message encryption for sensitive data
