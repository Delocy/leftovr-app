# Leftovr App Architecture

## Overview
Leftovr is a multi-agent AI system for recipe recommendations built with LangChain, LangGraph, and Streamlit.

## Entry Point
**Primary Interface**: Streamlit Web App (`streamlit_app.py`)

## Agent Architecture

### 4 Specialized Agents

1. **Executive Chef Agent** (`agents/executive_chef_agent.py`)
   - **Dual Role**: Orchestrator + User Interface
   - Classifies user queries (recipe/pantry/general)
   - Extracts dietary preferences and restrictions
   - Coordinates other agents
   - Presents final results

2. **Pantry Agent** (`agents/pantry_agent.py`)
   - Manages ingredient inventory
   - Tracks expiration dates
   - Provides ingredient availability checks

3. **Recipe Knowledge Agent** (`agents/recipe_knowledge_agent.py`)
   - Hybrid search: Keyword + Semantic (Qdrant)
   - Loads recipe metadata from JSONL
   - Ingredient-to-recipe mapping

4. **Sous Chef Agent** (`agents/sous_chef_agent.py`)
   - Generates recipe recommendations
   - Adapts recipes to user preferences
   - Handles recipe Q&A dialogue

## Workflow State Machine (LangGraph)

### Nodes
```
waiter_node → executive_chef_orchestrate → agent_execute → waiter_finalize
                                         ↘ sous_chat (optional)
```

### State Flow
```
User Input
    ↓
[waiter_node]
    ├─ Stage: initial → Greet user
    ├─ Stage: collecting → Classify query, extract preferences
    ├─ Stage: presenting_options → Show recipe recommendations
    └─ Stage: awaiting_selection → Wait for user choice
    ↓
[executive_chef_orchestrate]
    ├─ Analyze complexity
    ├─ Create task plan
    └─ Delegate to agents
    ↓
[agent_execute]
    ├─ executing_pantry → Pantry operations
    ├─ executing_recipe_search → Find recipes
    └─ executing_adaptation → Adapt selected recipe
    ↓
[waiter_finalize]
    ├─ Validate results
    └─ Present to user
```

## Data Flow

### Streamlit Chat Flow
```
1. User Message → ChatbotOrchestrator
2. Guardrail Check (cooking-related?)
3. process_chat_message()
   ├─ General Query → Direct response
   ├─ Pantry Query → Update inventory
   └─ Recipe Query → Trigger workflow
4. run_workflow() → LangGraph execution
5. Display results in Streamlit UI
```

## Technology Stack

- **Framework**: LangGraph (multi-agent orchestration)
- **LLM**: OpenAI GPT-4o-mini
- **Vector DB**: Qdrant (semantic search)
- **Embeddings**: sentence-transformers
- **UI**: Streamlit
- **Data**: Recipe metadata (JSONL) + ingredient index (JSON)

## Key Features

### 1. Hybrid Search
- **Keyword Search**: Fast ingredient-based lookup
- **Semantic Search**: Natural language recipe matching
- **Combined**: Best of both approaches

### 2. Dietary Constraints
- Allergies (automatic filtering)
- Restrictions (vegetarian, vegan, gluten-free, etc.)
- Cuisine preferences
- Skill level adaptation

### 3. Smart Recommendations
- Prioritizes expiring ingredients
- Validates recipe safety
- Adapts recipes to pantry availability

## Configuration

### Environment Variables (.env)
```bash
OPENAI_API_KEY=your_key_here
LANGCHAIN_TRACING_V2=false  # Optional: Enable LangSmith tracing
LANGCHAIN_API_KEY=your_langsmith_key  # Optional
LANGCHAIN_PROJECT=leftovr-app  # Optional
```

### Recipe Data Setup
```bash
# Quick start (sample data)
python scripts/ingest_recipes_qdrant.py \
  --input assets/full_dataset.csv \
  --outdir data \
  --sample 1000 \
  --build-qdrant

# Full database (slow - hours)
python scripts/ingest_recipes_qdrant.py \
  --input assets/full_dataset.csv \
  --outdir data \
  --build-qdrant
```

## File Structure
```
leftovr-app/
├── streamlit_app.py          # Main Streamlit interface
├── main.py                    # Core workflow engine (LangGraph)
├── .env                       # API keys (not committed)
├── requirements.txt           # Python dependencies
├── agents/
│   ├── executive_chef_agent.py
│   ├── pantry_agent.py
│   ├── recipe_knowledge_agent.py
│   └── sous_chef_agent.py
├── data/
│   ├── recipe_metadata.jsonl  # Recipe database
│   └── ingredient_index.json  # Ingredient → recipe mapping
├── utils/
│   └── output_validator.py    # Safety validation
└── scripts/
    └── ingest_recipes_qdrant.py  # Data ingestion
```

## Error Handling

### Graceful Degradation
1. **No Recipe Data**: App works but can't search recipes
2. **No Semantic Search**: Falls back to keyword-only search
3. **API Failures**: Clear error messages with recovery suggestions

### Validation Layers
1. **Input Validation**: Guardrails for cooking-related queries
2. **Recipe Validation**: Allergy checks, constraint satisfaction
3. **Output Validation**: Safety checks before presentation

## Development Notes

### Python Version
- **Required**: Python 3.9-3.12
- **Note**: PyTorch doesn't support Python 3.13 yet

### Dependencies
- Use Python 3.9 for full compatibility (PyTorch + sentence-transformers)
- NumPy <2.0 required for PyTorch compatibility

### Testing
```bash
# Run test scenarios
python tests/test_scenarios.py
python tests/test_orchestration.py
python tests/test_hybrid_search.py
```

## Future Improvements

1. **Add sample dataset** in repo for quick start
2. **Improve node routing** - simplify the workflow graph
3. **Add more test coverage** for edge cases
4. **Implement Google Sheets** integration for persistent pantry
5. **Add recipe rating/feedback** system
