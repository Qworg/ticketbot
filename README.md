# Discord Ticket Bot

A comprehensive support ticket management system that integrates Discord channels with a FastAPI backend and React web dashboard. This system enables organizations to provide customer support through Discord while giving staff members the flexibility to manage tickets through either Discord commands or a web interface.

## Features

- 🎫 **Ticket Management**: Create, assign, and close tickets through Discord or web interface
- 🔄 **Real-time Sync**: Seamless synchronization between Discord and web dashboard
- 👥 **Permission System**: Role-based access control for staff members
- 📝 **Transcript Generation**: Automatic conversation history with search capabilities
- 🔍 **Advanced Search**: Full-text search across all ticket transcripts
- 🔗 **Transcript Sharing**: Secure sharing of ticket conversations
- 🌐 **REST API**: Complete API for external system integration
- 📊 **Web Dashboard**: Modern React-based interface for staff

## Architecture

The system consists of three main microservices:

- **Discord Bot Service** (Python + py-cord): Handles Discord interactions
- **FastAPI Backend**: Provides REST API and business logic
- **React Dashboard**: Web interface for staff management
- **PostgreSQL**: Primary database for persistent storage
- **Redis**: Caching and real-time synchronization

## Project Structure

```
ticketbot/
├── .env                  # Environment variables (from .env.template)
├── .env.template         # Template for environment variables
├── docker-compose.yml    # Docker Compose configuration
├── README.md             # Project documentation
├── start.sh              # Script to start development environment
├── stop.sh               # Script to stop development environment
├── reset-db.sh           # Script to reset database and run migrations
├── setup-local-db.bat    # Windows script for local database setup
│
├── .kiro/                # Kiro IDE configuration
│   ├── specs/            # Kiro specifications
│   └── steering/         # Kiro steering rules
│       └── python-uv.md  # uv package manager guidance
│
├── backend/              # FastAPI Backend Service
│   ├── Dockerfile        # Docker configuration for backend
│   ├── alembic.ini       # Alembic configuration
│   ├── main.py           # FastAPI application entry point
│   ├── models.py         # SQLAlchemy database models
│   ├── schemas.py        # Pydantic schemas for API
│   ├── database_service.py # Database service layer
│   ├── db.py             # Database connection utilities
│   ├── pyproject.toml    # Python project dependencies (for uv)
│   ├── uv.lock           # uv lock file for dependencies
│   ├── .python-version   # Python version specification
│   ├── pytest.ini        # Pytest configuration
│   ├── run_tests.py      # Test runner script
│   ├── __init__.py       # Package initialization
│   ├── repositories/     # Repository pattern implementations
│   ├── services/         # Business logic services
│   ├── tests/            # Test suite
│   │   └── test_enhanced_database_service.py # Database service tests
│   └── migrations/       # Database migrations
│       ├── env.py        # Alembic environment
│       ├── script.py.mako # Migration template
│       └── versions/     # Migration versions
│
├── discord-bot/          # Discord Bot Service
│   ├── Dockerfile        # Docker configuration for Discord bot
│   ├── main.py           # Discord bot entry point
│   ├── pyproject.toml    # Python project dependencies (for uv)
│   ├── uv.lock           # uv lock file for dependencies
│   ├── .python-version   # Python version specification
│   ├── README.md         # Discord bot documentation
│   └── __init__.py       # Package initialization
│
└── dashboard/            # React Web Dashboard
    ├── Dockerfile        # Docker configuration for dashboard
    ├── index.html        # HTML entry point
    ├── package.json      # Node.js dependencies
    └── src/              # React source code
        ├── components/   # Reusable components
        └── pages/        # Page components
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Discord Bot Token and Guild ID
- Git
- uv (Python package manager) - for local development

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ticketbot
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.template .env

# Edit .env file with your Discord configuration
# Required: DISCORD_BOT_TOKEN, DISCORD_GUILD_ID
```

### 3. Start Development Environment

```bash
# Make scripts executable
chmod +x start.sh stop.sh reset-db.sh

# Start all services
./start.sh

# The script will:
# - Build Docker containers
# - Start database and Redis
# - Run database migrations
# - Start all services
```

