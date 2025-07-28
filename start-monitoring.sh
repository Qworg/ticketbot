#!/bin/bash

# Start monitoring stack for Discord Ticket Bot
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Discord Ticket Bot Monitoring Stack${NC}"

# Check if main application is running
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠ Main application doesn't appear to be running${NC}"
    echo -e "${YELLOW}  Consider starting it first with: ./start.sh${NC}"
    echo ""
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found, copying from template${NC}"
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo -e "${GREEN}✓ Created .env from template${NC}"
    fi
fi

# Create monitoring directories if they don't exist
echo -e "${YELLOW}Creating monitoring directories...${NC}"
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources

# Create Grafana datasource configuration
cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true

  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
    editable: true
EOF

# Create basic Grafana dashboard configuration
cat > monitoring/grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

echo -e "${YELLOW}Starting monitoring services...${NC}"

# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to start
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 15

# Check service health
echo -e "${YELLOW}Checking service health...${NC}"

services=("prometheus:9090" "grafana:3000" "alertmanager:9093" "loki:3100")
all_healthy=true

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -f -s --max-time 10 "http://localhost:$port" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name is healthy${NC}"
    else
        echo -e "${RED}✗ $name is not responding${NC}"
        all_healthy=false
    fi
done

echo ""

if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}✅ All monitoring services are running!${NC}"
else
    echo -e "${YELLOW}⚠ Some services may still be starting up${NC}"
fi

echo ""
echo -e "${BLUE}Monitoring Services:${NC}"
echo -e "  📊 Grafana:      http://localhost:3001 (admin/admin)"
echo -e "  📈 Prometheus:   http://localhost:9090"
echo -e "  🚨 AlertManager: http://localhost:9093"
echo -e "  📋 Loki:        http://localhost:3100"
echo -e "  🔍 Jaeger:      http://localhost:16686"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo -e "  docker-compose -f docker-compose.monitoring.yml logs -f [service-name]"
echo ""
echo -e "${YELLOW}To stop monitoring:${NC}"
echo -e "  docker-compose -f docker-compose.monitoring.yml down"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Access Grafana at http://localhost:3001"
echo -e "  2. Import dashboards for your services"
echo -e "  3. Configure alert notifications in AlertManager"
echo -e "  4. Set up log queries in Loki"