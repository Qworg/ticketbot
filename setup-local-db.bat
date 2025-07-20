@echo off
REM Discord Ticket Bot - Local Database Setup Script for Windows
REM This script sets up the local database for development

echo 🔄 Setting up Discord Ticket Bot Database...

REM Confirm with user
set /p CONFIRM="⚠️  This will reset your local database. Are you sure? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo ❌ Database setup cancelled.
    exit /b 1
)

REM Check if Docker is running
docker info > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Stop backend and discord-bot to avoid connection issues
echo 🛑 Stopping backend services...
docker-compose stop backend discord-bot

REM Drop and recreate database
echo 🗑️  Dropping database...
docker-compose exec -T postgres psql -U ticketbot -c "DROP DATABASE IF EXISTS ticketbot;"
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to drop database. Make sure PostgreSQL is running.
    exit /b 1
)

docker-compose exec -T postgres psql -U ticketbot -c "CREATE DATABASE ticketbot;"
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to create database. Make sure PostgreSQL is running.
    exit /b 1
)

REM Run migrations and create sample data
echo 🔄 Running database setup script...
docker-compose exec -T backend python -m scripts.setup_local_db
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to run setup script.
    exit /b 1
)

REM Restart services
echo 🚀 Restarting backend services...
docker-compose up -d backend discord-bot

echo ✅ Database setup completed successfully!
echo 👤 Sample data has been created with test tickets and users
echo 📊 You can now access the system and see the sample data