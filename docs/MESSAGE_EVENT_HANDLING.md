# Discord Message Event Handling Flow

## Overview

The Discord message event handling system automatically captures, processes, and stores all messages sent in ticket channels. This document describes the complete flow from Discord message events to database storage.

## Architecture

### Components

1. **Event Listeners** (`app/bot.py`):
   - `on_message_create`: Handles new message creation
   - `on_message_update`: Handles message edits
   - `on_message_delete`: Handles message deletions

2. **Message Service** (`app/services/message_service.py`):
   - Database operations for message CRUD
   - Staff role checking
   - Attachment metadata extraction

3. **Database Models** (`app/models/message.py`):
   - Message data model with metadata
   - Relationship to tickets

## Event Flow

### Message Creation Flow

```
Discord Message → Bot Event Listener → Validation → Database Save
```

1. **Event Reception**: Bot receives `MessageCreate` event from Discord
2. **Initial Filtering**:
   - Skip bot messages
   - Check rate limiting (100 messages/minute per channel)
3. **Channel Validation**:
   - Query database to verify channel is a ticket channel
   - Exit early if not a ticket channel
4. **Data Extraction**:
   - Extract message content, author, timestamp
   - Process attachments and store metadata
   - Determine staff status based on user roles
5. **Database Operation**:
   - Save message to database with all metadata
   - Handle database errors gracefully
   - Log operation for audit purposes

### Message Update Flow

```
Discord Edit → Bot Event Listener → Validation → Database Update
```

1. **Event Reception**: Bot receives `MessageUpdate` event
2. **Validation**: Same filtering as creation
3. **Database Update**:
   - Update message content
   - Set edited timestamp
   - Preserve original creation data

### Message Deletion Flow

```
Discord Delete → Bot Event Listener → Validation → Soft Delete
```

1. **Event Reception**: Bot receives `MessageDelete` event
2. **Validation**: Same filtering as creation
3. **Soft Delete**:
   - Mark message as deleted (`is_deleted = true`)
   - Preserve original content for audit
   - Log deletion event

## Rate Limiting

### Purpose
- Prevent database spam from rapid message events
- Protect against malicious users or bots
- Maintain system performance

### Implementation
- **Limit**: 100 messages per minute per channel
- **Tracking**: In-memory dictionary with timestamps
- **Cleanup**: Automatic removal of old entries
- **Behavior**: Skip processing when limit exceeded

```python
def _check_message_rate_limit(self, channel_id: int) -> bool:
    current_time = time.time()
    channel_uses = self._message_rate_limits.setdefault(channel_id, [])
    
    # Remove uses older than 1 minute
    channel_uses[:] = [use_time for use_time in channel_uses 
                      if current_time - use_time < 60]
    
    if len(channel_uses) >= self._message_rate_limit_per_minute:
        return False
    
    # Add current use
    channel_uses.append(current_time)
    return True
```

## Message Types Handled

### Text Messages
- Plain text content
- Markdown formatting preserved
- Emoji and mentions captured

### Embeds
- Embedded content from URLs
- Bot-generated embeds
- Rich media previews

### File Attachments
- Metadata extraction (filename, size, content type)
- URL preservation for access
- Thumbnail information for images
- Security validation

### Staff-Only Messages
- Automatic detection based on user roles
- Flagged in database for filtering
- Used for private staff communication

## Database Schema

### Message Table Structure
```sql
CREATE TABLE messages (
    id BIGINT PRIMARY KEY,           -- Discord message ID
    ticket_id INTEGER NOT NULL,      -- FK to tickets table
    author_id BIGINT NOT NULL,       -- Discord user ID
    content TEXT,                    -- Message content
    attachments JSONB,               -- Attachment metadata
    is_staff_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    edited_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);
```

### Indexes
- `(ticket_id, created_at)`: Message ordering
- `author_id`: User message queries
- `is_staff_only`: Staff message filtering

## Error Handling

### Database Errors
- Automatic rollback on database failures
- Graceful error logging
- Continue processing other messages

### Discord API Errors
- Handle missing message data
- Cope with permission changes
- Retry logic for temporary failures

### Rate Limiting
- Skip processing when exceeded
- Log warnings for monitoring
- Automatic recovery after time window

## Security Considerations

### Data Validation
- Sanitize message content
- Validate attachment metadata
- Prevent SQL injection

### Access Control
- Staff-only message flagging
- Role-based visibility
- Audit trail preservation

### Performance
- Efficient database operations
- Minimal memory usage
- Background processing

## Monitoring and Logging

### Event Logging
```python
logger.info(f"Saved message {message.id} from user {author_id} in ticket {ticket.id}")
logger.warning(f"Rate limit exceeded for channel {channel_id}")
logger.error(f"Database error saving message {message_id}: {e}")
```

### Audit Trail
- Message creation events
- Edit history tracking
- Deletion records
- Staff activity monitoring

## Testing

### Unit Tests
- Message filtering logic
- Data extraction accuracy
- Rate limiting functionality
- Error handling scenarios

### Integration Tests
- Database operations
- Event handler workflow
- Error recovery
- Performance under load

## Configuration

### Environment Variables
```bash
# Rate limiting
MESSAGE_RATE_LIMIT_PER_MINUTE=100

# Database connection
DATABASE_URL=postgresql://...

# Discord bot settings
DISCORD_TOKEN=...
```

### Guild Settings
- Staff role configuration
- Admin role configuration
- Ticket category settings

## Troubleshooting

### Common Issues

1. **Messages Not Saving**
   - Check database connection
   - Verify ticket channel exists
   - Check rate limiting logs

2. **Rate Limit Exceeded**
   - Review channel activity
   - Adjust rate limit settings
   - Check for bot spam

3. **Staff Detection Issues**
   - Verify guild role configuration
   - Check user role assignments
   - Review staff role IDs

4. **Database Performance**
   - Monitor query execution times
   - Check index usage
   - Review connection pooling

### Debug Commands
```bash
# Check database connectivity
python -c "from app.database import get_db_session; print(get_db_session())"

# Test message service
python -c "from app.services.message_service import get_ticket_by_channel; print('Service available')"

# Check bot event registration
python -c "from app.bot import get_bot; bot = get_bot(); print(f'Bot ready: {bot.is_ready()}')"
```

## Future Enhancements

### Planned Features
- Message threading support
- Reaction tracking
- Voice message transcription
- Advanced search capabilities

### Performance Improvements
- Message batching
- Async database operations
- Caching layer
- Load balancing

### Security Enhancements
- Message encryption
- Content filtering
- Spam detection
- Malware scanning
