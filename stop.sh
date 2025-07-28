#!/bin/bash

# Discord Ticket Bot - Development Stop Script
# This script stops all services and optionally cleans up

set -e

echo "🛑 Stopping Discord Ticket Bot Development Environment..."

# Determine which compose file to use
COMPOSE_FILE="docker-compose.dev.yml"
if [ "$1" = "--production" ] || [ "$1" = "-p" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    shift
fi

# Stop all services
docker-compose -f "$COMPOSE_FILE" down

# Check if user wants to remove volumes
if [ "$1" = "--clean" ] || [ "$1" = "-c" ]; then
    echo "🧹 Cleaning up volumes and networks..."
    docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
    
    # Clean up unused Docker resources
    echo "🧹 Cleaning up unused Docker resources..."
    docker system prune -f
    
    # Remove unused images
    if [ "$2" = "--images" ]; then
        echo "🧹 Removing unused images..."
        docker image prune -a -f
    fi
    
    echo "✅ Environment stopped and cleaned up!"
else
    echo "✅ Environment stopped!"
    echo "💡 Use './stop.sh --clean' to also remove volumes and free up space"
    echo "💡 Use './stop.sh --clean --images' to also remove unused images"
    echo "💡 Use './stop.sh --production' to stop production environment"
fi