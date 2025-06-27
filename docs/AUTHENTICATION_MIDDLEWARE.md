# Authentication Middleware Documentation

## Overview

The authentication middleware provides comprehensive JWT-based authentication for the Discord Ticket Bot API. It handles token extraction, validation, user verification, rate limiting, and security monitoring.

## Features

- **JWT Token Authentication**: Validates Bearer tokens from Authorization headers
- **Cookie Authentication**: Supports HTTP-only cookies for web dashboard
- **Rate Limiting**: Prevents brute force attacks with Redis-based rate limiting
- **Security Monitoring**: Logs authentication failures for security analysis
- **Public Endpoint Bypass**: Automatically skips authentication for public routes
- **User Verification**: Validates user existence and account status in database
- **Flexible Dependencies**: Provides optional and required authentication decorators

## Core Components

### Authentication Middleware (`app/middleware.py`)

#### `get_current_user(request, credentials, db)`

Main authentication dependency that:
- Extracts JWT token from Authorization header
- Validates token signature and expiration
- Verifies user exists in database
- Checks user account status
- Implements rate limiting for failed attempts
- Returns user information for downstream handlers

**Parameters:**
- `request`: FastAPI Request object
- `credentials`: HTTPAuthorizationCredentials (optional)
- `db`: Database session

**Returns:**
- Dictionary with user information if authenticated
- `{"is_authenticated": False}` for public endpoints

**Raises:**
- `HTTPException(401)`: Invalid/missing/expired token
- `HTTPException(429)`: Rate limit exceeded

#### `get_optional_user(request, credentials, db)`

Optional authentication that doesn't raise exceptions.

**Returns:**
- User information if authenticated
- `None` if authentication fails

#### `require_authentication()`

Dependency factory that requires valid authentication.

**Usage:**
```python
@app.get("/protected")
async def protected_endpoint(user_info=Depends(require_authentication())):
    return {"user_id": user_info["user_id"]}
```

#### `get_user_from_cookie(request, db)`

Authenticates users via HTTP-only cookies for web dashboard.

### Permission Decorators (`app/decorators.py`)

Enhanced to work with the new middleware system.

#### `require_permissions(*permissions)`

Requires specific permissions.

**Usage:**
```python
@app.get("/tickets")
async def list_tickets(user_info=Depends(require_permissions(Permission.MANAGE_TICKETS))):
    pass
```

#### `require_role(role)`

Requires minimum role level.

**Usage:**
```python
@app.get("/admin")
async def admin_panel(user_info=Depends(require_role(Role.ADMIN))):
    pass
```

#### Common Permission Decorators

- `require_admin()`: Admin-only access
- `require_staff()`: Staff+ access
- `require_authenticated()`: Any authenticated user
- `require_ticket_management()`: Ticket management permissions
- `require_analytics_access()`: Analytics view permissions

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here

# Redis Configuration (for rate limiting)
REDIS_URL=redis://localhost:6379/0

# Session Configuration (for OAuth2)
SESSION_SECRET_KEY=your-session-secret-here
```

### Public Endpoints

Public endpoints that bypass authentication:

```python
PUBLIC_ENDPOINTS = {
    "/",
    "/health", 
    "/docs",
    "/openapi.json",
    "/auth/discord/login",
    "/auth/discord/callback",
    "/auth/logout"
}
```

Add new public endpoints by modifying this set.

### Rate Limiting

- **Window**: 5 minutes (300 seconds)
- **Max Attempts**: 10 failed attempts per IP
- **Storage**: Redis (fallback to allowing requests if Redis unavailable)

## Usage Examples

### Basic Protected Endpoint

```python
from fastapi import FastAPI, Depends
from app.middleware import require_authentication

app = FastAPI()

@app.get("/api/profile")
async def get_profile(user_info=Depends(require_authentication())):
    return {
        "user_id": user_info["user_id"],
        "role": user_info["role"],
        "discord_id": user_info["discord_id"]
    }
```

### Permission-Based Protection

```python
from app.decorators import require_permissions
from app.permissions import Permission

@app.post("/api/tickets")
async def create_ticket(
    ticket_data: dict,
    user_info=Depends(require_permissions(Permission.CREATE_TICKET))
):
    # Create ticket logic
    pass
