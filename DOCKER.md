# Docker Deployment Guide

This document provides comprehensive information about deploying the Discord Ticket Bot using Docker containers.

## Overview

The Discord Ticket Bot uses a microservices architecture with the following components:

- **Backend API** (FastAPI) - REST API and WebSocket server
- **Discord Bot** (py-cord) - Discord integration service
- **Dashboard** (React + Vite) - Web management interface
- **PostgreSQL** - Primary database
- **Redis** - Caching and pub/sub messaging
- **Nginx** (Production) - Reverse proxy and load balancer

## Quick Start

### Development Environment

```bash
# Start development environment
./start.sh

# Or manually
./deploy.sh -e development --build
```

### Production Environment

```bash
# Build and deploy production
./deploy.sh -e production --build

# Or use docker-compose directly
docker-compose -f docker-compose.prod.yml up -d
```

## Docker Configurations

### Development (docker-compose.dev.yml)

- **Hot reloading** enabled for all services
- **Volume mounts** for source code
- **Debug ports** exposed
- **Development database** with sample data

Services:
- Backend: http://localhost:8000
- Dashboard: http://localhost:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Production (docker-compose.prod.yml)

- **Multi-stage builds** for optimized images
- **Health checks** for all services
- **Resource limits** configured
- **Nginx reverse proxy** with SSL support
- **Service scaling** configured

Services:
- All services: http://localhost (via Nginx)
- Internal services not exposed

## Docker Images

### Multi-Stage Builds

All services use multi-stage Docker builds for optimization:

1. **Builder stage**: Install dependencies and build artifacts
2. **Production stage**: Copy only necessary files for runtime

### Image Optimization

- **Alpine Linux** base images where possible
- **Non-root users** for security
- **Layer caching** optimization
- **.dockerignore** files to reduce build context

## Scripts

### Build Script (docker-build.sh)

```bash
# Build all images for development
./docker-build.sh -e development

# Build for production with cache
./docker-build.sh -e production --cache

# Build and push to registry
./docker-build.sh -e production --registry your-registry.com --push
```

Options:
- `-e, --environment`: Set environment (development|production)
- `--cache`: Use Docker build cache
- `--push`: Push images to registry
- `--registry`: Docker registry URL

### Deployment Script (deploy.sh)

```bash
# Start development environment
./deploy.sh

# Start production environment
./deploy.sh -e production

# Stop services
./deploy.sh -a down

# View logs
./deploy.sh -a logs
```

Options:
- `-e, --environment`: Set environment
- `-a, --action`: Docker compose action (up|down|restart|logs)
- `--build`: Build images before starting

### Health Check Script (health-check.sh)

```bash
# Check development environment
./health-check.sh

# Check production environment
./health-check.sh -e production

# Custom timeout
./health-check.sh -t 60
```

## Environment Configuration

### Environment Variables

Create a `.env` file based on `.env.template`:

```bash
# Database
POSTGRES_DB=ticketbot
POSTGRES_USER=ticketbot
POSTGRES_PASSWORD=your_secure_password

# Discord
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_guild_id

# API
JWT_SECRET_KEY=your_jwt_secret
API_KEY=your_api_key

# Redis
REDIS_URL=redis://redis:6379

# Frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

### Production Environment Variables

Additional variables for production:

```bash
# Environment
ENVIRONMENT=production

# Ports
BACKEND_PORT=8000
DASHBOARD_PORT=3000
POSTGRES_PORT=5432
REDIS_PORT=6379

# SSL (if using HTTPS)
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

## Health Checks

All services include health checks:

### Backend API
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

### Discord Bot
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "python.*main.py" || exit 1
```

### Dashboard (Production)
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1
```

### Database Services
- **PostgreSQL**: `pg_isready` command
- **Redis**: `redis-cli ping` command

## Networking

### Development
- **Bridge network** with port mapping
- **Direct access** to all services
- **Host networking** for debugging

### Production
- **Internal networks** for security
- **Frontend network**: Dashboard, Nginx, Backend
- **Backend network**: Backend, Discord Bot, Database, Redis
- **No direct external access** to internal services

## Volumes

### Persistent Data
- `postgres_data`: Database files
- `redis_data`: Redis persistence

### Development Mounts
- Source code directories mounted for hot reloading
- Node modules excluded via anonymous volumes

## Security

### Container Security
- **Non-root users** in all containers
- **Read-only root filesystems** where possible
- **Security headers** in Nginx configuration
- **Resource limits** to prevent DoS

### Network Security
- **Internal networks** for service communication
- **Firewall rules** via Docker networks
- **SSL/TLS termination** at Nginx
- **Rate limiting** for API endpoints

## Monitoring and Logging

### Logging Configuration
- **Structured logging** with JSON format
- **Log rotation** configured
- **Centralized logging** via Docker logging drivers

### Monitoring
- **Health check endpoints** for all services
- **Metrics collection** ready for Prometheus
- **Container resource monitoring**

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check service status
   docker-compose ps
   
   # View logs
   docker-compose logs [service-name]
   ```

2. **Database connection issues**
   ```bash
   # Check database health
   docker-compose exec postgres pg_isready -U ticketbot
   
   # Reset database
   ./reset-db.sh
   ```

3. **Port conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :8000
   
   # Use different ports in .env
   BACKEND_PORT=8001
   ```

4. **Build failures**
   ```bash
   # Clean build cache
   docker builder prune
   
   # Rebuild without cache
   ./docker-build.sh --no-cache
   ```

### Debug Mode

Enable debug mode for development:

```bash
# Set debug environment variables
export DEBUG=true
export LOG_LEVEL=debug

# Start with debug logging
./deploy.sh -e development
```

### Performance Tuning

For production deployments:

1. **Resource Limits**: Adjust CPU and memory limits in docker-compose.prod.yml
2. **Database Tuning**: Configure PostgreSQL settings for your workload
3. **Redis Configuration**: Optimize Redis memory and persistence settings
4. **Nginx Tuning**: Adjust worker processes and connection limits

## Backup and Recovery

### Database Backup
```bash
# Create backup
docker-compose exec postgres pg_dump -U ticketbot ticketbot > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U ticketbot ticketbot < backup.sql
```

### Volume Backup
```bash
# Backup volumes
docker run --rm -v ticketbot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Scaling

### Horizontal Scaling
The production configuration supports scaling:

```bash
# Scale backend service
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Scale dashboard service
docker-compose -f docker-compose.prod.yml up -d --scale dashboard=2
```

### Load Balancing
Nginx is configured for load balancing across multiple instances of services.

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and Deploy
        run: |
          ./docker-build.sh -e production --registry ${{ secrets.REGISTRY }}
          ./deploy.sh -e production
```

## Support

For issues related to Docker deployment:

1. Check the health check script output
2. Review service logs
3. Verify environment configuration
4. Check Docker and Docker Compose versions
5. Consult the troubleshooting section above