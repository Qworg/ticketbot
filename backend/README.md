# Discord Ticket Bot Backend

FastAPI backend service for the Discord Ticket Bot system, providing REST API endpoints for ticket management, real-time synchronization, and transcript handling.

## Features

- **REST API**: Comprehensive ticket management endpoints
- **Real-time Updates**: WebSocket support for live synchronization
- **Authentication**: JWT tokens for staff and API keys for external systems
- **Transcript Management**: Generate, search, and share ticket transcripts
- **Database Integration**: PostgreSQL with Alembic migrations
- **Caching**: Redis for performance and pub/sub messaging
- **Documentation**: Complete OpenAPI/Swagger documentation

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL
- Redis
- uv (Python package manager)

### Installation

1. **Install dependencies**:
   ```bash
   cd backend
   uv venv
   uv pip install -e .
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run database migrations**:
   ```bash
   uv run alembic upgrade head
   ```

4. **Start the server**:
   ```bash
   uv run python main.py
   ```

The API will be available at `http://localhost:8000`

## API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Documentation Files

- **[Complete API Guide](docs/API_DOCUMENTATION.md)**: Comprehensive API documentation
- **[Postman Collection](docs/Discord_Ticket_Bot_API.postman_collection.json)**: Ready-to-use API testing collection
- **[Code Examples](docs/api_examples.py)**: Integration examples for various languages

### Quick API Test

Run the included test script to verify API functionality:

```bash
uv run python test_api.py
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Staff login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/api-keys` - Create API key
- `GET /api/auth/api-keys` - List API keys

### Tickets
- `POST /api/tickets` - Create ticket
- `GET /api/tickets` - List/search tickets
- `GET /api/tickets/{id}` - Get ticket details
- `PUT /api/tickets/{id}` - Update ticket
- `DELETE /api/tickets/{id}` - Close ticket
- `POST /api/tickets/{id}/messages` - Add message

### Transcripts
- `GET /api/tickets/{id}/transcript` - Get transcript
- `POST /api/tickets/{id}/transcript/share` - Generate share token
- `GET /api/search/transcripts` - Search transcripts

### System
- `GET /` - API information
- `GET /health` - Health check
- `WS /ws` - WebSocket endpoint

## Authentication

### JWT Tokens (Staff Access)

```bash
# Login
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"discord_id": 123456789, "username": "staff_member"}'

# Use token
curl -X GET "http://localhost:8000/api/tickets" \
     -H "Authorization: Bearer <jwt_token>"
```

### API Keys (External Systems)

```bash
# Create API key (admin only)
curl -X POST "http://localhost:8000/api/auth/api-keys" \
     -H "Authorization: Bearer <admin_jwt_token>" \
     -d '{"name": "External System", "permissions": {"create_tickets": true}}'

# Use API key
curl -X GET "http://localhost:8000/api/tickets" \
     -H "Authorization: Bearer <api_key>"
```

## Development

### Running Tests

```bash
# Unit tests
uv run pytest

# Integration tests
uv run python run_integration_tests.py

# API tests
uv run python test_api.py
```

### Database Migrations

```bash
# Create migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1
```

### Code Quality

```bash
# Format code
uv run black .

# Lint code
uv run flake8 .

# Type checking
uv run mypy .
```

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/ticketbot

# Redis
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Discord
DISCORD_BOT_TOKEN=your-bot-token

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

## Docker

### Build

```bash
docker build -t ticketbot-backend .
```

### Run

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  ticketbot-backend
```

### Docker Compose

```bash
docker-compose up -d
```

## Monitoring

### Health Checks

The `/health` endpoint provides system status:

```json
{
  "status": "healthy",
  "service": "discord-ticket-bot-backend",
  "version": "1.0.0",
  "database": {"status": "connected"},
  "redis": {"status": "healthy"}
}
```

### Logging

Structured logging is configured with different levels:

- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Warning conditions
- **ERROR**: Error conditions
- **CRITICAL**: Critical errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

## License

MIT License - see LICENSE file for details