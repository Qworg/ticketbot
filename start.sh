#!/bin/bash

# Discord Ticket Bot - Development Start Script
# This script starts all services for local development

set -e

echo "🚀 Starting Discord Ticket Bot Development Environment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.template .env
    echo "📝 Please edit .env file with your configuration before continuing."
    echo "   Required: DISCORD_BOT_TOKEN, DISCORD_GUILD_ID"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build and start services
echo "🔨 Building Docker containers..."
docker-compose build

echo "🗄️  Starting database and Redis..."
docker-compose up -d postgres redis

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
timeout=30
while ! docker-compose exec -T postgres pg_isready -U ticketbot > /dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [ $timeout -eq 0 ]; then
        echo "❌ Database failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

echo "🔄 Running database migrations..."
docker-compose exec -T backend alembic upgrade head

echo "🎯 Starting all services..."
docker-compose up -d

echo "✅ Development environment started successfully!"
echo ""
echo "📋 Service URLs:"
echo "   🌐 Web Dashboard: http://localhost:3000"
echo "   🔌 Backend API:   http://localhost:8000"
echo "   📚 API Docs:      http://localhost:8000/docs"
echo "   🗄️  Database:      localhost:5432"
echo "   🔴 Redis:         localhost:6379"
echo ""
echo "📊 To view logs: docker-compose logs -f [service_name]"
echo "🛑 To stop:      ./stop.sh"
echo "🔄 To reset DB:  ./reset-db.sh"