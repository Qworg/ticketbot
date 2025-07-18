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

# Run migrations
echo "🔄 Running database migrations..."
docker-compose exec -T backend alembic upgrade head

# Insert sample data for development
echo "📝 Inserting sample data..."
docker-compose exec -T postgres psql -U ticketbot -d ticketbot -c "
INSERT INTO staff (id, discord_id, username, role, permissions, active) VALUES 
(gen_random_uuid(), 123456789012345678, 'admin_user', 'admin', '{\"manage_tickets\": true, \"manage_staff\": true}', true),
(gen_random_uuid(), 234567890123456789, 'support_user', 'support', '{\"manage_tickets\": true}', true);
"

# Restart services
echo "🚀 Restarting backend services..."
docker-compose up -d backend discord-bot

echo "✅ Database reset completed successfully!"
echo "👤 Sample staff users created:"
echo "   - Admin User (ID: 123456789012345678)"
echo "   - Support User (ID: 234567890123456789)"