#!/bin/bash

# Discord Ticket Bot - Development Stop Script
# This script stops all services and optionally cleans up

set -e

echo "🛑 Stopping Discord Ticket Bot Development Environment..."

# Stop all services
docker-compose down

# Check if user wants to remove volumes
if [ "$1" = "--clean" ] || [ "$1" = "-c" ]; then
    echo "🧹 Cleaning up volumes and networks..."
    docker-compose down -v --remove-orphans
    docker system prune -f
    echo "✅ Environment stopped and cleaned up!"
else
    echo "✅ Environment stopped!"
    echo "💡 Use './stop.sh --clean' to also remove volumes and free up space"
fi