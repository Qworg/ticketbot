"""
API usage examples and documentation for Discord Ticket Bot.

This module contains comprehensive examples of how to use the Discord Ticket Bot API,
including authentication, ticket management, and real-time features.
"""

from typing import Dict, Any, List


class APIExamples:
    """Collection of API usage examples and documentation."""
    
    @staticmethod
    def get_authentication_examples() -> Dict[str, Any]:
        """Get authentication examples."""
        return {
            "staff_login": {
                "description": "Authenticate a staff member and get JWT token",
                "endpoint": "POST /api/auth/login",
                "request": {
                    "discord_id": 123456789,
                    "username": "staff_member"
                },
                "response": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600
                },
                "curl_example": """
                curl -X POST "http://localhost:8000/api/auth/login" \\
                     -H "Content-Type: application/json" \\
                     -d '{
                       "discord_id": 123456789,
                       "username": "staff_member"
                     }'
                """
            },
            "api_key_creation": {
                "description": "Create API key for external system (admin only)",
                "endpoint": "POST /api/auth/api-keys",
                "headers": {
                    "Authorization": "Bearer <jwt_token>"
                },
                "request": {
                    "name": "External CRM Integration",
                    "permissions": {
                        "create_tickets": True,
                        "read_tickets": True,
                        "update_tickets": True,
                        "read_transcripts": True
                    }
                },
                "response": {
                    "api_key": "tb_1234567890abcdef...",
                    "key_id": "key_123",
                    "name": "External CRM Integration",
                    "permissions": {
                        "create_tickets": True,
                        "read_tickets": True,
                        "update_tickets": True,
                        "read_transcripts": True
                    }
                }
            }
        }
    
    @staticmethod
    def get_ticket_examples() -> Dict[str, Any]:
        """Get ticket management examples."""
        return {
            "create_ticket": {
                "description": "Create a new support ticket",
                "endpoint": "POST /api/tickets",
                "headers": {
                    "Authorization": "Bearer <token>",
                    "Content-Type": "application/json"
                },
                "request": {
                    "title": "Cannot access user dashboard",
                    "description": "User reports that the dashboard shows a blank page after login",
                    "priority": "high",
                    "creator_discord_id": 123456789,
                    "discord_channel_id": 987654321
                },
                "response": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "Cannot access user dashboard",
                    "description": "User reports that the dashboard shows a blank page after login",
                    "discord_channel_id": 987654321,
                    "status": "open",
                    "priority": "high",
                    "creator_discord_id": 123456789,
                    "assigned_staff_id": None,
                    "created_at": "2024-01-01T12:00:00Z",
                    "updated_at": "2024-01-01T12:00:00Z",
                    "closed_at": None
                },
                "python_example": """
                import requests
                
                headers = {
                    'Authorization': 'Bearer your_jwt_token_here',
                    'Content-Type': 'application/json'
                }
                
                data = {
                    'title': 'Cannot access user dashboard',
                    'description': 'User reports that the dashboard shows a blank page after login',
                    'priority': 'high',
                    'creator_discord_id': 123456789,
                    'discord_channel_id': 987654321
                }
                
                response = requests.post(
                    'http://localhost:8000/api/tickets',
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 201:
                    ticket = response.json()
                    print(f"Created ticket: {ticket['id']}")
                """
            },
            "search_tickets": {
                "description": "Search and filter tickets with pagination",
                "endpoint": "GET /api/tickets",
                "parameters": {
                    "search": "login issue",
                    "status": "open",
                    "priority": "high",
                    "page": 1,
                    "size": 20
                },
                "response": {
                    "items": [
                        {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Login Issue - Cannot authenticate",
                            "status": "open",
                            "priority": "high",
                            "creator_discord_id": 123456789,
                            "created_at": "2024-01-01T12:00:00Z"
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "size": 20,
                    "pages": 1
                },
                "curl_example": """
                curl -X GET "http://localhost:8000/api/tickets?search=login%20issue&status=open&priority=high&page=1&size=20" \\
                     -H "Authorization: Bearer <token>"
                """
            },
            "update_ticket": {
                "description": "Update ticket status and assignment",
                "endpoint": "PUT /api/tickets/{ticket_id}",
                "request": {
                    "status": "in_progress",
                    "assigned_staff_id": 987654321,
                    "priority": "urgent"
                },
                "response": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "Cannot access user dashboard",
                    "status": "in_progress",
                    "priority": "urgent",
                    "assigned_staff_id": 987654321,
                    "updated_at": "2024-01-01T12:30:00Z"
                }
            },
            "add_message": {
                "description": "Add a message to an existing ticket",
                "endpoint": "POST /api/tickets/{ticket_id}/messages",
                "request": {
                    "content": "I've identified the issue and am working on a fix",
                    "author_discord_id": 987654321,
                    "message_type": "staff_message",
                    "discord_message_id": 1234567890
                },
                "response": {
                    "id": "456e7890-e89b-12d3-a456-426614174001",
                    "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
                    "content": "I've identified the issue and am working on a fix",
                    "author_discord_id": 987654321,
                    "message_type": "staff_message",
                    "discord_message_id": 1234567890,
                    "created_at": "2024-01-01T12:45:00Z"
                }
            }
        }
    
    @staticmethod
    def get_transcript_examples() -> Dict[str, Any]:
        """Get transcript management examples."""
        return {
            "get_transcript": {
                "description": "Get transcript for a specific ticket",
                "endpoint": "GET /api/tickets/{ticket_id}/transcript",
                "response": {
                    "id": "789e0123-e89b-12d3-a456-426614174002",
                    "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
                    "content": "Ticket: Cannot access user dashboard\\nID: 123e4567-e89b-12d3-a456-426614174000\\n...",
                    "formatted_content": {
                        "ticket": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "Cannot access user dashboard",
                            "status": "closed",
                            "created_at": "2024-01-01T12:00:00Z"
                        },
                        "messages": [
                            {
                                "id": "456e7890-e89b-12d3-a456-426614174001",
                                "author_discord_id": 123456789,
                                "content": "I can't access my dashboard after logging in",
                                "message_type": "user_message",
                                "created_at": "2024-01-01T12:05:00Z"
                            }
                        ]
                    },
                    "share_token": None,
                    "created_at": "2024-01-01T13:00:00Z",
                    "updated_at": "2024-01-01T13:00:00Z"
                }
            },
            "search_transcripts": {
                "description": "Search transcripts by content",
                "endpoint": "GET /api/search/transcripts",
                "parameters": {
                    "search": "dashboard blank page",
                    "created_after": "2024-01-01T00:00:00Z",
                    "search_mode": "fuzzy",
                    "page": 1,
                    "size": 10
                },
                "response": {
                    "items": [
                        {
                            "id": "789e0123-e89b-12d3-a456-426614174002",
                            "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
                            "content": "Ticket contains: dashboard shows a blank page...",
                            "created_at": "2024-01-01T13:00:00Z"
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "size": 10,
                    "pages": 1
                }
            },
            "share_transcript": {
                "description": "Generate a shareable link for a transcript",
                "endpoint": "POST /api/tickets/{ticket_id}/transcript/share",
                "response": {
                    "share_token": "st_1234567890abcdef..."
                },
                "usage": "Share URL: https://api.example.com/api/transcripts/shared/st_1234567890abcdef..."
            }
        }
    
    @staticmethod
    def get_websocket_examples() -> Dict[str, Any]:
        """Get WebSocket usage examples."""
        return {
            "connection": {
                "description": "Connect to WebSocket for real-time updates",
                "endpoint": "ws://localhost:8000/ws",
                "authentication": "Include JWT token as query parameter: ?token=<jwt_token>",
                "javascript_example": """
                const token = 'your_jwt_token_here';
                const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
                
                ws.onopen = function(event) {
                    console.log('Connected to WebSocket');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    console.log('Received:', data);
                    
                    switch(data.type) {
                        case 'ticket_update':
                            handleTicketUpdate(data.data);
                            break;
                        case 'message_new':
                            handleNewMessage(data.data);
                            break;
                        case 'transcript_update':
                            handleTranscriptUpdate(data.data);
                            break;
                    }
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
                """
            },
            "message_types": {
                "ticket_update": {
                    "type": "ticket_update",
                    "data": {
                        "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "in_progress",
                        "assigned_staff_id": 987654321,
                        "updated_by": 987654321
                    },
                    "timestamp": "2024-01-01T12:30:00Z"
                },
                "message_new": {
                    "type": "message_new",
                    "data": {
                        "message_id": "456e7890-e89b-12d3-a456-426614174001",
                        "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
                        "content": "New message content",
                        "author_discord_id": 123456789,
                        "message_type": "user_message"
                    },
                    "timestamp": "2024-01-01T12:35:00Z"
                },
                "transcript_update": {
                    "type": "transcript_update",
                    "data": {
                        "transcript_id": "789e0123-e89b-12d3-a456-426614174002",
                        "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
                        "updated": True
                    },
                    "timestamp": "2024-01-01T13:00:00Z"
                }
            }
        }
    
    @staticmethod
    def get_error_handling_examples() -> Dict[str, Any]:
        """Get error handling examples."""
        return {
            "authentication_error": {
                "status_code": 401,
                "response": {
                    "detail": "Invalid authentication credentials"
                },
                "description": "Returned when JWT token is invalid or expired"
            },
            "permission_error": {
                "status_code": 403,
                "response": {
                    "detail": "Insufficient permissions to perform this action"
                },
                "description": "Returned when user lacks required permissions"
            },
            "not_found_error": {
                "status_code": 404,
                "response": {
                    "detail": "Ticket with ID 123e4567-e89b-12d3-a456-426614174000 not found"
                },
                "description": "Returned when requested resource doesn't exist"
            },
            "validation_error": {
                "status_code": 422,
                "response": {
                    "detail": [
                        {
                            "loc": ["body", "title"],
                            "msg": "ensure this value has at least 3 characters",
                            "type": "value_error.any_str.min_length",
                            "ctx": {"limit_value": 3}
                        }
                    ]
                },
                "description": "Returned when request data fails validation"
            },
            "rate_limit_error": {
                "status_code": 429,
                "response": {
                    "detail": "Rate limit exceeded. Try again later."
                },
                "headers": {
                    "X-RateLimit-Limit": "100",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "1640995200"
                },
                "description": "Returned when API rate limits are exceeded"
            }
        }
    
    @staticmethod
    def get_integration_examples() -> Dict[str, Any]:
        """Get integration examples for external systems."""
        return {
            "python_client": """
            import requests
            import json
            from typing import Dict, Any, Optional
            
            class TicketBotClient:
                def __init__(self, base_url: str, api_key: str):
                    self.base_url = base_url.rstrip('/')
                    self.headers = {
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    }
                
                def create_ticket(self, title: str, description: str, 
                                creator_discord_id: int, discord_channel_id: int,
                                priority: str = 'medium') -> Dict[str, Any]:
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
                
                def get_tickets(self, search: Optional[str] = None,
                              status: Optional[str] = None,
                              page: int = 1, size: int = 10) -> Dict[str, Any]:
                    params = {'page': page, 'size': size}
                    if search:
                        params['search'] = search
                    if status:
                        params['status'] = status
                    
                    response = requests.get(
                        f'{self.base_url}/api/tickets',
                        headers=self.headers,
                        params=params
                    )
                    response.raise_for_status()
                    return response.json()
                
                def update_ticket(self, ticket_id: str, **updates) -> Dict[str, Any]:
                    response = requests.put(
                        f'{self.base_url}/api/tickets/{ticket_id}',
                        headers=self.headers,
                        json=updates
                    )
                    response.raise_for_status()
                    return response.json()
            
            # Usage example
            client = TicketBotClient('http://localhost:8000', 'your_api_key_here')
            
            # Create a ticket
            ticket = client.create_ticket(
                title='API Integration Test',
                description='Testing the API integration',
                creator_discord_id=123456789,
                discord_channel_id=987654321,
                priority='high'
            )
            
            print(f"Created ticket: {ticket['id']}")
            """,
            "nodejs_client": """
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
                    try {
                        const response = await axios.post(
                            `${this.baseUrl}/api/tickets`,
                            ticketData,
                            { headers: this.headers }
                        );
                        return response.data;
                    } catch (error) {
                        throw new Error(`Failed to create ticket: ${error.response?.data?.detail || error.message}`);
                    }
                }
                
                async getTickets(filters = {}) {
                    try {
                        const response = await axios.get(
                            `${this.baseUrl}/api/tickets`,
                            { 
                                headers: this.headers,
                                params: filters
                            }
                        );
                        return response.data;
                    } catch (error) {
                        throw new Error(`Failed to get tickets: ${error.response?.data?.detail || error.message}`);
                    }
                }
                
                async updateTicket(ticketId, updates) {
                    try {
                        const response = await axios.put(
                            `${this.baseUrl}/api/tickets/${ticketId}`,
                            updates,
                            { headers: this.headers }
                        );
                        return response.data;
                    } catch (error) {
                        throw new Error(`Failed to update ticket: ${error.response?.data?.detail || error.message}`);
                    }
                }
            }
            
            // Usage example
            const client = new TicketBotClient('http://localhost:8000', 'your_api_key_here');
            
            (async () => {
                try {
                    const ticket = await client.createTicket({
                        title: 'Node.js Integration Test',
                        description: 'Testing the API integration from Node.js',
                        creator_discord_id: 123456789,
                        discord_channel_id: 987654321,
                        priority: 'medium'
                    });
                    
                    console.log('Created ticket:', ticket.id);
                } catch (error) {
                    console.error('Error:', error.message);
                }
            })();
            """
        }