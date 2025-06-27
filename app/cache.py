"""
Redis caching layer for user permissions.
Provides fast access to user permissions with 1-hour expiration.
"""
import json
import redis
from typing import Set, Optional
from datetime import timedelta
import logging
from app.permissions import Permission, get_user_permissions
from app.models.role_assignment import get_user_role_in_guild

logger = logging.getLogger(__name__)

# Redis client - will be initialized in main app
redis_client: Optional[redis.Redis] = None

PERMISSIONS_CACHE_TTL = timedelta(hours=1)  # 1 hour cache expiration


def init_redis(redis_url: str = "redis://localhost:6379/0"):
    """
    Initialize Redis client for permissions caching.
    
    Args:
        redis_url: Redis connection URL
    """
    global redis_client
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        # Test connection
        redis_client.ping()
        logger.info("Redis client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {e}")
        redis_client = None


def _get_cache_key(user_id: str, guild_id: Optional[int] = None) -> str:
    """
    Generate cache key for user permissions.
    
    Args:
        user_id: User UUID as string
        guild_id: Optional guild ID for guild-specific permissions
        
    Returns:
        str: Cache key
    """
    if guild_id:
        return f"permissions:user:{user_id}:guild:{guild_id}"
    return f"permissions:user:{user_id}:global"


def cache_user_permissions(user_id: str, permissions: Set[Permission], guild_id: Optional[int] = None):
    """
    Cache user permissions in Redis.
    
    Args:
        user_id: User UUID as string
        permissions: Set of permissions to cache
        guild_id: Optional guild ID for guild-specific permissions
    """
    if not redis_client:
        logger.warning("Redis client not initialized, skipping cache")
        return
    
    try:
        cache_key = _get_cache_key(user_id, guild_id)
        # Convert Permission enum to string list for JSON serialization
        permissions_list = [perm.value for perm in permissions]
        
        redis_client.setex(
            cache_key,
            PERMISSIONS_CACHE_TTL,
            json.dumps(permissions_list)
        )
        logger.debug(f"Cached permissions for user {user_id} in guild {guild_id}")
    except Exception as e:
        logger.error(f"Failed to cache permissions: {e}")


def get_cached_user_permissions(user_id: str, guild_id: Optional[int] = None) -> Optional[Set[Permission]]:
    """
    Get cached user permissions from Redis.
    
    Args:
        user_id: User UUID as string
        guild_id: Optional guild ID for guild-specific permissions
        
    Returns:
        Optional[Set[Permission]]: Cached permissions or None if not found/expired
    """
    if not redis_client:
        return None
    
    try:
        cache_key = _get_cache_key(user_id, guild_id)
        cached_data = redis_client.get(cache_key)
        
        if cached_data and isinstance(cached_data, str):
            permissions_list = json.loads(cached_data)
            # Convert back to Permission enum set
            permissions = {Permission(perm) for perm in permissions_list}
            logger.debug(f"Retrieved cached permissions for user {user_id} in guild {guild_id}")
            return permissions
        
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve cached permissions: {e}")
        return None


def invalidate_user_permissions(user_id: str, guild_id: Optional[int] = None):
    """
    Invalidate cached user permissions.
    
    Args:
        user_id: User UUID as string
        guild_id: Optional guild ID. If None, invalidates all guild caches for user
    """
    if not redis_client:
        return
    
    try:
        if guild_id:
            # Invalidate specific guild cache
            cache_key = _get_cache_key(user_id, guild_id)
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated permissions cache for user {user_id} in guild {guild_id}")
        else:
            # Invalidate all caches for this user
            pattern = f"permissions:user:{user_id}:*"
            keys = redis_client.keys(pattern)
            if keys and isinstance(keys, list):
                redis_client.delete(*keys)
                logger.debug(f"Invalidated all permissions caches for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate permissions cache: {e}")


def get_user_permissions_cached(db_session, user_id: str, guild_id: Optional[int] = None) -> Set[Permission]:
    """
    Get user permissions with Redis caching.
    First checks cache, then falls back to database query.
    
    Args:
        db_session: Database session
        user_id: User UUID as string  
        guild_id: Optional guild ID for guild-specific permissions
        
    Returns:
        Set[Permission]: User's permissions
    """
    # Try to get from cache first
    cached_permissions = get_cached_user_permissions(user_id, guild_id)
    if cached_permissions is not None:
        return cached_permissions
    
    # Cache miss - get from database
    try:
        import uuid
        user_uuid = uuid.UUID(user_id)
        
        if guild_id:
            # Get guild-specific role and permissions
            from app.models.role_assignment import get_user_permissions_in_guild
            permissions = get_user_permissions_in_guild(db_session, user_uuid, guild_id)
        else:
            # Get global role and permissions
            from app.models.user import User
            user = db_session.query(User).filter(User.id == user_uuid).first()
            if user:
                permissions = get_user_permissions(str(user.role))
            else:
                permissions = get_user_permissions("USER")  # Default permissions
        
        # Cache the result
        cache_user_permissions(user_id, permissions, guild_id)
        
        return permissions
        
    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        # Return default USER permissions as fallback
        return get_user_permissions("USER")
