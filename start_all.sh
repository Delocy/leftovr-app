#!/bin/bash

# ============================================
# Start All Leftovr Services
# ============================================
# Starts MCP Server, FastAPI Backend, and React Frontend

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Starting Leftovr (Full Stack)${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Start backend in a new terminal window (macOS)
echo -e "${GREEN}Starting Backend...${NC}"
osascript -e 'tell application "Terminal" to do script "cd '"$SCRIPT_DIR"' && ./start_backend.sh"'

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Backend is ready!"
        break
    fi
    sleep 2
    echo -n "."
done
echo ""

# Start frontend in a new terminal window
echo -e "${GREEN}Starting Frontend...${NC}"
osascript -e 'tell application "Terminal" to do script "cd '"$SCRIPT_DIR/frontend"' && npm start"'

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   All Services Started!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "🚀 Application URLs:"
echo -e "   Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "   Backend:  ${BLUE}http://localhost:8000${NC}"
echo -e "   API Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "Run ${BLUE}./test_integration.sh${NC} to verify everything is working"
