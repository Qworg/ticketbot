"""Configuration settings for the Discord bot."""

import os
import logging
from typing import Optional, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("discord-bot")


class BotConfig(BaseModel):
    """Configuration settings for the Discord bot."""
    
    # Discord API settings
    token: str = Field(..., description="Discord bot token")
    guild_id: Optional[int] = Field(None, description="Discord guild ID for command syncing")
    
    # Backend API settings
    api_url: str = Field("http://localhost:8000", description="Backend API URL")
    api_key: Optional[str] = Field(None, description="API key for backend authentication")
    
    # Redis settings
    redis_url: str = Field("redis://localhost:6379", description="Redis URL for pub/sub")
    
    # Bot settings
    command_prefix: str = Field("!", description="Command prefix for text commands")
    ticket_category_id: Optional[int] = Field(None, description="Category ID for ticket channels")
    staff_role_id: Optional[int] = Field(None, description="Staff role ID")
    admin_role_id: Optional[int] = Field(None, description="Admin role ID")
    support_team_ids: List[int] = Field([], description="List of support team member IDs")
    
    # Permission settings
    auto_invite_staff: bool = Field(False, description="Automatically invite available staff to new tickets")
    max_auto_invite_staff: int = Field(3, description="Maximum number of staff to auto-invite")
    
    # Logging settings
    log_level: str = Field("INFO", description="Logging level")


def load_config() -> BotConfig:
    """Load configuration from environment variables."""
    # Required settings
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables")
        raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
    
    # Optional settings with defaults
    guild_id_str = os.getenv("DISCORD_GUILD_ID")
    guild_id = int(guild_id_str) if guild_id_str else None
    
    api_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    api_key = os.getenv("BACKEND_API_KEY")
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    command_prefix = os.getenv("COMMAND_PREFIX", "!")
    
    ticket_category_id_str = os.getenv("TICKET_CATEGORY_ID")
    ticket_category_id = int(ticket_category_id_str) if ticket_category_id_str else None
    
    staff_role_id_str = os.getenv("STAFF_ROLE_ID")
    staff_role_id = int(staff_role_id_str) if staff_role_id_str else None
    
    admin_role_id_str = os.getenv("ADMIN_ROLE_ID")
    admin_role_id = int(admin_role_id_str) if admin_role_id_str else None
    
    # Parse support team IDs (comma-separated list)
    support_team_ids_str = os.getenv("SUPPORT_TEAM_IDS", "")
    support_team_ids = []
    if support_team_ids_str:
        try:
            support_team_ids = [int(id_str.strip()) for id_str in support_team_ids_str.split(",") if id_str.strip()]
        except ValueError:
            logger.warning("Invalid SUPPORT_TEAM_IDS format. Expected comma-separated integers.")
    
    # Permission settings
    auto_invite_staff = os.getenv("AUTO_INVITE_STAFF", "").lower() in ("true", "yes", "1")
    
    max_auto_invite_staff_str = os.getenv("MAX_AUTO_INVITE_STAFF")
    max_auto_invite_staff = int(max_auto_invite_staff_str) if max_auto_invite_staff_str else 3
    
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Set logging level
    logger.setLevel(getattr(logging, log_level))
    
    return BotConfig(
        token=token,
        guild_id=guild_id,
        api_url=api_url,
        api_key=api_key,
        redis_url=redis_url,
        command_prefix=command_prefix,
        ticket_category_id=ticket_category_id,
        staff_role_id=staff_role_id,
        admin_role_id=admin_role_id,
        support_team_ids=support_team_ids,
        auto_invite_staff=auto_invite_staff,
        max_auto_invite_staff=max_auto_invite_staff,
        log_level=log_level,
    )


# Create a global config instance
config = load_config()