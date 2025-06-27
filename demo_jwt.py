#!/usr/bin/env python3
"""
Simple JWT demo script to verify implementation.
"""

import os
os.environ['JWT_SECRET_KEY'] = 'test-secret-for-demo'

from app.auth import generate_token, validate_token

# Test the complete JWT flow
user_data = {
    'user_id': 'demo-user-123',
    'discord_id': 987654321,
    'role': 'STAFF',
    'email': 'demo@example.com'
}

print('=== JWT Token Generation Demo ===')
token = generate_token(user_data)
print(f'Generated token (first 50 chars): {token[:50]}...')

token_data = validate_token(token)
print(f'Validated user_id: {token_data.user_id}')
print(f'Validated discord_id: {token_data.discord_id}')
print(f'Validated role: {token_data.role}')
print(f'Token expires at: {token_data.expires_at}')

print('✅ JWT implementation working correctly!')