```

### Role-Based Protection

```python
from app.decorators import require_role
from app.permissions import Role

@app.get("/api/admin/analytics")
async def get_analytics(user_info=Depends(require_role(Role.ADMIN))):
    # Admin-only analytics
    pass
```

### Optional Authentication

```python
from app.middleware import get_optional_user

@app.get("/api/public-content")
async def get_public_content(user_info=Depends(get_optional_user)):
    if user_info and user_info.get("is_authenticated"):
        # Personalized content for authenticated users
        return {"content": "personalized", "user_id": user_info["user_id"]}
    else:
        # Generic content for anonymous users
        return {"content": "generic"}
```

### Cookie Authentication (Web Dashboard)

```python
from app.middleware import get_user_from_cookie

@app.get("/dashboard")
async def dashboard(
    request: Request,
    user_info=Depends(get_user_from_cookie)
):
    if not user_info:
        return RedirectResponse("/auth/discord/login")
    
    return {"dashboard_data": "..."}
```

## Security Features

### Rate Limiting

Prevents brute force attacks by limiting failed authentication attempts:

- Tracks failed attempts per IP address
- 10 attempts allowed per 5-minute window
- Returns 429 status when limit exceeded
- Automatically resets after time window

### Authentication Logging

All authentication failures are logged with:

- Client IP address
- Failure reason
- User agent
- Timestamp

Example log entry:
```
WARNING:app.middleware:Authentication failure - IP: 192.168.1.100, Reason: Token expired, User-Agent: Mozilla/5.0...
```

### Token Validation

Comprehensive token validation includes:

- JWT signature verification
- Expiration time checking
- Required claims validation
- User existence verification
- Account status checking

### Secure Cookie Handling

For web dashboard authentication:

- HTTP-only cookies (not accessible via JavaScript)
- Secure flag (HTTPS only in production)
- SameSite strict policy
- 24-hour expiration

## Error Handling

### Common HTTP Status Codes

- **401 Unauthorized**: Invalid, missing, or expired token
- **403 Forbidden**: Insufficient permissions
- **429 Too Many Requests**: Rate limit exceeded

### Error Response Format

```json
{
    "detail": "Error description",
    "headers": {
        "WWW-Authenticate": "Bearer"
    }
}
```

## Testing

### Unit Tests

Run authentication middleware tests:

```bash
pytest tests/test_middleware.py -v
```

### Integration Tests

Test complete authentication flow:

```bash
pytest tests/test_middleware_integration.py -v
```

### Test Coverage

Tests cover:

- Valid token authentication
- Invalid/expired token rejection
- Missing authorization headers
- Rate limiting functionality
- User verification
- Permission checking
- Public endpoint bypass
- Cookie authentication

## Troubleshooting

### Common Issues

1. **"Authorization header required"**
   - Ensure Authorization header is present
   - Use format: `Authorization: Bearer <token>`

2. **"Token has expired"**
   - Generate new token via OAuth2 flow
   - Check system clock synchronization

3. **"User not found"**
   - User may have been deleted from database
   - Token may contain invalid user_id

4. **"Too many failed authentication attempts"**
   - Wait 5 minutes for rate limit reset
   - Check for potential brute force attacks

5. **Rate limiting not working**
   - Verify Redis connection
   - Check Redis configuration

### Debug Mode

Enable debug logging to troubleshoot authentication issues:

```python
import logging
logging.getLogger("app.middleware").setLevel(logging.DEBUG)
```

## Security Best Practices

1. **Use HTTPS in production** to protect tokens in transit
2. **Rotate JWT secrets regularly**
3. **Monitor authentication failure logs** for suspicious activity
4. **Set appropriate token expiration times** (default: 24 hours)
5. **Use Redis for rate limiting** in production environments
6. **Validate user account status** before granting access
7. **Implement proper CORS policies** for web clients

## Migration from Previous Authentication

If migrating from a previous authentication system:

1. Update endpoint decorators to use new middleware
2. Replace custom authentication logic with provided dependencies
3. Update error handling for new status codes
4. Test all protected endpoints thoroughly
5. Update documentation for API consumers
