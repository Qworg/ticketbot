# Discord Ticket Bot API Documentation

## Overview

The Discord Ticket Bot API is a comprehensive REST API that provides ticket management functionality for Discord-based support systems. It integrates Discord channels with a web dashboard, offering real-time synchronization, transcript management, and role-based access control.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [WebSocket API](#websocket-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)
- [SDKs and Integration](#sdks-and-integration)

## Getting Started

### Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.ticketbot.example.com`

### API Documentation

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

### Quick Start

1. **Get an API key** (for external systems) or **JWT token** (for staff access)
2. **Include authentication** in the `Authorization` header
3. **Make requests** to the API endpoints
4. **Handle responses** and errors appropriately

## Authentication

The API supports two authentication methods:

### 1. JWT Bearer Tokens (Staff Access)

Used by staff members accessing the web dashboard.

```bash
# Login to get JWT token
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "discord_id": 123456789,
       "username": "staff_member"
     }'

# Use token in subsequent requests
curl -X GET "http://localhost:8000/api/tickets" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 2. API Keys (External Systems)

Used by external systems for programmatic access.

```bash
# Create API key (admin only)
curl -X POST "http://localhost:8000/api/auth/api-keys" \
     -H "Authorization: Bearer <admin_jwt_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "External CRM Integration",
       "permissions": {
         "create_tickets": true,
         "read_tickets": true,
         "update_tickets": true
       }
     }'

# Use API key
curl -X GET "http://localhost:8000/api/tickets" \
     -H "Authorization: Bearer tb_1234567890abcdef..."
```

## API Endpoints

### Tickets

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tickets` | Create a new ticket |
| `GET` | `/api/tickets` | List tickets with filtering |
| `GET` | `/api/tickets/{id}` | Get ticket details |
| `PUT` | `/api/tickets/{id}` | Update ticket |
| `DELETE` | `/api/tickets/{id}` | Close ticket |
| `POST` | `/api/tickets/{id}/messages` | Add message to ticket |

### Transcripts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tickets/{id}/transcript` | Get ticket transcript |
| `POST` | `/api/tickets/{id}/transcript/share` | Generate share token |
| `DELETE` | `/api/tickets/{id}/transcript/share` | Revoke share token |
| `GET` | `/api/transcripts/shared/{token}` | Get shared transcript |
| `GET` | `/api/search/transcripts` | Search transcripts |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Staff login |
| `GET` | `/api/auth/me` | Get current user info |
| `POST` | `/api/auth/api-keys` | Create API key |
| `GET` | `/api/auth/api-keys` | List API keys |
| `DELETE` | `/api/auth/api-keys/{id}` | Revoke API key |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |

## WebSocket API

### Connection

Connect to the WebSocket endpoint for real-time updates:

```javascript
const token = 'your_jwt_token_here';
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

### Message Types

The WebSocket sends messages in the following format:

```json
{
    "type": "ticket_update|message_new|transcript_update|system_notification",
    "data": { ... },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Ticket Update
```json
{
    "type": "ticket_update",
    "data": {
        "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
        "status": "in_progress",
        "assigned_staff_id": 987654321,
        "updated_by": 987654321
    },
    "timestamp": "2024-01-01T12:30:00Z"
}
```

#### New Message
```json
{
    "type": "message_new",
    "data": {
        "message_id": "456e7890-e89b-12d3-a456-426614174001",
        "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
        "content": "New message content",
        "author_discord_id": 123456789,
        "message_type": "user_message"
    },
    "timestamp": "2024-01-01T12:35:00Z"
}
```

## Error Handling

The API returns structured error responses with appropriate HTTP status codes:

### Common Error Codes

| Code | Description | Example |
|------|-------------|---------|
| `400` | Bad Request | Invalid request data |
| `401` | Unauthorized | Invalid or missing authentication |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `409` | Conflict | Resource already exists |
| `422` | Validation Error | Request data validation failed |
| `429` | Rate Limited | Too many requests |
| `500` | Internal Error | Server error |

### Error Response Format

```json
{
    "detail": "Error description"
}
```

### Validation Errors

```json
{
    "detail": [
        {
            "loc": ["body", "title"],
            "msg": "ensure this value has at least 3 characters",
            "type": "value_error.any_str.min_length",
            "ctx": {"limit_value": 3}
        }
    ]
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Default**: 100 requests per minute per IP/API key
- **Burst**: Up to 10 requests per second
- **WebSocket**: 1 connection per authenticated user

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Examples

### Create a Ticket

```bash
curl -X POST "http://localhost:8000/api/tickets" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Cannot access user dashboard",
       "description": "User reports blank page after login",
       "priority": "high",
       "creator_discord_id": 123456789,
       "discord_channel_id": 987654321
     }'
```

### Search Tickets

```bash
curl -X GET "http://localhost:8000/api/tickets?search=login%20issue&status=open&priority=high&page=1&size=20" \
     -H "Authorization: Bearer <token>"
```

### Update Ticket Status

```bash
curl -X PUT "http://localhost:8000/api/tickets/123e4567-e89b-12d3-a456-426614174000" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "status": "in_progress",
       "assigned_staff_id": 987654321
     }'
