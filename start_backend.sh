#!/bin/bash

# ============================================
# Leftovr Backend Startup Script
# ============================================
# This script starts both the MCP server and FastAPI server
# in the correct order with proper error handling

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Leftovr Backend Startup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if Python 3.11 is available
if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}❌ Python 3.11 not found!${NC}"
    echo "Please install Python 3.11 first:"
    echo "  brew install python@3.11"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python 3.11 found"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠ Virtual environment not found. Creating...${NC}"
    python3.11 -m venv .venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Check if dependencies are installed
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! .venv/bin/pip list | grep -q fastapi; then
    echo -e "${YELLOW}⚠ Installing dependencies...${NC}"
    .venv/bin/pip install -q -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${GREEN}✓${NC} Dependencies already installed"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create a .env file with your API keys:"
    echo "  OPENAI_API_KEY=your_key_here"
    echo "  ZILLIZ_CLUSTER_ENDPOINT=your_endpoint"
    echo "  ZILLIZ_TOKEN=your_token"
    exit 1
fi

echo -e "${GREEN}✓${NC} Environment file found"
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    # if [ ! -z "$MCP_PID" ]; then
    #     kill $MCP_PID 2>/dev/null || true
    #     echo -e "${GREEN}✓${NC} MCP Server stopped"
    # fi
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
        echo -e "${GREEN}✓${NC} FastAPI Server stopped"
    fi
    exit 0
}

# Set up trap for cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# MCP Server temporarily disabled
echo -e "${YELLOW}ℹ️  MCP Server temporarily disabled (using direct DB access)${NC}"
echo ""

# Start FastAPI Server
echo -e "${BLUE}Starting FastAPI Server...${NC}"
.venv/bin/python api/server.py > logs/api_server.log 2>&1 &
API_PID=$!
sleep 3

if ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}✓${NC} FastAPI Server running (PID: $API_PID)"
else
    echo -e "${RED}❌ FastAPI Server failed to start${NC}"
    echo "Check logs/api_server.log for details"
    # kill $MCP_PID 2>/dev/null || true
    exit 1
fi

# Test the health endpoint
echo ""
echo -e "${YELLOW}Testing health endpoint...${NC}"
sleep 2
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is healthy and ready!"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Check logs/api_server.log for details"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Backend Started Successfully!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "📊 Server URLs:"
echo -e "   FastAPI: ${BLUE}http://localhost:8000${NC}"
echo -e "   Docs:    ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "📝 Logs:"
echo -e "   API:     tail -f logs/api_server.log"
echo ""
echo -e "Press ${RED}Ctrl+C${NC} to stop all servers"
echo ""

# Keep script running and tail logs
tail -f logs/api_server.log
