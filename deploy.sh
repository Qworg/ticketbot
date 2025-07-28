#!/bin/bash

# Deployment script for Discord Ticket Bot
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
COMPOSE_FILE="docker-compose.dev.yml"
ACTION="up"
BUILD=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            if [ "$ENVIRONMENT" = "production" ]; then
                COMPOSE_FILE="docker-compose.prod.yml"
            elif [ "$ENVIRONMENT" = "development" ]; then
                COMPOSE_FILE="docker-compose.dev.yml"
            else
                COMPOSE_FILE="docker-compose.yml"
            fi
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        --build)
            BUILD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --environment ENV    Set environment (development|production) [default: development]"
            echo "  -a, --action ACTION      Docker compose action (up|down|restart|logs) [default: up]"
            echo "  --build                  Build images before starting"
            echo "  -h, --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Start development environment"
            echo "  $0 -e production                     # Start production environment"
            echo "  $0 -a down                          # Stop services"
            echo "  $0 -a logs                          # Show logs"
            echo "  $0 --build                          # Build and start"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}Discord Ticket Bot Deployment${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Compose file: $COMPOSE_FILE${NC}"
echo -e "${YELLOW}Action: $ACTION${NC}"

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}✗ Compose file $COMPOSE_FILE not found${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found, copying from template${NC}"
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo -e "${GREEN}✓ Created .env from template${NC}"
        echo -e "${YELLOW}Please review and update .env file with your configuration${NC}"
    else
        echo -e "${RED}✗ .env.template not found${NC}"
        exit 1
    fi
fi

# Build images if requested
if [ "$BUILD" = true ]; then
    echo -e "${YELLOW}Building Docker images...${NC}"
    ./docker-build.sh -e "$ENVIRONMENT" --cache
fi

# Execute the requested action
case $ACTION in
    up)
        echo -e "${YELLOW}Starting services...${NC}"
        docker-compose -f "$COMPOSE_FILE" up -d
        
        echo -e "${GREEN}✓ Services started successfully${NC}"
        echo -e "${BLUE}Service URLs:${NC}"
        
        if [ "$ENVIRONMENT" = "production" ]; then
            echo "  - Dashboard: http://localhost"
            echo "  - API: http://localhost/api"
        else
            echo "  - Dashboard: http://localhost:3000"
            echo "  - API: http://localhost:8000"
            echo "  - PostgreSQL: localhost:5432"
            echo "  - Redis: localhost:6379"
        fi
        
        echo -e "${YELLOW}To view logs: docker-compose -f $COMPOSE_FILE logs -f${NC}"
        echo -e "${YELLOW}To stop services: $0 -e $ENVIRONMENT -a down${NC}"
        ;;
    down)
        echo -e "${YELLOW}Stopping services...${NC}"
        docker-compose -f "$COMPOSE_FILE" down
        echo -e "${GREEN}✓ Services stopped${NC}"
        ;;
    restart)
        echo -e "${YELLOW}Restarting services...${NC}"
        docker-compose -f "$COMPOSE_FILE" restart
        echo -e "${GREEN}✓ Services restarted${NC}"
        ;;
    logs)
        echo -e "${YELLOW}Showing logs...${NC}"
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
    ps)
        echo -e "${YELLOW}Service status:${NC}"
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
    *)
        echo -e "${RED}✗ Unknown action: $ACTION${NC}"
        echo "Available actions: up, down, restart, logs, ps"
        exit 1
        ;;
esac