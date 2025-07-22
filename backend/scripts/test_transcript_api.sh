#!/bin/bash
# Script for testing transcript API endpoints

# Set base URL
BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section header
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Function to make API requests and display results
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "${GREEN}$description${NC}"
    echo -e "Request: $method $endpoint"
    
    if [ -n "$data" ]; then
        echo -e "Data: $data"
        echo -e "Response:"
        curl -s -X $method "$BASE_URL$endpoint" -H "Content-Type: application/json" -d "$data" | json_pp
    else
        echo -e "Response:"
        curl -s -X $method "$BASE_URL$endpoint" | json_pp
    fi
    
    echo -e "\n"
}

# Check if ticket ID is provided
if [ -z "$1" ]; then
    echo -e "${RED}Please provide a ticket ID as the first argument${NC}"
    echo -e "Usage: $0 <ticket_id> [share_token]"
    exit 1
fi

TICKET_ID=$1
SHARE_TOKEN=$2

print_header "Testing Transcript API Endpoints"

# Get ticket transcript
print_header "1. Get Ticket Transcript"
make_request "GET" "/api/tickets/$TICKET_ID/transcript" "" "Get transcript for ticket $TICKET_ID"

# Generate share token
print_header "2. Generate Share Token"
make_request "POST" "/api/tickets/$TICKET_ID/transcript/share" "" "Generate share token for ticket $TICKET_ID"

# If share token is provided, test endpoints that require it
if [ -n "$SHARE_TOKEN" ]; then
    # Get transcript by share token
    print_header "3. Get Transcript by Share Token"
    make_request "GET" "/api/transcripts/shared/$SHARE_TOKEN" "" "Get transcript using share token"
    
    # Revoke share token
    print_header "4. Revoke Share Token"
    make_request "DELETE" "/api/tickets/$TICKET_ID/transcript/share" "" "Revoke share token for ticket $TICKET_ID"
fi

# Search transcripts
print_header "5. Search Transcripts"
make_request "GET" "/api/search/transcripts?search=test&page=1&size=10" "" "Search transcripts for 'test'"

# Search transcripts with fuzzy mode
print_header "6. Search Transcripts with Fuzzy Mode"
make_request "GET" "/api/search/transcripts?search=test&search_mode=fuzzy&page=1&size=10" "" "Search transcripts for 'test' with fuzzy mode"

echo -e "\n${GREEN}All tests completed!${NC}"