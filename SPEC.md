# Discord Ticket Bot Implementation Plan

## 1. Project Overview

The Discord Ticket Bot is a comprehensive support ticket management system that seamlessly integrates Discord channels with a web-based dashboard. The system enables organizations to provide customer support through Discord while giving staff members the flexibility to manage tickets through either Discord commands or a React-based web interface.

### Key Features:
- Automated ticket channel creation and management
- Real-time synchronization between Discord and web dashboard
- Comprehensive ticket lifecycle management (create, modify, close)
- User permission management
- Transcript generation and public sharing
- Staff performance tracking and statistics
- Customizable ticket statuses and categories

### Technology Stack:
- **Discord Bot**: Python with interactions.py library
- **Backend API**: FastAPI or Flask with WebSocket support
- **Database**: PostgreSQL with Redis for caching
- **Web Dashboard**: React with Material-UI or Ant Design
- **Real-time Communication**: Socket.IO or native WebSockets
- **Hosting**: Docker containers on AWS/DigitalOcean

## 2. System Architecture

### Component Overview:
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Discord Bot   │────▶│   Backend API    │◀────│  Web Dashboard  │
│   (Python)      │     │   (FastAPI)      │     │    (React)      │
└────────┬────────┘     └────────┬─────────┘     └─────────────────┘
         │                       │
         │              ┌────────▼─────────┐
         └─────────────▶│   PostgreSQL     │
                        │   Database       │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │      Redis       │
                        │   Cache Layer    │
                        └──────────────────┘
