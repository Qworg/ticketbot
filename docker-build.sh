#!/bin/bash

# Docker build script for Discord Ticket Bot
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
BUILD_CACHE="--no-cache"
PUSH_IMAGES=false
REGISTRY=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --cache)
            BUILD_CACHE=""
            shift
            ;;
        --push)
            PUSH_IMAGES=true
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --environment ENV    Set environment (development|production) [default: development]"
            echo "  --cache                  Use Docker build cache"
            echo "  --push                   Push images to registry"
            echo "  --registry REGISTRY      Docker registry URL"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Building Discord Ticket Bot Docker images...${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"

# Set image tags
if [ -n "$REGISTRY" ]; then
    BACKEND_TAG="$REGISTRY/ticketbot-backend:$ENVIRONMENT"
    DISCORD_BOT_TAG="$REGISTRY/ticketbot-discord-bot:$ENVIRONMENT"
    DASHBOARD_TAG="$REGISTRY/ticketbot-dashboard:$ENVIRONMENT"
else
    BACKEND_TAG="ticketbot-backend:$ENVIRONMENT"
    DISCORD_BOT_TAG="ticketbot-discord-bot:$ENVIRONMENT"
    DASHBOARD_TAG="ticketbot-dashboard:$ENVIRONMENT"
fi

# Build backend
echo -e "${YELLOW}Building backend service...${NC}"
docker build $BUILD_CACHE \
    --target production \
    -t "$BACKEND_TAG" \
    ./backend

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backend build successful${NC}"
else
    echo -e "${RED}✗ Backend build failed${NC}"
    exit 1
fi

# Build Discord bot
echo -e "${YELLOW}Building Discord bot service...${NC}"
docker build $BUILD_CACHE \
    --target production \
    -t "$DISCORD_BOT_TAG" \
    ./discord-bot

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Discord bot build successful${NC}"
else
    echo -e "${RED}✗ Discord bot build failed${NC}"
    exit 1
fi

# Build dashboard
echo -e "${YELLOW}Building dashboard service...${NC}"
TARGET="production"
if [ "$ENVIRONMENT" = "development" ]; then
    TARGET="development"
fi

docker build $BUILD_CACHE \
    --target "$TARGET" \
    -t "$DASHBOARD_TAG" \
    ./dashboard

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dashboard build successful${NC}"
else
    echo -e "${RED}✗ Dashboard build failed${NC}"
    exit 1
fi

# Push images if requested
if [ "$PUSH_IMAGES" = true ]; then
    if [ -z "$REGISTRY" ]; then
        echo -e "${RED}✗ Registry URL required for pushing images${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Pushing images to registry...${NC}"
    
    docker push "$BACKEND_TAG"
    docker push "$DISCORD_BOT_TAG"
    docker push "$DASHBOARD_TAG"
    
    echo -e "${GREEN}✓ Images pushed successfully${NC}"
fi

echo -e "${GREEN}All builds completed successfully!${NC}"
echo -e "${YELLOW}Built images:${NC}"
echo "  - $BACKEND_TAG"
echo "  - $DISCORD_BOT_TAG"
echo "  - $DASHBOARD_TAG"

# Show next steps
echo -e "${YELLOW}Next steps:${NC}"
if [ "$ENVIRONMENT" = "development" ]; then
    echo "  Run: docker-compose -f docker-compose.dev.yml up"
else
    echo "  Run: docker-compose -f docker-compose.prod.yml up"
fi