# Discord OAuth2 Integration

This document explains how the Discord OAuth2 authentication is implemented in the ticketbot application.

## Overview

The Discord OAuth2 integration allows users to authenticate using their Discord accounts. The flow includes:

1. User visits `/auth/discord/login` to start authentication
2. User is redirected to Discord for authorization
3. Discord redirects back to `/auth/discord/callback` with authorization code
4. Application exchanges code for user information
5. User is created/updated in database
6. JWT token is generated and set as secure cookie
7. User is redirected to dashboard

## Configuration

Required environment variables:

```bash
DISCORD_CLIENT_ID=your_discord_client_id_here
DISCORD_CLIENT_SECRET=your_discord_client_secret_here
JWT_SECRET_KEY=your-super-secret-jwt-key-here
SESSION_SECRET_KEY=your-session-secret-key-here
```

## Discord Application Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to OAuth2 settings
4. Add redirect URI: `http://localhost:8000/auth/discord/callback` (for development)
5. Note down Client ID and Client Secret
6. Set required scopes: `identify`, `email`, `guilds`

## Security Features

### CSRF Protection
- State parameter is generated for each OAuth2 request
- State is stored in session and validated on callback
- Invalid state returns 400 error

### Secure Cookies
- JWT token is stored in HTTP-only cookie
- Cookie has `secure` flag (HTTPS only in production)
- Cookie has `samesite=strict` for additional protection
- 24-hour expiration time

### Error Handling
- Graceful handling of missing OAuth2 credentials
- User-friendly error messages
- Proper HTTP status codes
- Security event logging

## API Endpoints

### `GET /auth/discord/login`
Initiates Discord OAuth2 flow.

**Response:**
- Redirects to Discord authorization URL
- Sets session state for CSRF protection

**Errors:**
- `500` - Discord OAuth2 credentials not configured

### `GET /auth/discord/callback`
Handles Discord OAuth2 callback.

**Parameters:**
- `code` - Authorization code from Discord
- `state` - CSRF protection state parameter

**Response:**
- Redirects to `/dashboard` on success
- Sets `auth_token` cookie with JWT

**Errors:**
- `400` - Invalid state parameter
- `500` - Authentication failed or Discord OAuth2 not configured

### `GET /auth/logout`
Logs out user by clearing authentication cookie.

**Response:**
- Redirects to root path
- Deletes `auth_token` cookie

## Database Integration

When a user authenticates:

1. Check if user exists by Discord ID
2. If exists: Update user information (email, username, avatar)
3. If not exists: Create new user with default role 'USER'
4. Generate JWT token with user data
5. Return user to dashboard

## Error Scenarios

### Missing Credentials
If Discord OAuth2 credentials are not configured, the application will:
- Still start successfully
- Return 500 error for OAuth2 endpoints
- Allow other endpoints to function normally

### Authentication Failures
- Invalid OAuth2 responses are logged and return 500 error
- Database errors during user creation/update return 500 error
- All errors include user-friendly messages

## Testing

OAuth2 integration includes tests for:
- Missing credentials handling
- State parameter validation
- Error scenarios
- Security features
- Configuration validation

Run tests with:
```bash
pytest tests/test_oauth2_integration.py -v
```

## Development vs Production

### Development
- Use `http://localhost:8000` for redirect URI
- Set `secure=False` for cookies (HTTP)
- Enable debug logging

### Production
- Use HTTPS domain for redirect URI
- Set `secure=True` for cookies (HTTPS only)
- Use strong secret keys
- Enable security headers
- Monitor authentication failures

## Next Steps

The OAuth2 integration is ready for:
1. Role-based permissions system (Story E1-004)
2. API authentication middleware (Story E1-005)
3. Dashboard implementation
4. Discord bot integration
