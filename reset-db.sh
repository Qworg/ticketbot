#!/bin/bash

# Discord Ticket Bot - Database Reset Script
# This script resets the database and runs migrations

set -e

echo "🔄 Resetting Discord Ticket Bot Database..."

# Confirm with user
read -p "⚠️  This will delete ALL data in the database. Are you sure? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Database reset cancelled."
    exit 1
fi

# Stop backend and discord-bot to avoid connection issues
echo "🛑 Stopping backend services..."
docker-compose stop backend discord-bot

# Drop and recreate database
echo "🗑️  Dropping database..."
docker-compose exec -T postgres psql -U ticketbot -c "DROP DATABASE IF EXISTS ticketbot;"
docker-compose exec -T postgres psql -U ticketbot -c "CREATE DATABASE ticketbot;"

# Run migrations and create sample data
echo "🔄 Running database setup script..."
docker-compose exec -T backend python -m scripts.setup_local_db

# Restart services
echo "🚀 Restarting backend services..."
docker-compose up -d backend discord-bot

echo "✅ Database reset completed successfully!"
echo "👤 Sample data has been created with test tickets and users"
echo "📊 You can now access the system and see the sample data"