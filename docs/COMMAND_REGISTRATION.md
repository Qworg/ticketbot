# Command Registration System Documentation

## Overview

The Discord bot command registration system provides a robust framework for creating, registering, and managing slash commands with built-in features like cooldowns, rate limiting, permission checking, and error handling.

## Architecture

### Core Components

1. **BaseCommand**: Abstract base class for all commands
2. **CommandRegistry**: Manages command registration and Discord integration
3. **CommandManager**: Handles background maintenance tasks
4. **Error Classes**: Specialized exceptions for different error scenarios

### Key Features

- **Automatic Permission Checking**: Role-based and permission-based access control
- **Cooldown Management**: Per-user cooldowns to prevent spam
- **Rate Limiting**: Commands per minute limits
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Command Analytics**: Usage logging and statistics
- **Background Cleanup**: Automatic cleanup of tracking data

## Creating Commands

### Basic Command

```python
from app.commands.base import BaseCommand
import interactions

class MyCommand(BaseCommand):
    def __init__(self):
        super().__init__(
            name="mycommand",
            description="My custom command",
            cooldown_seconds=5.0,
            rate_limit_per_minute=10
        )
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs):
        await ctx.send("Hello from my command!")
```

### Command with Permissions

```python
class StaffCommand(BaseCommand):
    def __init__(self):
        super().__init__(
            name="staffcommand",
            description="Staff-only command",
            staff_only=True,
            required_permissions=["MANAGE_TICKETS"]
        )
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs):
        await ctx.send("This is a staff command!")
```

### Command with Validation

```python
class ValidatedCommand(BaseCommand):
    def __init__(self):
        super().__init__(
            name="validated",
            description="Command with argument validation"
        )
    
    def validate_arguments(self, **kwargs):
        if 'message' in kwargs and len(kwargs['message']) > 100:
            raise CommandValidationError('message', 'Message too long')
    
    async def _execute(self, ctx: interactions.SlashContext, **kwargs):
        self.validate_arguments(**kwargs)
        await ctx.send(f"Message: {kwargs.get('message', 'No message')}")
```

## Command Configuration Options

### Basic Options

- `name`: Command name (required)
- `description`: Command description (required)
- `cooldown_seconds`: Cooldown time between uses (default: 0)
- `rate_limit_per_minute`: Maximum uses per minute (default: None)

### Permission Options

- `staff_only`: Requires STAFF or ADMIN role (default: False)
- `admin_only`: Requires ADMIN role (default: False)
- `required_permissions`: List of specific permissions required

### Available Permissions

- `CREATE_TICKET`: Can create support tickets
- `MANAGE_TICKETS`: Can manage and assign tickets
- `VIEW_ANALYTICS`: Can view analytics and reports
- `ADMIN_SETTINGS`: Can modify system settings

## Error Handling

### Built-in Error Types

1. **CommandError**: Base error class
2. **CommandCooldownError**: Command is on cooldown
3. **CommandPermissionError**: Insufficient permissions
4. **CommandRateLimitError**: Rate limit exceeded
5. **CommandValidationError**: Invalid arguments

### Custom Error Handling

```python
async def _execute(self, ctx: interactions.SlashContext, **kwargs):
    try:
        # Command logic here
        pass
    except SomeCustomError as e:
        raise CommandError(str(e), "Something went wrong!")
```

## Command Registration

### Manual Registration

```python
from app.commands.registry import get_command_registry

# Get registry and register command
registry = get_command_registry(bot)
registry.register_command(MyCommand())
```

### Auto-Registration in Bot Setup

Commands are automatically registered in `bot.py`:

```python
def _setup_commands(self):
    """Set up bot commands."""
    self.command_registry.register_command(HelpCommand())
    self.command_registry.register_command(MyNewCommand())
```

## Background Maintenance

The command system includes automatic maintenance:

- **Cooldown Cleanup**: Removes expired cooldown data every 5 minutes
- **Rate Limit Cleanup**: Removes old rate limit entries
- **Memory Management**: Prevents memory leaks from tracking data

## Testing Commands

### Unit Testing

```python
import pytest
from app.commands.base import BaseCommand

class TestMyCommand:
    def setup_method(self):
        self.command = MyCommand()
        self.mock_ctx = Mock(spec=interactions.SlashContext)
    
    @pytest.mark.asyncio
    async def test_command_execution(self):
        await self.command.execute(self.mock_ctx)
        # Add assertions
```

### Integration Testing

Commands can be tested with the full permission and database system:

```python
@patch('app.commands.base.get_db_session')
@pytest.mark.asyncio
async def test_with_permissions(self, mock_db):
    # Mock database and permissions
    # Test command execution
```

## Performance Considerations

### Memory Usage

- Cooldown and rate limit data is automatically cleaned up
- Use appropriate cooldown and rate limit values
- Consider using database storage for persistent tracking

### Database Connections

- Commands automatically handle database sessions
- Sessions are properly closed after permission checks
- Use connection pooling for high-traffic scenarios

### Discord API Limits

- Global command sync happens once on startup
- Commands are cached by Discord after registration
- Rate limits are handled automatically by the library

## Best Practices

### Command Design

1. Keep commands focused on a single responsibility
2. Use descriptive names and descriptions
3. Implement proper validation for all arguments
4. Provide helpful error messages to users

### Security

1. Always use permission checks for sensitive commands
2. Validate all user input
3. Use appropriate cooldowns to prevent abuse
4. Log command usage for security monitoring

### Error Handling

1. Catch specific exceptions rather than broad catches
2. Provide user-friendly error messages
3. Log errors with appropriate severity levels
4. Use ephemeral responses for error messages

### Testing

1. Write unit tests for all command logic
2. Test permission checking scenarios
3. Test error conditions and edge cases
4. Use mocks for external dependencies

## Monitoring and Analytics

### Command Statistics

```python
from app.commands.registry import get_command_registry

registry = get_command_registry()
stats = registry.get_command_stats()
print(f"Total commands: {stats['total_commands']}")
```

### Usage Logging

All command executions are automatically logged with:
- User ID
- Guild ID
- Command name
- Execution time
- Success/failure status

### Health Monitoring

The command manager provides health status:
- Active commands count
- Background task status
- Memory usage statistics
