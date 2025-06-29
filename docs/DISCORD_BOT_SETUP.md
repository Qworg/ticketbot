# Discord Bot Setup and Configuration

This document provides comprehensive instructions for setting up and configuring the Discord bot for the Ticket Management System.

## Prerequisites

1. **Python 3.10+** - The bot requires Python 3.10 or higher
2. **Discord Application** - You need to create a Discord application and bot
3. **Discord Server** - A Discord server where you have administrator permissions
4. **Environment Variables** - Required configuration values

## Discord Application Setup

### 1. Create Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter a name for your application (e.g., "Ticket Bot")
4. Save the application

### 2. Create Bot User

1. Navigate to the "Bot" section in your application
2. Click "Add Bot"
3. Customize the bot's username and avatar if desired
4. Copy the bot token (keep this secure!)

### 3. Configure Bot Permissions

The bot requires the following permissions:
- **Read Messages/View Channels**
- **Send Messages**
- **Manage Channels**
- **Manage Messages**
- **Embed Links**
- **Attach Files**
- **Read Message History**
- **Use Slash Commands**

### 4. Configure OAuth2

1. Go to the "OAuth2" > "URL Generator" section
2. Select the following scopes:
   - `bot`
   - `applications.commands`
3. Select the required permissions (listed above)
4. Copy the generated URL and use it to invite the bot to your server

## Environment Configuration

Create a `.env` file in your project root with the following variables:

```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token_here
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_CLIENT_SECRET=your_client_secret_here

# Database Configuration
DATABASE_URL=sqlite:///./ticketbot.db
# For PostgreSQL: DATABASE_URL=postgresql://username:password@localhost:5432/ticketbot

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO
```

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Bot token from Discord Developer Portal | Yes |
| `DISCORD_CLIENT_ID` | Application ID from Discord Developer Portal | Yes |
| `DISCORD_CLIENT_SECRET` | Client secret for OAuth2 authentication | Yes |
| `DATABASE_URL` | Database connection string | Yes |
| `REDIS_URL` | Redis connection string for caching | Yes |
| `JWT_SECRET_KEY` | Secret key for JWT token signing | Yes |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No (default: INFO) |

## Bot Intents

The bot is configured with the following Discord intents:

- **DEFAULT** - Basic bot functionality
- **GUILDS** - Access to guild information
- **GUILD_MESSAGES** - Read guild messages
- **MESSAGE_CONTENT** - Access to message content

These intents must be enabled in the Discord Developer Portal under Bot > Privileged Gateway Intents.

## Running the Bot

### Development Mode

```bash
# Install dependencies
poetry install

# Run the bot directly
python app/bot.py

# Or run with the FastAPI server
python app/main.py
```

### Production Mode

```bash
# Set environment variables
export DISCORD_TOKEN="your_token_here"
export DATABASE_URL="your_database_url"
# ... other variables

# Run the bot
python app/bot.py
```

## Bot Features

### Connection Management

- **Automatic Reconnection** - The bot automatically handles connection interruptions
- **Graceful Shutdown** - Properly handles SIGTERM and SIGINT signals
- **Health Checks** - Built-in health check endpoint for monitoring
- **Error Handling** - Comprehensive error logging and recovery

### Event Handlers

- **on_ready** - Fired when bot connects and is ready
- **on_error** - Handles bot errors and exceptions
- **on_disconnect** - Handles disconnection events

### Logging

The bot uses Python's built-in logging module with the following features:

- **Configurable Log Levels** - Set via `LOG_LEVEL` environment variable
- **Structured Logging** - Includes timestamps, logger names, and levels
- **Error Tracking** - Detailed error logs with stack traces
- **Connection Events** - Logs all connection/disconnection events

## Monitoring and Health Checks

### Health Check Endpoint

The bot provides a health check method that returns:

```json
{
  "status": "healthy|unhealthy",
  "connected": true|false,
  "guilds": 5,
  "latency": 0.05
}
```

### Monitoring Metrics

- **Connection Status** - Whether the bot is connected to Discord
- **Guild Count** - Number of servers the bot is in
- **Latency** - Bot's latency to Discord servers
- **Ready State** - Internal ready state of the bot

## Troubleshooting

### Common Issues

1. **Invalid Token Error**
   - Verify `DISCORD_TOKEN` is correct
   - Ensure token hasn't been regenerated
   - Check for extra spaces or characters

2. **Permission Errors**
   - Verify bot has required permissions in Discord server
   - Check role hierarchy (bot role must be above roles it manages)
   - Ensure bot was invited with correct permissions

3. **Connection Issues**
   - Check network connectivity
   - Verify Discord API status
   - Check for firewall restrictions

4. **Intent Errors**
   - Enable required privileged intents in Discord Developer Portal
   - Verify bot has MESSAGE_CONTENT intent if reading message content

### Debug Mode

Enable debug mode by setting:

```bash
DEBUG=True
LOG_LEVEL=DEBUG
```

This provides detailed logging for troubleshooting.

## Security Considerations

1. **Token Security**
   - Never commit tokens to version control
   - Use environment variables or secure secret management
   - Rotate tokens regularly

2. **Permissions**
   - Grant minimum required permissions
   - Regularly audit bot permissions
   - Use role hierarchy properly

3. **Rate Limiting**
   - Bot includes built-in rate limiting
   - Monitor API usage to avoid rate limits
   - Implement exponential backoff for retries

## Performance Optimization

1. **Connection Pooling** - Database connections are pooled
2. **Caching** - Redis caching for frequently accessed data
3. **Async Operations** - All Discord operations are asynchronous
4. **Resource Management** - Proper cleanup of resources on shutdown

## Support

For additional support:

1. Check the logs for detailed error messages
2. Verify all environment variables are set correctly
3. Ensure Discord application is configured properly
4. Test bot permissions in a development server first
