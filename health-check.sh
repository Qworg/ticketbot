#!/bin/bash

# Health check script for Discord Ticket Bot services
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
TIMEOUT=30

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --environment ENV    Set environment (development|production) [default: development]"
            echo "  -t, --timeout SECONDS    Timeout for health checks [default: 30]"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}Discord Ticket Bot Health Check${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Timeout: ${TIMEOUT}s${NC}"
echo ""

# Set URLs based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    BACKEND_URL="http://localhost/api/health"
    DASHBOARD_URL="http://localhost/"
    POSTGRES_HOST="localhost"
    REDIS_HOST="localhost"
else
    BACKEND_URL="http://localhost:8000/health"
    DASHBOARD_URL="http://localhost:3000/"
    POSTGRES_HOST="localhost"
    REDIS_HOST="localhost"
fi

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local service_name=$2
    
    echo -n "Checking $service_name... "
    
    if curl -f -s --max-time "$TIMEOUT" "$url" > /dev/null; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

# Function to check database connection
check_postgres() {
    echo -n "Checking PostgreSQL... "
    
    if command -v pg_isready > /dev/null; then
        if pg_isready -h "$POSTGRES_HOST" -p 5432 -t "$TIMEOUT" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Healthy${NC}"
            return 0
        else
            echo -e "${RED}✗ Unhealthy${NC}"
            return 1
        fi
    else
        # Fallback: try to connect with docker
        if docker exec -it $(docker ps -q -f name=postgres) pg_isready > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Healthy${NC}"
            return 0
        else
            echo -e "${RED}✗ Unhealthy (pg_isready not available)${NC}"
            return 1
        fi
    fi
}

# Function to check Redis connection
check_redis() {
    echo -n "Checking Redis... "
    
    if command -v redis-cli > /dev/null; then
        if timeout "$TIMEOUT" redis-cli -h "$REDIS_HOST" -p 6379 ping > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Healthy${NC}"
            return 0
        else
            echo -e "${RED}✗ Unhealthy${NC}"
            return 1
        fi
    else
        # Fallback: try to connect with docker
        if docker exec -it $(docker ps -q -f name=redis) redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Healthy${NC}"
            return 0
        else
            echo -e "${RED}✗ Unhealthy (redis-cli not available)${NC}"
            return 1
        fi
    fi
}

# Function to check Docker container status
check_container() {
    local container_name=$1
    local service_name=$2
    
    echo -n "Checking $service_name container... "
    
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*Up"; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Perform health checks
echo -e "${YELLOW}Checking service health...${NC}"

FAILED_CHECKS=0

# Check containers
check_container "postgres" "PostgreSQL" || ((FAILED_CHECKS++))
check_container "redis" "Redis" || ((FAILED_CHECKS++))
check_container "backend" "Backend API" || ((FAILED_CHECKS++))
check_container "discord-bot" "Discord Bot" || ((FAILED_CHECKS++))
check_container "dashboard" "Dashboard" || ((FAILED_CHECKS++))

echo ""

# Check service endpoints
echo -e "${YELLOW}Checking service endpoints...${NC}"

check_postgres || ((FAILED_CHECKS++))
check_redis || ((FAILED_CHECKS++))
check_http "$BACKEND_URL" "Backend API" || ((FAILED_CHECKS++))
check_http "$DASHBOARD_URL" "Dashboard" || ((FAILED_CHECKS++))

echo ""

# Summary
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}✓ All health checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ $FAILED_CHECKS health check(s) failed${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "  - Check if all services are running: docker-compose ps"
    echo "  - View service logs: docker-compose logs [service-name]"
    echo "  - Restart services: docker-compose restart"
    echo "  - Check environment variables in .env file"
    exit 1
fi