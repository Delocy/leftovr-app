# Leftovr Project Analysis & Architecture Review

## Executive Summary
This document provides a comprehensive analysis of the Leftovr application architecture, identifying issues, and providing recommendations for a clean React + Flask + LangGraph setup.

## Current Architecture

### ✅ WHAT'S CORRECT

#### 1. **Backend Structure (Well Designed)**
```
Backend: FastAPI (api/server.py) ← Should be Flask based on your requirement
Main Logic: LangGraph Workflow (main.py)
Agents: Specialized agents for different tasks
Database: MCP Server + SQLite for pantry management
Vector DB: Milvus for recipe search
```

**Key Components:**
- `api/server.py` - FastAPI server with proper CORS, endpoints for chat, pantry, recipes
- `main.py` - LangGraph workflow orchestrating 4 specialized agents
- `agents/` - Modular agent system (Executive Chef, Pantry, Sous Chef, Recipe Knowledge)
- `mcp/server.py` - Model Context Protocol server for pantry operations
- `database/pantry_storage.py` - SQLite database layer

#### 2. **Agent Workflow (Excellent Design)**
The LangGraph workflow is well-architected:
- **ExecutiveChefAgent**: Orchestrator that classifies queries and routes to appropriate agents
- **PantryAgent**: MCP client for pantry operations (add/remove/update ingredients)
- **SousChefAgent**: Recipe recommendation and adaptation
- **RecipeKnowledgeAgent**: Vector search using Milvus

**Workflow Flow:**
1. User message → Orchestrator (classify)
2. Route to: Pantry | Recipe Search | General Response
3. Recipe Search → Recommendation (Top 3) → Customization
4. Returns formatted response

#### 3. **API Endpoints (Complete)**
```python
GET  /              - Health check
GET  /health        - Detailed health check
POST /chat          - Main chat interface
GET  /pantry/inventory
POST /pantry/add
PUT  /pantry/update/{item_name}
DELETE /pantry/delete/{item_name}
POST /recipes/search
```

### ❌ CRITICAL ISSUES

#### 1. **Frontend is INCOMPLETE**
**Problem:**
```
frontend/src/
├── components/
│   └── Navbar.js (EMPTY)
├── pages/
│   ├── PantryManagement.js (EMPTY)
│   ├── RecipeSearch.js (EMPTY)
│   └── ChatInterface.js.backup (exists but not being used)
└── services/ (EMPTY - no API integration)
```

**What's Missing:**
- ❌ No `App.js` or main entry point
- ❌ No `package.json` with dependencies
- ❌ No API service layer to connect to backend
- ❌ Components are empty files
- ❌ No routing setup (React Router)
- ❌ Build was generated but source is missing

#### 2. **Backend Mismatch**
**Issue:** You requested Flask, but the implementation uses FastAPI.

**Current:**
```python
# api/server.py
from fastapi import FastAPI, HTTPException
app = FastAPI()
```

**Should be:**
```python
# api/server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
```

#### 3. **Unused Dependencies**
`requirements.txt` has 99 packages including:
- ❌ `streamlit==1.50.0` - Not used (comment says "Streamlit = Frontend" but using React)
- ❌ `qdrant-client==1.15.1` - Not used (using Milvus)
- ❌ Many transitive dependencies not needed

**Cleaned to 20+ essential packages only.**

#### 4. **Redundant Files**
- ✅ Removed: `scripts/ingest_recipes_pinecone.py` (using Milvus)
- ✅ Removed: `scripts/ingest_recipes_qdrant.py` (using Milvus)
- ✅ Removed: `frontend/build/` (should be regenerated)
- ✅ Removed: `__pycache__` directories
- ✅ Removed: `ChatInterface.js.backup`