```

### Architecture Details:
- **Discord Bot**: Handles all Discord interactions and commands
- **Backend API**: Central hub for data processing and business logic
- **Database Layer**: PostgreSQL for persistent storage, Redis for caching and real-time data
- **WebSocket Server**: Enables real-time communication between components
- **Message Queue**: RabbitMQ or Redis Pub/Sub for event distribution

### Communication Flow:
1. Discord events → Bot → API → Database
2. Dashboard actions → API → Bot → Discord
3. Real-time updates via WebSocket connections

## 3. Database Design

### Tables Structure:

#### guilds
```sql
CREATE TABLE guilds (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### tickets
```sql
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(id),
    channel_id BIGINT UNIQUE,
    creator_id BIGINT NOT NULL,
    assigned_to BIGINT,
    status VARCHAR(50) DEFAULT 'open',
    category VARCHAR(100),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    close_reason TEXT,
    is_shadow_closed BOOLEAN DEFAULT FALSE
);
```

#### ticket_participants
```sql
CREATE TABLE ticket_participants (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    role VARCHAR(50) DEFAULT 'participant',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP,
    UNIQUE(ticket_id, user_id)
);
```

#### messages
```sql
CREATE TABLE messages (
    id BIGINT PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL,
    content TEXT,
    attachments JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edited_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);
```

#### staff_stats
```sql
CREATE TABLE staff_stats (
    user_id BIGINT PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(id),
    tickets_handled INTEGER DEFAULT 0,
    tickets_closed INTEGER DEFAULT 0,
    average_response_time INTEGER,
    last_active TIMESTAMP,
    monthly_stats JSONB DEFAULT '{}'
);
```

#### transcripts
```sql
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id INTEGER REFERENCES tickets(id),
    content TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    access_count INTEGER DEFAULT 0
);
```

### Indexes:
```sql
CREATE INDEX idx_tickets_guild_status ON tickets(guild_id, status);
CREATE INDEX idx_tickets_assigned ON tickets(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_messages_ticket ON messages(ticket_id, created_at);
CREATE INDEX idx_participants_user ON ticket_participants(user_id) WHERE removed_at IS NULL;
```

## 4. API Design

### RESTful Endpoints:

#### Authentication
```
POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/auth/logout
GET    /api/auth/discord/callback
```

#### Tickets
```
GET    /api/tickets                    # List all tickets with pagination
POST   /api/tickets                    # Create new ticket
GET    /api/tickets/{ticket_id}        # Get ticket details
PUT    /api/tickets/{ticket_id}        # Update ticket
DELETE /api/tickets/{ticket_id}        # Close ticket
POST   /api/tickets/{ticket_id}/claim  # Claim ticket
POST   /api/tickets/{ticket_id}/unclaim # Unclaim ticket
```

#### Ticket Participants
```
GET    /api/tickets/{ticket_id}/participants
POST   /api/tickets/{ticket_id}/participants
DELETE /api/tickets/{ticket_id}/participants/{user_id}
```

#### Messages
```
GET    /api/tickets/{ticket_id}/messages
POST   /api/tickets/{ticket_id}/messages
PUT    /api/messages/{message_id}
DELETE /api/messages/{message_id}
```

#### Transcripts
```
POST   /api/tickets/{ticket_id}/transcript
GET    /api/transcript/{transcript_id}
```

#### Statistics
```
GET    /api/stats/staff
GET    /api/stats/staff/{user_id}
GET    /api/stats/tickets
```

### WebSocket Events:

#### Client → Server
```javascript
{
    "event": "join_ticket",
    "data": { "ticket_id": 123 }
}

{
    "event": "send_message",
    "data": { 
        "ticket_id": 123,
        "content": "Message content",
        "attachments": []
    }
}
```

#### Server → Client
```javascript
{
    "event": "ticket_updated",
    "data": { /* ticket object */ }
}

{
    "event": "message_received",
    "data": { /* message object */ }
}

{
    "event": "participant_added",
    "data": { "ticket_id": 123, "user": { /* user object */ } }
}
```

## 5. Discord Bot Functionality

### Command Implementation:

#### `/ticket [reason]`
```python
@slash_command(name="ticket", description="Create a support ticket")
@slash_option(
    name="reason",
    description="Reason for creating the ticket",
    opt_type=OptionType.STRING,
    required=True
)
async def create_ticket(ctx: SlashContext, reason: str):
    # Check if user already has an open ticket
    existing_ticket = await db.get_user_open_ticket(ctx.author.id, ctx.guild.id)
    if existing_ticket:
        return await ctx.send("You already have an open ticket!", ephemeral=True)
    
    # Create ticket category if not exists
    category = await get_or_create_ticket_category(ctx.guild)
    
    # Create ticket channel
    overwrites = {
        ctx.guild.default_role: PermissionOverwrite(read_messages=False),
        ctx.author: PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.guild.me: PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    # Add staff role permissions
    staff_role = await get_staff_role(ctx.guild)
    if staff_role:
        overwrites[staff_role] = PermissionOverwrite(read_messages=True, send_messages=True)
    
    channel = await ctx.guild.create_text_channel(
        name=f"ticket-{ctx.author.name}",
        category=category,
        overwrites=overwrites
    )
    
    # Save to database
    ticket = await db.create_ticket(
        guild_id=ctx.guild.id,
        channel_id=channel.id,
        creator_id=ctx.author.id,
        reason=reason
    )
    
    # Send initial message
    embed = Embed(
        title="Support Ticket Created",
        description=f"**Reason:** {reason}\n**Created by:** {ctx.author.mention}",
        color=0x00ff00
    )
    await channel.send(embed=embed)
    
    # Notify via WebSocket
    await ws.emit_ticket_created(ticket)
    
    await ctx.send(f"Ticket created: {channel.mention}", ephemeral=True)
```

#### `/rename [new_name]`
```python
@slash_command(name="rename", description="Rename the current ticket channel")
@slash_option(
    name="new_name",
    description="New name for the ticket",
    opt_type=OptionType.STRING,
    required=True
)
@ticket_channel_only()
@staff_only()
async def rename_ticket(ctx: SlashContext, new_name: str):
    ticket = await db.get_ticket_by_channel(ctx.channel.id)
    
    # Sanitize channel name
    channel_name = f"ticket-{new_name.lower().replace(' ', '-')}"
    await ctx.channel.edit(name=channel_name)
    
    # Log the action
    await db.log_ticket_action(ticket.id, ctx.author.id, "rename", {"new_name": new_name})
    
    embed = Embed(
        title="Ticket Renamed",
        description=f"Ticket renamed to: **{new_name}**",
        color=0x00ff00
    )
    await ctx.send(embed=embed)
```

#### `/close [reason]`
```python
@slash_command(name="close", description="Close the current ticket")
@slash_option(
    name="reason",
    description="Reason for closing",
    opt_type=OptionType.STRING,
    required=False
)
@ticket_channel_only()
async def close_ticket(ctx: SlashContext, reason: str = None):
    ticket = await db.get_ticket_by_channel(ctx.channel.id)
    
    # Check permissions
    if ctx.author.id != ticket.creator_id and not await is_staff(ctx.author, ctx.guild):
        return await ctx.send("You don't have permission to close this ticket!", ephemeral=True)
    
    # Create confirmation embed
    embed = Embed(
        title="Confirm Ticket Closure",
        description="Are you sure you want to close this ticket?",
        color=0xffff00
    )
    if reason:
        embed.add_field(name="Reason", value=reason)
    
    # Add confirmation buttons
    components = [
        Button(
            style=ButtonStyle.DANGER,
            label="Close Ticket",
            custom_id=f"close_confirm_{ticket.id}"
        ),
        Button(
            style=ButtonStyle.SECONDARY,
            label="Cancel",
            custom_id=f"close_cancel_{ticket.id}"
        )
    ]
    
    await ctx.send(embed=embed, components=components)
```

#### `/transcript`
```python
@slash_command(name="transcript", description="Generate a transcript for this ticket")
@ticket_channel_only()
async def generate_transcript(ctx: SlashContext):
    ticket = await db.get_ticket_by_channel(ctx.channel.id)
    
    # Check if transcript already exists
    existing = await db.get_ticket_transcript(ticket.id)
    if existing and existing.expires_at > datetime.utcnow():
        return await ctx.send(f"Transcript: {config.BASE_URL}/transcript/{existing.id}")
    
    # Generate transcript
    messages = await db.get_ticket_messages(ticket.id)
    transcript_content = await format_transcript(ticket, messages)
    
    # Save transcript
    transcript = await db.create_transcript(
        ticket_id=ticket.id,
        content=transcript_content,
        expires_in_days=30
    )
    
    embed = Embed(
        title="Transcript Generated",
        description=f"[View Transcript]({config.BASE_URL}/transcript/{transcript.id})",
        color=0x00ff00
    )
    embed.set_footer(text="This transcript will expire in 30 days")
    
    await ctx.send(embed=embed)
```

### Event Handlers:

```python
@listen()
async def on_message_create(event: MessageCreate):
    # Check if message is in a ticket channel
    ticket = await db.get_ticket_by_channel(event.message.channel_id)
    if not ticket:
        return
    
    # Save message to database
    await db.save_message(
        message_id=event.message.id,
        ticket_id=ticket.id,
        author_id=event.message.author.id,
        content=event.message.content,
        attachments=[att.to_dict() for att in event.message.attachments]
    )
    
    # Emit to WebSocket
    await ws.emit_message_created(ticket.id, event.message)
    
    # Update staff activity
    if await is_staff(event.message.author, event.message.guild):
        await db.update_staff_activity(event.message.author.id, event.message.guild.id)
```

## 6. Web Dashboard Integration

### React Component Structure:
```
src/
├── components/
│   ├── Layout/
│   │   ├── Header.jsx
│   │   ├── Sidebar.jsx
│   │   └── Footer.jsx
│   ├── Tickets/
│   │   ├── TicketList.jsx
│   │   ├── TicketDetails.jsx
│   │   ├── TicketChat.jsx
│   │   └── TicketActions.jsx
│   ├── Stats/
│   │   ├── StaffStats.jsx
│   │   └── TicketStats.jsx
│   └── Common/
│       ├── LoadingSpinner.jsx
│       └── ErrorBoundary.jsx
├── hooks/
│   ├── useWebSocket.js
│   ├── useTickets.js
│   └── useAuth.js
├── services/
│   ├── api.js
│   ├── websocket.js
│   └── auth.js
└── utils/
    ├── constants.js
    └── helpers.js
```

### Real-time Chat Component:
```jsx
const TicketChat = ({ ticketId }) => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const { socket, connected } = useWebSocket();
    
    useEffect(() => {
        // Join ticket room
        socket.emit('join_ticket', { ticket_id: ticketId });
        
        // Listen for new messages
        socket.on('message_received', (message) => {
            setMessages(prev => [...prev, message]);
        });
        
        // Fetch existing messages
        fetchMessages();
        
        return () => {
            socket.emit('leave_ticket', { ticket_id: ticketId });
            socket.off('message_received');
        };
    }, [ticketId]);
    
    const sendMessage = async () => {
        if (!inputValue.trim()) return;
        
        await api.post(`/tickets/${ticketId}/messages`, {
            content: inputValue
        });
        
        setInputValue('');
    };
    
    return (
        <div className="ticket-chat">
            <MessageList messages={messages} />
            <MessageInput 
                value={inputValue}
                onChange={setInputValue}
                onSend={sendMessage}
                disabled={!connected}
            />
        </div>
    );
};
```

### State Management (Redux Toolkit):
```javascript
const ticketSlice = createSlice({
    name: 'tickets',
    initialState: {
        list: [],
        current: null,
        loading: false,
        error: null
    },
    reducers: {
        ticketUpdated: (state, action) => {
            const index = state.list.findIndex(t => t.id === action.payload.id);
            if (index !== -1) {
                state.list[index] = action.payload;
            }
            if (state.current?.id === action.payload.id) {
                state.current = action.payload;
            }
        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchTickets.fulfilled, (state, action) => {
                state.list = action.payload;
                state.loading = false;
            })
            .addCase(fetchTickets.pending, (state) => {
                state.loading = true;
            });
    }
});
```

## 7. Security Considerations

### Authentication & Authorization:
1. **Discord OAuth2**: Use Discord OAuth2 for dashboard authentication
2. **JWT Tokens**: Implement JWT with refresh tokens for session management
3. **Role-Based Access Control (RBAC)**: Define clear permission levels:
   - Admin: Full system access
   - Staff: Ticket management access
   - User: Own ticket access only

### API Security:
```python
# Rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.get("/api/tickets")
@limiter.limit("100/minute")
async def get_tickets(request: Request):
    pass

# Input validation
from pydantic import BaseModel, validator

class TicketCreate(BaseModel):
    reason: str
    
    @validator('reason')
    def validate_reason(cls, v):
        if len(v) < 5 or len(v) > 500:
            raise ValueError('Reason must be between 5 and 500 characters')
        return v

# SQL injection prevention (using ORM)
ticket = await Ticket.filter(
    guild_id=guild_id,
    status="open"
).order_by("-created_at").limit(10)
```

### Data Protection:
1. **Encryption**: Encrypt sensitive data at rest using AES-256
2. **HTTPS**: Enforce HTTPS for all API communications
3. **Environment Variables**: Store secrets in environment variables
4. **Data Retention**: Implement automatic data purging policies

### Discord Bot Security:
```python
# Command permission checks
def staff_only():
    async def predicate(ctx: SlashContext):
        staff_role = await get_staff_role(ctx.guild)
        if not staff_role or staff_role not in ctx.author.roles:
            await ctx.send("You don't have permission to use this command!", ephemeral=True)
            return False
        return True
    return check(predicate)

# Prevent command spam
command_cooldowns = {}

async def check_cooldown(user_id: int, command: str, seconds: int = 5):
    key = f"{user_id}:{command}"
    if key in command_cooldowns:
        if time.time() - command_cooldowns[key] < seconds:
            return False
    command_cooldowns[key] = time.time()
    return True
```

## 8. Testing Strategy

### Unit Testing:
```python
# Test ticket creation
async def test_create_ticket():
    ticket = await create_ticket(
        guild_id=123456,
        channel_id=789012,
        creator_id=345678,
        reason="Test ticket"
    )
    assert ticket.id is not None
    assert ticket.status == "open"
    assert ticket.reason == "Test ticket"

# Test permission checking
async def test_staff_permission():
    mock_ctx = MockContext(user_roles=["Member"])
    result = await check_staff_permission(mock_ctx)
    assert result is False
    
    mock_ctx.user_roles.append("Staff")
    result = await check_staff_permission(mock_ctx)
    assert result is True
```

### Integration Testing:
1. **API Testing**: Use pytest with httpx for async API testing
2. **Discord Bot Testing**: Mock Discord API responses
3. **WebSocket Testing**: Test real-time message flow
4. **Database Testing**: Use test database with fixtures

### End-to-End Testing:
```javascript
// Cypress test for ticket creation flow
describe('Ticket Management', () => {
    it('should create and close a ticket', () => {
        cy.login();
        cy.visit('/dashboard');
        
        // Create ticket
        cy.get('[data-test="create-ticket"]').click();
        cy.get('[data-test="reason-input"]').type('Test ticket');
        cy.get('[data-test="submit-ticket"]').click();
        
        // Verify ticket created
        cy.contains('Test ticket').should('exist');
        
        // Close ticket
        cy.get('[data-test="close-ticket"]').click();
        cy.get('[data-test="confirm-close"]').click();
        
        // Verify ticket closed
        cy.contains('Status: Closed').should('exist');
    });
});
```

## 9. Deployment Plan

### Docker Configuration:
```dockerfile
# Bot Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]

# API Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Dashboard Dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

### Docker Compose:
```yaml
version: '3.8'
services:
  bot:
    build: ./bot
    env_file: .env
    depends_on:
      - postgres
      - redis
      - api
    restart: unless-stopped

  api:
    build: ./api
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  dashboard:
    build: ./dashboard
    ports:
      - "3000:80"
    depends_on:
      - api
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ticketbot
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### CI/CD Pipeline (GitHub Actions):
```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit
          
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/ticketbot
            git pull
            docker-compose down
            docker-compose up -d --build
```

## 10. Maintenance and Scalability

### Monitoring:
1. **Application Monitoring**: 
   - Sentry for error tracking
   - Prometheus + Grafana for metrics
   - Custom Discord webhook for critical alerts

2. **Database Monitoring**:
   - pg_stat_statements for query performance
   - Automated backup verification
   - Connection pool monitoring

3. **Bot Health Checks**:
```python
@tasks.loop(minutes=5)
async def health_check():
    try:
        # Check Discord connection
        if not bot.is_ready():
            await alert_admins("Bot disconnected from Discord")
            
        # Check database connection
        await db.execute("SELECT 1")
        
        # Check Redis connection
        await redis.ping()
        
        # Update health status
        await redis.set("bot:health", "healthy", ex=360)
    except Exception as e:
        await alert_admins(f"Health check failed: {e}")
```

### Scaling Strategies:

1. **Horizontal Scaling**:
   - Use Discord bot sharding for multiple servers
   - Load balance API across multiple instances
   - Implement Redis Cluster for caching

2. **Database Optimization**:
   ```sql
   -- Partition tickets table by month
   CREATE TABLE tickets_2024_01 PARTITION OF tickets
   FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
   
   -- Archive old tickets
   INSERT INTO tickets_archive 
   SELECT * FROM tickets 
   WHERE closed_at < NOW() - INTERVAL '6 months';
   ```

3. **Performance Optimization**:
   - Implement message queuing for heavy operations
   - Use database connection pooling
   - Cache frequently accessed data
   - Optimize Discord API calls with bulk operations