### 4. Access Services

- **Web Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Development Workflow

### Starting Development

```bash
./start.sh
```

This script will:
- Check for required configuration
- Build and start all Docker containers
- Run database migrations
- Display service URLs and helpful commands

### Local Development with uv

This project uses `uv` as the Python package manager for faster dependency resolution and virtual environment management.

#### Installing uv

```bash
# Install uv using pip
pip install uv

# Or on macOS with Homebrew
brew install uv
```

#### Setting up local development environment

```bash
# Backend service
cd backend
uv venv  # Create a virtual environment
uv pip install -e .  # Install the package in development mode

# Discord bot service
cd discord-bot
uv venv
uv pip install -e .
```

#### Running services locally

```bash
# Run backend service
cd backend
uv run python main.py

# Run Discord bot
cd discord-bot
uv run python main.py
```

### Stopping Development

```bash
# Stop services (keeps data)
./stop.sh

# Stop and clean up everything
./stop.sh --clean
```

### Database Management

```bash
# Reset database with sample data
./reset-db.sh

# Run migrations manually
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f discord-bot
docker-compose logs -f dashboard
```

### Running Tests

```bash
# Backend tests (in Docker)
docker-compose exec backend pytest

# Discord bot tests (in Docker)
docker-compose exec discord-bot pytest

# Frontend tests (in Docker)
docker-compose exec dashboard npm test

# Local development with uv (outside Docker)
cd backend
uv run python run_tests.py  # Run backend tests
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DISCORD_BOT_TOKEN` | Discord bot token | Yes | - |
| `DISCORD_GUILD_ID` | Discord server ID | Yes | - |
| `DATABASE_URL` | PostgreSQL connection string | No | Auto-configured |
| `REDIS_URL` | Redis connection string | No | Auto-configured |
| `JWT_SECRET_KEY` | JWT signing key | Yes | - |
| `API_KEY` | API authentication key | Yes | - |
| `DEBUG` | Enable debug mode | No | `true` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### Discord Bot Setup

1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot user and copy the token
3. Invite the bot to your server with appropriate permissions:
   - Manage Channels
   - Send Messages
   - Read Message History
   - Use Slash Commands
   - Manage Roles (for ticket permissions)

### Database Schema

The system uses PostgreSQL with the following main tables:
- `tickets`: Core ticket information
- `messages`: Ticket conversation messages
- `transcripts`: Generated conversation transcripts
- `staff`: Staff member information and permissions

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

### Key Endpoints

- `POST /api/tickets` - Create new ticket
- `GET /api/tickets` - List tickets with filtering
- `GET /api/tickets/{id}` - Get ticket details
- `PUT /api/tickets/{id}` - Update ticket
- `GET /api/tickets/{id}/transcript` - Get ticket transcript
- `GET /api/search/transcripts` - Search transcripts

## Discord Commands

- `/ticket create [subject]` - Create new support ticket
- `/ticket close` - Close current ticket
- `/ticket assign @user` - Assign ticket to staff member
- `/ticket transcript` - Generate ticket transcript

## Development Tips

### Hot Reloading

All services are configured with hot reloading:
- **Backend**: FastAPI auto-reloads on file changes
- **Discord Bot**: Restart required for changes
- **Dashboard**: Vite hot module replacement

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U ticketbot -d ticketbot

# Connect to Redis
docker-compose exec redis redis-cli
```

### Debugging

- Backend logs: `docker-compose logs -f backend`
- Discord bot logs: `docker-compose logs -f discord-bot`
- Database logs: `docker-compose logs -f postgres`

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Reset database
./reset-db.sh
```

**Discord Bot Not Responding**
- Check bot token in `.env`
- Verify bot permissions in Discord server
- Check logs: `docker-compose logs -f discord-bot`

**Port Already in Use**
```bash
# Stop all services and clean up
./stop.sh --clean
```

**Permission Denied on Scripts**
```bash
chmod +x start.sh stop.sh reset-db.sh
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

[MIT License](LICENSE)

## Support

For support and questions:
- Check the troubleshooting section above
- Review logs for error messages
- Create an issue in the repository