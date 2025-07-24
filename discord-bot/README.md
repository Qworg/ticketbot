# Discord Ticket Bot

A Discord bot for managing support tickets with integration to a FastAPI backend and React web dashboard.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

### Installation

1. Clone the repository
2. Navigate to the discord-bot directory
3. Run the installation script:

```bash
python install_dev.py
```

This will:
- Create a virtual environment in the `.venv` directory
- Install the package in development mode

### Running Tests

To run tests, use one of the following commands:

```bash
# Using uv directly
uv run pytest

# Using the test runner script
uv run python run_tests_fixed.py
```

### Environment Variables

Create a `.env` file in the discord-bot directory with the following variables:

```
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_guild_id
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=your_api_key
REDIS_URL=redis://localhost:6379
TICKET_CATEGORY_ID=your_category_id
STAFF_ROLE_ID=your_staff_role_id
ADMIN_ROLE_ID=your_admin_role_id
SUPPORT_TEAM_IDS=id1,id2,id3
AUTO_INVITE_STAFF=true
MAX_AUTO_INVITE_STAFF=3
LOG_LEVEL=INFO
```

### Running the Bot

To run the bot:

```bash
uv run python main.py
```

## Project Structure

- `bot/` - Core bot functionality
  - `ticket_bot.py` - Main bot class
  - `ticket_manager.py` - Ticket management
  - `permission_manager.py` - Discord permission handling
  - `message_processor.py` - Message processing and formatting
  - `cogs/` - Discord command modules
- `config/` - Configuration settings
- `utils/` - Utility functions and classes
- `tests/` - Test suite