# 🚀 Leftovr Startup Guide

This guide will help you start the Leftovr application with all its components.

## Quick Start

### Option 1: Start Everything at Once (Recommended)
```bash
./start_all.sh
```
This will open new terminal windows for:
- Backend (MCP Server + FastAPI)
- Frontend (React)

### Option 2: Start Components Individually

#### Start Backend Only
```bash
./start_backend.sh
```
This starts both:
- MCP Server (pantry database)
- FastAPI Server (port 8000)

Press `Ctrl+C` to stop both servers.

#### Start Frontend Only
```bash
cd frontend
npm start
```
Opens React app at http://localhost:3000

## Testing the Integration

After starting the backend, run:
```bash
./test_integration.sh
```

This will test:
- ✅ Health check
- ✅ Pantry operations (add/get/delete)
- ✅ Chat with AI agents
- ✅ Recipe search

## Application URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Logs

View logs in real-time:
```bash
# API Server logs
tail -f logs/api_server.log

# MCP Server logs
tail -f logs/mcp_server.log
```

## Architecture

```
┌─────────────────────────────────────┐
│   React Frontend (Port 3000)        │
│   - Chat Interface                  │
│   - Pantry Management               │
│   - Recipe Search                   │
└────────────┬────────────────────────┘
             │ HTTP Requests
             ↓
┌─────────────────────────────────────┐
│   FastAPI Server (Port 8000)        │
│   - /chat                           │
│   - /pantry/*                       │
│   - /recipes/search                 │
└────────────┬────────────────────────┘
             │ Invokes
             ↓
┌─────────────────────────────────────┐
│   LeftovrWorkflow (LangGraph)       │
│   ├─ ExecutiveChefAgent             │
│   ├─ PantryAgent ────────┐          │
│   ├─ RecipeKnowledgeAgent│          │
│   └─ SousChefAgent       │          │
└──────────────────────────┼──────────┘
                           │ JSON-RPC
                           ↓
┌─────────────────────────────────────┐
│   MCP Server                        │
│   └─ SQLite Database (pantry.db)   │
└─────────────────────────────────────┘
```

## Features Connected

### ✅ Chat Interface
- AI-powered recipe recommendations
- Multi-turn conversations
- Context-aware responses
- Ingredient-based suggestions

### ✅ Pantry Management
- Add ingredients with expiration dates
- Update quantities
- Delete items
- View inventory
- Expiration warnings

### ✅ Recipe Search
- Hybrid search (semantic + keyword)
- Ingredient matching
- Dietary preferences
- Match percentage calculation

## Troubleshooting

### Backend won't start
1. Check if Python 3.11 is installed: `python3.11 --version`
2. Check logs: `cat logs/api_server.log`
3. Ensure .env file exists with required keys:
   ```
   OPENAI_API_KEY=your_key
   ZILLIZ_CLUSTER_ENDPOINT=your_endpoint
   ZILLIZ_TOKEN=your_token
   ```

### Frontend can't connect to backend
1. Check if backend is running: `curl http://localhost:8000/health`
2. Check CORS configuration in `api/server.py`
3. Verify proxy in `frontend/package.json` is set to "http://localhost:8000"

### MCP Server issues
1. Check if pantry.db exists: `ls -la database/`
2. View MCP logs: `cat logs/mcp_server.log`
3. Restart backend: `./start_backend.sh`

## Development

### Hot Reload
- Frontend: Changes auto-reload with `npm start`
- Backend: Restart `./start_backend.sh` after code changes

### Adding Dependencies
```bash
# Backend
source api/venv/bin/activate
pip install package_name
pip freeze > requirements.txt

# Frontend
cd frontend
npm install package_name
```

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run integration tests: `./test_integration.sh`
3. Review API docs: http://localhost:8000/docs
