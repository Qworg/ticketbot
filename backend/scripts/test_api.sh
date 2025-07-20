#!/bin/bash
# Script for testing the Discord Ticket Bot API endpoints

# Set the base URL
BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Discord Ticket Bot API Testing Script${NC}"
echo "=================================="
echo ""

# Function to make API requests and display results
function make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "${BLUE}Testing:${NC} $description"
    echo -e "${BLUE}$method${NC} $endpoint"
    
    if [ -n "$data" ]; then
        echo -e "${BLUE}Request:${NC}"
        echo "$data" | jq '.'
        
        response=$(curl -s -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -X $method "$BASE_URL$endpoint")
    fi
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint" ${data:+-H "Content-Type: application/json" -d "$data"})
    
    echo -e "${BLUE}Response:${NC} HTTP $http_code"
    echo "$response" | jq '.'
    echo "=================================="
}

# Check if the API is running
echo -e "${BLUE}Checking if API is running...${NC}"
health_response=$(curl -s "$BASE_URL/health")
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: API is not running at $BASE_URL${NC}"
    echo "Please start the API server and try again."
    exit 1
fi

echo -e "${GREEN}API is running!${NC}"
echo "$health_response" | jq '.'
echo "=================================="

# Test 1: Create a new ticket
echo -e "${BLUE}Test 1: Create a new ticket${NC}"
ticket_data='{
    "title": "Test Ticket",
    "description": "This is a test ticket created via API",
    "priority": "medium",
    "creator_discord_id": 123456789,
    "discord_channel_id": 987654321
}'
make_request "POST" "/api/tickets" "$ticket_data" "Create a new ticket"

# Store the ticket ID for later use
ticket_id=$(echo "$response" | jq -r '.id')

# Test 2: Get all tickets with pagination
echo -e "${BLUE}Test 2: Get all tickets with pagination${NC}"
make_request "GET" "/api/tickets?page=1&size=10" "" "Get all tickets (page 1, size 10)"

# Test 3: Get tickets with filters
echo -e "${BLUE}Test 3: Get tickets with filters${NC}"
make_request "GET" "/api/tickets?status=open&priority=medium" "" "Get tickets filtered by status and priority"

# Test 4: Get a specific ticket by ID
echo -e "${BLUE}Test 4: Get a specific ticket by ID${NC}"
if [ -n "$ticket_id" ] && [ "$ticket_id" != "null" ]; then
    make_request "GET" "/api/tickets/$ticket_id" "" "Get ticket by ID"
else
    echo -e "${RED}No ticket ID available from previous test${NC}"
fi

echo -e "${GREEN}API testing completed!${NC}"
echo ""
echo "For more examples, you can use these curl commands:"
echo ""
echo "# Create a ticket"
echo 'curl -X POST "http://localhost:8000/api/tickets" -H "Content-Type: application/json" -d "{\\"title\\": \\"New Ticket\\", \\"description\\": \\"Ticket description\\", \\"priority\\": \\"high\\", \\"creator_discord_id\\": 123456789, \\"discord_channel_id\\": 987654321}"'
echo ""
echo "# Get tickets with pagination and filtering"
echo 'curl -X GET "http://localhost:8000/api/tickets?page=1&size=10&status=open&priority=high&search=help"'
echo ""
echo "# Get a specific ticket"
echo 'curl -X GET "http://localhost:8000/api/tickets/YOUR_TICKET_ID"'
echo ""