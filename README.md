<div align="center">

# 🍽️ Leftovr

**Your AI-Powered Recipe Assistant & Pantry Manager**

A sophisticated multi-agent food concierge system that helps you discover delicious recipes based on what you already have in your pantry.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991.svg)](https://openai.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-green.svg)](https://github.com/langchain-ai/langgraph)

</div>

---

## 📖 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Setup Instructions](#-setup-instructions)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Database Management](#-database-management)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## ✨ Features

### 🤖 **Multi-Agent AI System**

- **Executive Chef (Orchestrator)**: Routes queries and coordinates agent collaboration
- **Pantry Agent**: Manages inventory with natural language commands via Model Context Protocol (MCP)
- **Recipe Knowledge Agent**: Performs hybrid search across recipe databases (Milvus/Qdrant)
- **Sous Chef**: Curates top-3 recommendations and adapts recipes to your pantry

### 🔍 **Intelligent Recipe Search**

- **Hybrid Search**: Combines semantic (vector) and keyword search for optimal results
- **Pantry-Based Matching**: Finds recipes that maximize use of your available ingredients
- **Expiring Item Prioritization**: Suggests recipes using ingredients that expire soon
- **Smart Filtering**: Respects dietary restrictions, allergies, and cuisine preferences

### 🗄️ **Smart Pantry Management**

- Natural language inventory updates ("I have 2 chicken breasts and tomatoes")
- Automatic expiration tracking
- Quantity management with delta operations
- Persistent SQLite storage (`~/.leftovr/pantry.db`)

### 🎨 **User-Friendly Interface**

- Beautiful Streamlit web interface
- Real-time chat-based interaction
- Visual recipe cards with metadata (prep time, servings, match percentage)
- Sidebar showing live pantry inventory and preferences

### 🧠 **Contextual Awareness**

- Maintains conversation history
- Remembers user preferences across sessions
- Learns dietary restrictions and allergies
- Adapts recipes based on skill level

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│                  (streamlit_app.py)                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Workflow Orchestrator                 │
│                    (main.py)                                 │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Executive    │  │   Pantry     │  │   Recipe     │     │
│  │    Chef      │─▶│   Agent      │  │  Knowledge   │     │
│  │ (Classifier) │  │   (MCP)      │  │   Agent      │     │
│  └──────────────┘  └──────┬───────┘  └──────┬───────┘     │
│                            │                  │              │
│                            ▼                  ▼              │
│                     ┌──────────────┐  ┌──────────────┐     │
│                     │   SQLite     │  │   Milvus/    │     │
│                     │   Pantry     │  │   Qdrant     │     │
│                     │     DB       │  │   Vector DB  │     │
│                     └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐                                           │
│  │  Sous Chef   │                                           │
│  │ (Recommender)│                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
                  ┌──────────┐
                  │ OpenAI   │
                  │ GPT-4o   │
                  └──────────┘
```

### Agent Responsibilities

| Agent                | Role                                                 | Technologies                                 |
| -------------------- | ---------------------------------------------------- | -------------------------------------------- |
| **Executive Chef**   | Query classification, routing, general conversation  | OpenAI GPT-4o                                |
| **Pantry Agent**     | Inventory CRUD operations, expiration tracking       | MCP Server, SQLite                           |
| **Recipe Knowledge** | Hybrid search, ingredient matching, recipe retrieval | Milvus/Zilliz, Qdrant, Sentence Transformers |
| **Sous Chef**        | Recipe ranking, adaptation, customization            | OpenAI GPT-4o                                |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key
- (Optional) Zilliz Cloud or Milvus cluster for vector search

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd leftovr-app

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Create .env file
# Edit .env and add your API keys
```

### Launch the App

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# Run Streamlit interface
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501` 🎉

---

## 🛠️ Setup Instructions

### 1. Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
touch .env
```

Add the following variables:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional - For LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=leftovr-app

# Optional - For Milvus/Zilliz Cloud
ZILLIZ_CLUSTER_ENDPOINT=your_zilliz_endpoint
ZILLIZ_TOKEN=your_zilliz_token
```

### 4. Set Up Vector Database (Optional but Recommended)

#### Option A: Zilliz Cloud (Managed Milvus)

1. Sign up at [Zilliz Cloud](https://cloud.zilliz.com/)
2. Create a cluster
3. Add credentials to `.env`:
   ```env
   ZILLIZ_CLUSTER_ENDPOINT=https://your-cluster.api.gcp-us-west1.zillizcloud.com
   ZILLIZ_TOKEN=your_token_here
   ```

#### Option B: Local Qdrant

Qdrant will be used automatically if Milvus is not configured. No additional setup needed.

### 5. Ingest Recipe Data

```bash
# Ingest recipes into Milvus (preferred)
python scripts/ingest_recipes_milvus.py --input assets/full_dataset.csv --outdir data --build-milvus

# OR ingest into Qdrant (local)
python scripts/ingest_recipes_qdrant.py
```

---

## 💡 Usage

### Basic Workflow

1. **Tell Leftovr What You Have**

   ```
   "I have 2 chicken breasts, tomatoes, pasta, and garlic"
   ```

2. **Ask for Recipe Suggestions**

   ```
   "What can I make with these ingredients?"
   "I want something Italian and vegetarian"
   ```

3. **Get Top 3 Recommendations**

   - View recipe cards with prep time, servings, and match percentage
   - See ingredient lists and direction previews
   - Select a recipe (1, 2, or 3)

4. **Receive Customized Recipe**
   - Adapted to your pantry
   - Substitutions suggested for missing ingredients
   - Formatted with step-by-step instructions

### Natural Language Commands

#### Pantry Management

```
✅ "Add 500g chicken breast, 3 tomatoes, and 1 onion"
✅ "I ate 2 eggs"
✅ "Remove the expired milk"
✅ "Update garlic quantity to 5 cloves"
✅ "Clear my entire pantry"
```

#### Recipe Search

```
✅ "Find recipes with chicken and tomatoes"
✅ "I'm vegetarian and allergic to nuts"
✅ "What can I cook in under 30 minutes?"
✅ "Suggest Italian recipes for beginners"
```

#### General Conversation

```
✅ "How do I dice an onion?"
✅ "What's the difference between sautéing and frying?"
✅ "Tell me about Mediterranean cuisine"
```

---

## 📁 Project Structure

```
leftovr-app/
├── agents/                          # AI Agent implementations
│   ├── executive_chef_agent.py      # Query classification & routing
│   ├── pantry_agent.py              # Inventory management (MCP)
│   ├── recipe_knowledge_agent.py    # Hybrid search engine
│   └── sous_chef_agent.py           # Recommendation & adaptation
│
├── database/                        # Data persistence layer
│   └── pantry_storage.py            # SQLite operations
│
├── mcp/                             # Model Context Protocol
│   └── server.py                    # MCP server for pantry operations
│
├── scripts/                         # Utility scripts
│   ├── ingest_recipes_milvus.py     # Ingest recipes to Milvus
│   ├── ingest_recipes_qdrant.py     # Ingest recipes to Qdrant
│   ├── validate_pantry.py           # Database validation
│   └── clear_pantry.py              # Reset pantry database
│
├── tests/                           # Test suite
│   └── test_hybrid_search.py        # Hybrid search tests
│
├── data/                            # Recipe metadata
│   ├── ingredient_index.json        # Ingredient mappings
│   └── recipe_metadata.jsonl        # Recipe database
│
├── assets/                          # Raw datasets
│   └── full_dataset.csv             # Recipe dataset
│
├── qdrant_data/                     # Qdrant vector storage
│
├── main.py                          # LangGraph workflow orchestration
├── streamlit_app.py                 # Streamlit web interface
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (gitignored)
├── .env.example                     # Environment template
└── README.md                        # This file
```

---

## 🗄️ Database Management

### Pantry Database

The pantry inventory is stored in SQLite at `~/.leftovr/pantry.db`.

#### Validate Database

```bash
python scripts/validate_pantry.py
```

**Output:**

- Current inventory items
- Quantities and units
- Expiration dates
- Items expiring within 3 days

#### Clear Pantry

```bash
python scripts/clear_pantry.py
```

#### Manual Database Access

```bash
sqlite3 ~/.leftovr/pantry.db
> SELECT * FROM pantry_items;
> .exit
```

### Vector Database

#### Milvus/Zilliz Cloud

- Collection: `recipes`
- Embedding Model: `sentence-transformers/all-MiniLM-L6-v2`
- Dimension: 384

#### Qdrant (Local)

- Collection: `recipes`
- Storage: `./qdrant_data/`

---

## 🧪 Development

### Running Tests

```bash
# Test hybrid search
python tests/test_hybrid_search.py

# Test pantry operations
python scripts/validate_pantry.py
```

### CLI Testing Mode

For development and debugging, you can run the workflow in CLI mode:

```bash
python main.py
```

**Note:** This runs a hardcoded test conversation. Use the Streamlit interface for production.

### Adding Dependencies

```bash
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
```

### LangSmith Tracing

Enable LangSmith for workflow debugging:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=leftovr-app
```

View traces at [smith.langchain.com](https://smith.langchain.com/)

---

## 🔧 Troubleshooting

### Common Issues

#### "Recipe search is not available"

**Cause:** Vector database not set up or recipe data not ingested.

**Solution:**

```bash
python scripts/ingest_recipes_milvus.py --input assets/full_dataset.csv --outdir data --build-milvus
```

#### "Could not connect to MCP server"

**Cause:** MCP server initialization failed.

**Solution:** Check that `mcp/server.py` exists and is valid. The app will continue without MCP but pantry operations may be limited.

#### "OpenAI API Error"

**Cause:** Invalid or missing API key.

**Solution:**

1. Verify `OPENAI_API_KEY` in `.env`
2. Check API key is valid at [platform.openai.com](https://platform.openai.com/)
3. Ensure you have credits/billing enabled

#### Slow Recipe Search

**Cause:** Using Qdrant (local) instead of Milvus (cloud).

**Solution:** Set up Zilliz Cloud for faster semantic search:

- Sign up at [cloud.zilliz.com](https://cloud.zilliz.com/)
- Add credentials to `.env`
- Re-run ingestion script

---

## 📚 Additional Resources

- **LangGraph Documentation**: [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
- **Streamlit Docs**: [docs.streamlit.io](https://docs.streamlit.io/)
- **Milvus Documentation**: [milvus.io/docs](https://milvus.io/docs)
- **Model Context Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)

---

## 📄 License

See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Recipe dataset from [source/attribution]
- Built with [LangChain](https://langchain.com/) & [LangGraph](https://github.com/langchain-ai/langgraph)
- Powered by [OpenAI GPT-4o](https://openai.com/)

---

<div align="center">

**Made with ❤️ and 🍽️**

_Reduce food waste. Cook delicious meals. Enjoy your leftovers._

</div>
