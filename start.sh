#!/bin/bash

# Discord Ticket Bot - Development Start Script
# This script starts all services for local development

set -e

echo "🚀 Starting Discord Ticket Bot Development Environment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    if [ -f .env.template ]; then
        cp .env.template .env
        echo "📝 Please edit .env file with your configuration before continuing."
        echo "   Required: DISCORD_BOT_TOKEN, DISCORD_GUILD_ID"
        exit 1
    else
        echo "❌ .env.template not found. Please create .env file manually."
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Use the deployment script for development
echo "🔨 Building and starting services..."
./deploy.sh -e development --build

echo "⏳ Waiting for services to be ready..."
sleep 10

# Run health check
echo "🏥 Running health checks..."
./health-check.sh -e development

echo "✅ Development environment started successfully!"
echo ""
echo "📋 Service URLs:"
echo "   🌐 Web Dashboard: http://localhost:3000"
echo "   🔌 Backend API:   http://localhost:8000"
echo "   📚 API Docs:      http://localhost:8000/docs"
echo "   🗄️  Database:      localhost:5432"
echo "   🔴 Redis:         localhost:6379"
echo ""
echo "📊 To view logs: docker-compose -f docker-compose.dev.yml logs -f [service_name]"
echo "🛑 To stop:      ./stop.sh"
echo "🔄 To reset DB:  ./reset-db.sh"