```

### Search Transcripts

```bash
curl -X GET "http://localhost:8000/api/search/transcripts?search=dashboard%20blank&page=1&size=10" \
     -H "Authorization: Bearer <token>"
```

## SDKs and Integration

### Python Client

```python
import requests

class TicketBotClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_ticket(self, title: str, description: str, 
                     creator_discord_id: int, discord_channel_id: int,
                     priority: str = 'medium'):
        data = {
            'title': title,
            'description': description,
            'creator_discord_id': creator_discord_id,
            'discord_channel_id': discord_channel_id,
            'priority': priority
        }
        
        response = requests.post(
            f'{self.base_url}/api/tickets',
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

# Usage
client = TicketBotClient('http://localhost:8000', 'your_api_key_here')
ticket = client.create_ticket(
    title='API Integration Test',
    description='Testing the API integration',
    creator_discord_id=123456789,
    discord_channel_id=987654321,
    priority='high'
)
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

class TicketBotClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async createTicket(ticketData) {
        const response = await axios.post(
            `${this.baseUrl}/api/tickets`,
            ticketData,
            { headers: this.headers }
        );
        return response.data;
    }
    
    async getTickets(filters = {}) {
        const response = await axios.get(
            `${this.baseUrl}/api/tickets`,
            { 
                headers: this.headers,
                params: filters
            }
        );
        return response.data;
    }
}

// Usage
const client = new TicketBotClient('http://localhost:8000', 'your_api_key_here');
const ticket = await client.createTicket({
    title: 'Node.js Integration Test',
    description: 'Testing the API integration',
    creator_discord_id: 123456789,
    discord_channel_id: 987654321,
    priority: 'medium'
});
```

## Best Practices

### 1. Authentication
- Store API keys securely (environment variables, secret managers)
- Implement token refresh for JWT tokens
- Use HTTPS in production

### 2. Error Handling
- Always check response status codes
- Implement retry logic for transient errors
- Log errors for debugging

### 3. Rate Limiting
- Implement exponential backoff for rate-limited requests
- Cache responses when appropriate
- Use WebSocket for real-time updates instead of polling

### 4. Performance
- Use pagination for large result sets
- Implement client-side caching
- Filter requests to reduce payload size

### 5. Security
- Validate all input data
- Use least-privilege principle for API keys
- Monitor for unusual API usage patterns

## Support

For API support and questions:

- **Documentation**: Visit `/docs` for interactive API documentation
- **GitHub**: [Repository Issues](https://github.com/your-org/discord-ticket-bot/issues)
- **Email**: support@example.com

## Changelog

### v1.0.0 (2024-01-01)
- Initial API release
- Ticket management endpoints
- Transcript functionality
- WebSocket real-time updates
- Authentication and authorization
- Comprehensive OpenAPI documentation