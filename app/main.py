"""
Main FastAPI application for Discord Ticket Bot.

This module sets up the FastAPI application with OAuth2 authentication routes.
"""

import os
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
import secrets
from typing import Optional

from .auth import generate_token, JWTError
from .database import get_db_session
from .models.user import User, create_user, get_user_by_discord_id, update_user
from .cache import init_redis
from .middleware import get_current_user, require_authentication

# FastAPI app initialization
app = FastAPI(
    title="Discord Ticket Bot API",
    description="API for Discord Ticket Management System",
    version="0.1.0"
)

# Initialize Redis for caching and rate limiting
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
init_redis(redis_url)

# Add session middleware for OAuth2 state management
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SESSION_SECRET_KEY", secrets.token_hex(32))
)

# OAuth2 configuration
config = Config(environ=os.environ)
oauth = OAuth(config)

# Discord OAuth2 client configuration - will be None if credentials missing
discord_client_id = os.getenv('DISCORD_CLIENT_ID')
discord_client_secret = os.getenv('DISCORD_CLIENT_SECRET')

discord = None
if discord_client_id and discord_client_secret:
    discord = oauth.register(
        name='discord',
        client_id=discord_client_id,
        client_secret=discord_client_secret,
        authorize_url='https://discord.com/api/oauth2/authorize',
        access_token_url='https://discord.com/api/oauth2/token',
        client_kwargs={
            'scope': 'identify email guilds'
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Discord Ticket Bot API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/auth/discord/login")
async def discord_login(request: Request):
    """
    Initiate Discord OAuth2 authentication flow.
    
    Redirects user to Discord for authentication with state parameter for CSRF protection.
    """
    # Check if Discord OAuth2 is configured
    if not discord:
        raise HTTPException(
            status_code=500, 
            detail="Discord OAuth2 credentials not configured"
        )
    
    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    
    # Redirect to Discord OAuth2
    redirect_uri = request.url_for('discord_callback')
    return await discord.authorize_redirect(request, redirect_uri, state=state)


@app.get("/auth/discord/callback")
async def discord_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    """
    Handle Discord OAuth2 callback.
    
    Processes the OAuth2 response, extracts user data, and creates/updates user record.
    """
    # Check if Discord OAuth2 is configured
    if not discord:
        raise HTTPException(status_code=500, detail="Discord OAuth2 not configured")
    
    # Verify state parameter for CSRF protection
    session_state = request.session.get('oauth_state')
    if not state or state != session_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Clear session state
    request.session.pop('oauth_state', None)
    
    try:
        # Exchange code for access token
        token = await discord.authorize_access_token(request)
        
        # Get user profile from Discord API
        user_info = await discord.get('https://discord.com/api/users/@me', token=token)
        user_data = user_info.json()
        
        # Extract user information
        discord_id = int(user_data['id'])
        username = user_data['username']
        email = user_data.get('email')
        avatar = user_data.get('avatar')
        
        # Get database session
        db_session = get_db_session()
        
        try:
            # Check if user exists
            existing_user = get_user_by_discord_id(db_session, discord_id)
            
            if existing_user:
                # Update existing user
                user = update_user(
                    db_session, 
                    user_id=existing_user.id,  # Explicitly name the parameter
                    email=email,
                    username=username,
                    avatar=avatar
                )
            else:
                # Create new user
                user = create_user(
                    db_session,
                    discord_id=discord_id,
                    email=email,
                    username=username,
                    avatar=avatar,
                    role='USER'  # Default role for new users
                )
            
            # Generate JWT token
            if user:
                token_data = {
                    'user_id': str(user.id),
                    'discord_id': user.discord_id,
                    'role': user.role,
                    'email': user.email
                }
                
                jwt_token = generate_token(token_data)
                
                # Create response and set secure cookie
                response = RedirectResponse(url="/dashboard")
                response.set_cookie(
                    key="auth_token",
                    value=jwt_token,
                    httponly=True,
                    secure=True,  # Use in production with HTTPS
                    samesite="strict",
                    max_age=24 * 60 * 60  # 24 hours
                )
                
                return response
            else:
                raise HTTPException(status_code=500, detail="Failed to create or update user")
            
        finally:
            db_session.close()
            
    except Exception as e:
        # Log the error for debugging
        print(f"OAuth2 callback error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Authentication failed. Please try again."
        )


@app.get("/auth/logout")
async def logout():
    """
    Logout user by clearing authentication cookie.
    """
    response = RedirectResponse(url="/")
    response.delete_cookie(key="auth_token")
    return response


@app.get("/dashboard")
async def dashboard():
    """
    Dashboard endpoint (placeholder).
    
    This will be expanded with the actual dashboard implementation.
    """
    return {"message": "Dashboard - Authentication successful!"}


@app.get("/api/user/profile")
async def get_user_profile(user_info=Depends(require_authentication())):
    """
    Get current user profile information.
    Protected endpoint demonstrating middleware usage.
    """
    return {
        "user_id": user_info["user_id"],
        "role": user_info["role"],
        "discord_id": user_info["discord_id"],
        "email": user_info["user"].email
    }


@app.get("/api/health/auth")
async def auth_health_check(user_info=Depends(get_current_user)):
    """
    Health check endpoint that shows authentication status.
    """
    if user_info.get("is_authenticated"):
        return {"status": "authenticated", "user_id": user_info["user_id"]}
    else:
        return {"status": "not_authenticated"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
