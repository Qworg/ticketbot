# JWT Authentication Documentation

## Overview

The JWT authentication module provides secure token-based authentication for the Discord Ticket Bot. It implements token generation, validation, and utility functions for handling user authentication.

## Features

- **Token Generation**: Creates JWT tokens with 24-hour expiration
- **Token Validation**: Validates token signatures and expiration
- **Claims Extraction**: Safely extracts claims from tokens
- **Error Handling**: Comprehensive error handling for various failure scenarios
- **Security**: Uses secure HMAC-SHA256 algorithm for token signing

## Configuration

### Environment Variables

The JWT module requires the following environment variable:

```bash
JWT_SECRET_KEY=your-super-secure-secret-key-here
```

**Security Notes:**
- The secret key should be at least 32 characters long
- Use a cryptographically secure random string
- Never commit the secret key to version control
- Rotate the secret key periodically for enhanced security

## Usage

### Token Generation

```python
from app.auth import generate_token

user_data = {
    'user_id': 'uuid-string',
    'discord_id': 123456789,
    'role': 'USER',  # or 'STAFF', 'ADMIN'
    'email': 'user@example.com'  # optional
}

token = generate_token(user_data)
```

### Token Validation

```python
from app.auth import validate_token, TokenExpiredError, TokenInvalidError

try:
    token_data = validate_token(token)
    print(f"User ID: {token_data.user_id}")
    print(f"Role: {token_data.role}")
    print(f"Expires: {token_data.expires_at}")
except TokenExpiredError:
    print("Token has expired")
except TokenInvalidError:
    print("Token is invalid or tampered")
```

### Helper Functions

```python
from app.auth import extract_claims, get_token_expiry, is_token_expired

# Extract claims without validation (for debugging)
claims = extract_claims(token)

# Get expiration time
expiry = get_token_expiry(token)

# Quick expiration check
if is_token_expired(token):
    print("Token needs renewal")
```

## Token Structure

JWT tokens contain the following claims:

| Claim | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Yes | User's UUID |
| `discord_id` | integer | Yes | Discord user ID |
| `role` | string | Yes | User role (USER, STAFF, ADMIN) |
| `email` | string | No | User's email address |
| `iat` | timestamp | Yes | Issued at time |
| `exp` | timestamp | Yes | Expiration time |

## Error Handling

The module defines custom exceptions:

- **`JWTError`**: Base exception for JWT-related errors
- **`TokenExpiredError`**: Token has expired and needs renewal
- **`TokenInvalidError`**: Token is malformed, tampered, or has invalid signature

## Security Considerations

1. **Secret Key Management**: Store the JWT secret key securely using environment variables
2. **Token Transmission**: Always use HTTPS when transmitting tokens
3. **Token Storage**: Store tokens in secure, HTTP-only cookies when possible
4. **Token Rotation**: Implement token refresh mechanism for long-lived sessions
5. **Validation**: Always validate tokens on the server side before trusting claims

## Testing

The module includes comprehensive unit tests covering:

- Token generation with valid and invalid data
- Token validation with various scenarios
- Expiration handling and timing tests
- Error cases and edge conditions
- Helper function behavior

Run tests with:

```bash
poetry run pytest tests/test_auth.py -v
```

## Integration

The JWT module integrates with:

- **FastAPI middleware**: For automatic token validation
- **Discord OAuth2**: For initial token generation after authentication
- **Database models**: For user validation and role checking
- **WebSocket connections**: For real-time authentication

## Performance

- Token validation is O(1) time complexity
- Uses efficient HMAC-SHA256 algorithm
- Claims extraction is lightweight for debugging purposes
- No database queries required for basic token validation

## Troubleshooting

### Common Issues

1. **"JWT_SECRET_KEY environment variable is required"**
   - Ensure the environment variable is set before importing the module
   - Check spelling and case sensitivity

2. **"Token has expired"**
   - Token lifetime is 24 hours - implement refresh mechanism
   - Check system clock synchronization

3. **"Invalid token" errors**
   - Verify token hasn't been modified during transmission
   - Ensure consistent secret key across all services

### Debug Mode

For debugging, use the `extract_claims()` function to inspect token contents without validation:

```python
claims = extract_claims(suspicious_token)
print(f"Token claims: {claims}")
```

## Migration Guide

When updating the JWT implementation:

1. **Secret Key Rotation**: Deploy new secret key gradually
2. **Algorithm Changes**: Ensure backward compatibility during transition
3. **Claim Structure**: Add new claims without breaking existing tokens
4. **Expiration Changes**: Consider existing token lifetimes
