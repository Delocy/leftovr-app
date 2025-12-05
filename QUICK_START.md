# Quick Start Guide - Leftovr App

## What You Have

✅ **Backend:** Fully functional FastAPI server with LangGraph agent workflow  
❌ **Frontend:** Structure exists but components are empty (needs implementation)

## Project Structure

```
leftovr-app/
├── api/server.py              # FastAPI backend (WORKING ✅)
├── main.py                    # LangGraph workflow (WORKING ✅)
├── agents/                    # 4 specialized agents (WORKING ✅)
├── mcp/server.py              # Pantry MCP server (WORKING ✅)
├── database/pantry_storage.py # SQLite database (WORKING ✅)
├── frontend/                  # React app (NEEDS IMPLEMENTATION ❌)
│   └── src/
│       ├── components/        # Empty files
│       ├── pages/             # Empty files
│       └── services/          # Missing API layer
├── data/                      # Recipe metadata
├── assets/                    # Dataset
└── requirements.txt           # Python dependencies (CLEANED ✅)
```

## Setup Instructions

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_openai_key_here
ZILLIZ_CLUSTER_ENDPOINT=your_milvus_endpoint
ZILLIZ_TOKEN=your_milvus_token
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=leftovr-app
EOF

# Ingest recipes to Milvus (one-time setup)
python scripts/ingest_recipes_milvus.py \
  --input assets/full_dataset.csv \
  --outdir data \
  --build-milvus
```

### 2. Running the Backend

Open 2 terminals:

**Terminal 1: MCP Server (Pantry Operations)**
```bash
python mcp/server.py
```

**Terminal 2: FastAPI Server**
```bash
python api/server.py
# OR
uvicorn api.server:app --reload --port 8000
```

### 3. Test Backend

```bash
# Health check
curl http://localhost:8000/health

# Test chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "What can I make with chicken?",
    "user_preferences": {},
    "pantry_inventory": []
  }'

# Get pantry inventory
curl http://localhost:8000/pantry/inventory

# Add pantry item
curl -X POST http://localhost:8000/pantry/add \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_name": "chicken",
    "quantity": 2,
    "unit": "lbs",
    "expiration_date": "2025-12-15"
  }'
```

## Frontend Setup (TO DO)

### Option 1: Create New React App

```bash
# Remove incomplete frontend
rm -rf frontend

# Create fresh React app
npx create-react-app frontend
cd frontend

# Install dependencies
npm install react-router-dom axios @mui/material @emotion/react @emotion/styled @mui/icons-material
```

### Option 2: Fix Existing Frontend

```bash
cd frontend

# Create package.json
cat > package.json << 'EOF'
{
  "name": "leftovr-frontend",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "react-scripts": "5.0.1",
    "axios": "^1.6.0",
    "@mui/material": "^5.14.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "@mui/icons-material": "^5.14.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": ["react-app"]
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  }
}
EOF

# Install dependencies
npm install

# Create API service
mkdir -p src/services
cat > src/services/api.js << 'EOF'
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const sendMessage = async (message, preferences, pantryInventory) => {
  const response = await axios.post(`${API_BASE_URL}/chat`, {
    user_message: message,
    user_preferences: preferences,
    pantry_inventory: pantryInventory,
  });
  return response.data;
};

export const getPantryInventory = async () => {
  const response = await axios.get(`${API_BASE_URL}/pantry/inventory`);
  return response.data;
};

export const addPantryItem = async (item) => {
  const response = await axios.post(`${API_BASE_URL}/pantry/add`, item);
  return response.data;
};

export const deletePantryItem = async (itemName) => {
  const response = await axios.delete(`${API_BASE_URL}/pantry/delete/${itemName}`);
  return response.data;
};

export const searchRecipes = async (query, preferences) => {
  const response = await axios.post(`${API_BASE_URL}/recipes/search`, {
    query,
    preferences,
    top_k: 10,
  });
  return response.data;
};
EOF

# Now implement the React components (App.js, ChatInterface.js, etc.)
# This requires actual React code which I can help you create
```

## What Needs Implementation

### 1. Core React Files
- [ ] `src/App.js` - Main app with routing
- [ ] `src/index.js` - React entry point
- [ ] `src/services/api.js` - API integration ✅ (provided above)

### 2. Components
- [ ] `src/components/Navbar.js` - Navigation bar
- [ ] `src/pages/ChatInterface.js` - Main chat interface
- [ ] `src/pages/PantryManagement.js` - Pantry CRUD
- [ ] `src/pages/RecipeSearch.js` - Recipe search

### 3. Styling
- [ ] Configure Material-UI theme
- [ ] Add global styles

## Development Workflow

Once frontend is implemented:

```bash
# Terminal 1: MCP Server
python mcp/server.py

# Terminal 2: FastAPI Backend
python api/server.py

# Terminal 3: React Frontend
cd frontend
npm start
```

Then open: http://localhost:3000

## Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Main chat interface |
| `/pantry/inventory` | GET | Get all pantry items |
| `/pantry/add` | POST | Add pantry item |
| `/pantry/update/{name}` | PUT | Update pantry item |
| `/pantry/delete/{name}` | DELETE | Delete pantry item |
| `/recipes/search` | POST | Search recipes |
| `/health` | GET | Health check |

## Environment Variables Required

```bash
# Required
OPENAI_API_KEY=sk-...           # OpenAI API key for LLM
ZILLIZ_CLUSTER_ENDPOINT=https://...  # Milvus cloud endpoint
ZILLIZ_TOKEN=...                # Milvus auth token

# Optional (for LangSmith tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=leftovr-app
```

## Troubleshooting

### Backend won't start
```bash
# Check if ports are in use
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### MCP Server issues
```bash
# Check if server is running
ps aux | grep "mcp/server.py"

# Check logs
tail -f logs/api_server.log
```

### Milvus connection fails
```bash
# Verify environment variables
echo $ZILLIZ_CLUSTER_ENDPOINT
echo $ZILLIZ_TOKEN

# Test connection
python -c "from pymilvus import MilvusClient; client = MilvusClient(uri='$ZILLIZ_CLUSTER_ENDPOINT', token='$ZILLIZ_TOKEN'); print('Connected!')"
```

## Next Steps

1. ✅ Backend is ready - test all endpoints
2. ❌ Implement React frontend components
3. ❌ Connect frontend to backend via API service
4. ❌ Test full workflow: Add ingredient → Chat → Get recipes
5. ❌ Deploy (optional)

## Need Help?

If you need help implementing the React components, I can provide:
- Complete `App.js` with routing
- Full `ChatInterface.js` with Material-UI
- `PantryManagement.js` CRUD interface
- `RecipeSearch.js` search interface

Just ask! 🚀