## Architecture Flow (Current State)

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                        │
│                   ❌ NOT IMPLEMENTED                         │
│  Should have:                                               │
│  - App.js with routing                                      │
│  - ChatInterface, PantryManagement, RecipeSearch pages      │
│  - API service layer (axios/fetch)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP (localhost:8000)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI/Flask)                    │
│                    api/server.py                            │
│  ✅ Endpoints: /chat, /pantry/*, /recipes/search            │
│  ✅ CORS configured for React (port 3000)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ calls
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              LANGGRAPH WORKFLOW (main.py)                   │
│  ✅ Orchestrates 4 specialized agents                       │
│  ✅ State management with RecipeWorkflowState               │
│  ✅ Conditional routing based on query type                 │
└─────────────────────────────────────────────────────────────┘
          │                   │                    │
          │                   │                    │
   ┌──────▼─────┐    ┌───────▼────────┐   ┌──────▼─────────┐
   │  Pantry    │    │  Sous Chef     │   │  Recipe        │
   │  Agent     │    │  Agent         │   │  Knowledge     │
   │  (MCP)     │    │  (LLM)         │   │  Agent         │
   └──────┬─────┘    └────────────────┘   └──────┬─────────┘
          │                                        │
          │ JSON-RPC                               │
          ↓                                        ↓
   ┌────────────────┐                    ┌──────────────────┐
   │  MCP Server    │                    │  Milvus Cloud    │
   │  (stdio)       │                    │  (Vector Search) │
   └───────┬────────┘                    └──────────────────┘
           │
           ↓
   ┌────────────────┐
   │  SQLite DB     │
   │  (Pantry)      │
   └────────────────┘
```

## Recommendations

### 1. **Fix Frontend** (HIGH PRIORITY)
You need to create a proper React app. Options:

**Option A: Create from scratch**
```bash
cd frontend
npm init -y
npm install react react-dom react-router-dom axios @mui/material @emotion/react @emotion/styled
```

**Option B: Use Create React App**
```bash
rm -rf frontend
npx create-react-app frontend
cd frontend
npm install react-router-dom axios @mui/material @emotion/react @emotion/styled
```

Then implement:
1. `src/App.js` - Main app with routing
2. `src/services/api.js` - API calls to backend
3. `src/pages/ChatInterface.js` - Chat UI
4. `src/pages/PantryManagement.js` - Pantry CRUD
5. `src/pages/RecipeSearch.js` - Recipe search UI

### 2. **Convert FastAPI to Flask** (if required)
If you specifically need Flask:

```python
# api/server.py (Flask version)
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    workflow = get_workflow()
    result = workflow.invoke({
        "user_message": data["user_message"],
        "user_preferences": data.get("user_preferences", {}),
        "pantry_inventory": data.get("pantry_inventory", [])
    })
    return jsonify({
        "response": result.get("response"),
        "pantry_inventory": result.get("pantry_inventory"),
        "top_3_recommendations": result.get("top_3_recommendations")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

**Update requirements.txt:**
```
flask==3.0.0
flask-cors==4.0.0
```

### 3. **Environment Setup**
Create `.env` file:
```env
# OpenAI
OPENAI_API_KEY=your_key_here

# Milvus/Zilliz
ZILLIZ_CLUSTER_ENDPOINT=your_endpoint
ZILLIZ_TOKEN=your_token

# LangSmith (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key
LANGCHAIN_PROJECT=leftovr-app
```

### 4. **Running the Application**

**Backend:**
```bash
# Terminal 1: Start MCP Server (pantry operations)
python mcp/server.py

# Terminal 2: Start FastAPI/Flask server
python api/server.py
# OR
uvicorn api.server:app --reload --port 8000
```

**Frontend:**
```bash
# Terminal 3: Start React dev server
cd frontend
npm start
```

## File Structure (After Cleanup)

```
leftovr-app/
├── api/
│   └── server.py          ✅ FastAPI server (or Flask)
├── agents/
│   ├── executive_chef_agent.py   ✅ Orchestrator
│   ├── pantry_agent.py           ✅ MCP client
│   ├── sous_chef_agent.py        ✅ Recipe recommender
│   └── recipe_knowledge_agent.py ✅ Vector search
├── database/
│   └── pantry_storage.py  ✅ SQLite layer
├── mcp/
│   └── server.py          ✅ MCP server (JSON-RPC)
├── scripts/
│   ├── ingest_recipes_milvus.py  ✅ Vector DB ingestion
│   ├── clear_pantry.py           ✅ Utility
│   ├── validate_pantry.py        ✅ Utility
│   └── evaluate_rag.py           ✅ Testing
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   └── Navbar.js         ❌ NEEDS IMPLEMENTATION
│   │   ├── pages/
│   │   │   ├── ChatInterface.js  ❌ NEEDS IMPLEMENTATION
│   │   │   ├── PantryManagement.js ❌ NEEDS IMPLEMENTATION
│   │   │   └── RecipeSearch.js   ❌ NEEDS IMPLEMENTATION
│   │   ├── services/
│   │   │   └── api.js            ❌ NEEDS IMPLEMENTATION
│   │   └── App.js                ❌ NEEDS IMPLEMENTATION
│   └── package.json              ❌ NEEDS CREATION
├── data/                  ✅ Recipe metadata
├── assets/                ✅ Dataset
├── main.py                ✅ LangGraph workflow
├── requirements.txt       ✅ CLEANED (20 packages)
├── .env                   ✅ Required
└── README.md              ✅ Exists
```

## Summary of Changes Made

### ✅ Files Removed:
1. `frontend/build/` - Old build artifact
2. `frontend/src/pages/ChatInterface.js.backup` - Backup file
3. `scripts/ingest_recipes_pinecone.py` - Unused
4. `scripts/ingest_recipes_qdrant.py` - Unused
5. All `__pycache__` directories
6. All `*.pyc` files
7. `requirements_old.txt` - Created backup of old requirements

### ✅ Files Updated:
1. `requirements.txt` - Cleaned from 99 to ~20 essential packages

### ❌ Next Steps Required:
1. **Implement React Frontend** - All components need to be created
2. **Add package.json** - Define React dependencies
3. **Create API service layer** - Connect frontend to backend
4. **Consider Flask migration** - If FastAPI → Flask is required
5. **Test end-to-end flow** - Frontend → Backend → Agents → Database

## Testing Checklist

- [ ] Backend starts successfully: `python api/server.py`
- [ ] MCP server starts: `python mcp/server.py`
- [ ] Can add pantry items via API: `POST /pantry/add`
- [ ] Can search recipes: `POST /recipes/search`
- [ ] Chat endpoint works: `POST /chat`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Frontend connects to backend
- [ ] Full workflow: Add ingredient → Chat "what can I make?" → Get recommendations

## Conclusion

**Architecture Quality: 8/10**
- Backend and agent workflow are excellent
- FastAPI vs Flask is minor (both work)
- Frontend is the main gap

**Immediate Priority:**
Implement the React frontend to complete the application.
