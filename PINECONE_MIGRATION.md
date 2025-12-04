# Pinecone Migration Guide

## ✅ Migration Complete!

Your Leftovr app has been successfully migrated from Zilliz Cloud (Milvus) to Pinecone.

---

## 🎯 What Changed

### 1. **Vector Database**: Zilliz/Milvus → Pinecone
   - **Why?** Better free tier (100K vectors vs Zilliz's paid tiers)
   - **Why?** Simpler setup (API key only, no cluster endpoints)
   - **Why?** Industry standard (looks great for job applications!)
   - **Why?** 5-minute setup vs complex Zilliz configuration

### 2. **Code Updates**
   - ✅ `agents/recipe_knowledge_agent.py`: Now uses Pinecone client
   - ✅ `main.py`: Calls `setup_pinecone()` instead of `setup_milvus()`
   - ✅ `scripts/ingest_recipes_pinecone.py`: New ingestion script for Pinecone
   - ✅ `requirements.txt`: Added `pinecone-client==5.0.1`
   - ✅ `.env.example`: Updated with `PINECONE_API_KEY` (removed Zilliz vars)

### 3. **Environment Variables**
   - ❌ Removed: `ZILLIZ_CLUSTER_ENDPOINT`
   - ❌ Removed: `ZILLIZ_TOKEN`
   - ✅ Added: `PINECONE_API_KEY`

---

## 🚀 Next Steps (Action Required!)

### Step 1: Get Your Pinecone API Key (5 minutes)

1. **Sign up for Pinecone** (free tier):
   - Go to: https://www.pinecone.io/
   - Click "Start Free"
   - Sign up with email or GitHub

2. **Create an API key**:
   - After login, go to: **API Keys** (left sidebar)
   - Click "Create API Key"
   - Copy your API key (looks like: `pcsk_...`)

3. **Save your API key**:
   ```bash
   # Create .env file from template
   cp .env.example .env
   
   # Edit .env and add your keys:
   OPENAI_API_KEY=sk-...
   PINECONE_API_KEY=pcsk_...
   ```

---

### Step 2: Ingest Recipes to Pinecone

You need to upload your recipe dataset to Pinecone. This creates the vector index for semantic search.

#### Option A: Full Dataset (Recommended for Production)
```bash
# Make sure you're in the project root
cd /Users/SG4111/Desktop/me/leftovr-app

# Activate virtual environment
source .venv/bin/activate

# Run ingestion (takes ~10-20 minutes for full dataset)
python scripts/ingest_recipes_pinecone.py \
  --input assets/full_dataset.csv \
  --outdir data
```

#### Option B: Sample Dataset (Fast, for Testing)
```bash
# Only ingest first 10,000 recipes (takes ~2-3 minutes)
python scripts/ingest_recipes_pinecone.py \
  --input assets/full_dataset.csv \
  --outdir data \
  --sample 10000
```

**What this does:**
- ✅ Creates embeddings for all recipes using `all-MiniLM-L6-v2`
- ✅ Uploads vectors + metadata to Pinecone index `leftovr-recipes`
- ✅ Generates `data/recipe_metadata.jsonl` (local cache)
- ✅ Generates `data/ingredient_index.json` (fast ingredient lookup)

**Expected Output:**
```
🔧 Setting up Pinecone connection...
   ✅ Connected to Pinecone
📦 Loading embedding model: all-MiniLM-L6-v2...
   Creating new Pinecone index 'leftovr-recipes'...
   ✅ Created 'leftovr-recipes' index

📂 Processing recipes from assets/full_dataset.csv...
   Processed 10,000 recipes...
   Processed 20,000 recipes...
   ...

✅ Processing complete!
   - Processed 231,637 recipes
   - Uploaded 231,637 recipes to Pinecone
   - Skipped 0 recipes (no ingredients)

📊 Pinecone Index Stats:
   - Total vectors: 231,637
   - Dimension: 384
```

---

### Step 3: Test the Integration

```bash
# Start the backend servers
./start_backend.sh

# In another terminal, test the API
./test_integration.sh
```

**Check Recipe Search Endpoint:**
```bash
curl -X POST http://localhost:8000/recipes/search \
  -H "Content-Type: application/json" \
  -d '{"query": "pasta carbonara", "limit": 5}'
```

Expected response: List of 5 recipes with match percentages.

---

### Step 4: Start the Full App

```bash
# Start both backend and frontend
./start_all.sh
```

Then open: http://localhost:3000

---

## 🔍 Verification Checklist

- [ ] `.env` file exists with both API keys
- [ ] Pinecone index `leftovr-recipes` created (check Pinecone dashboard)
- [ ] `data/recipe_metadata.jsonl` exists (~50MB file)
- [ ] `data/ingredient_index.json` exists
- [ ] Backend starts without errors: `./start_backend.sh`
- [ ] Recipe search returns results: `curl http://localhost:8000/recipes/search ...`
- [ ] Frontend loads: http://localhost:3000
- [ ] Chat interface can find recipes based on pantry items

---

## 🐛 Troubleshooting

### "Pinecone not connected"
**Solution:** Check your `PINECONE_API_KEY` in `.env`
```bash
# Verify .env has correct key
cat .env | grep PINECONE_API_KEY

# Should show: PINECONE_API_KEY=pcsk_...
```

### "Index 'leftovr-recipes' not found"
**Solution:** You haven't run the ingestion script yet
```bash
python scripts/ingest_recipes_pinecone.py \
  --input assets/full_dataset.csv \
  --outdir data
```

### "sentence-transformers not available"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Recipe search returns no results
**Possible causes:**
1. Index is empty → Run ingestion script
2. Wrong API key → Check `.env` file
3. Pinecone index name mismatch → Should be `leftovr-recipes`

**Debug:**
```bash
# Check Pinecone index stats
python -c "
from pinecone import Pinecone
import os
from dotenv import load_dotenv

load_dotenv()
pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
index = pc.Index('leftovr-recipes')
print(index.describe_index_stats())
"
```

---

## 📊 Pinecone Free Tier Limits

- ✅ **100,000 vectors** (your dataset: ~231K, so you might need to upgrade or sample)
- ✅ **1 index** (you're using `leftovr-recipes`)
- ✅ **1 pod** (serverless)
- ✅ **Unlimited queries** (no rate limits for hobby projects)

**Recommendation for Demo:**
- Use `--sample 95000` to stay under free tier limit
- Or upgrade to Pinecone Starter ($70/month) for full dataset

---

## 🎓 How It Works Now

### Old Flow (Zilliz/Milvus):
```
User Query → RecipeKnowledgeAgent.setup_milvus() 
          → MilvusClient (complex setup) 
          → Zilliz Cloud (paid)
```

### New Flow (Pinecone):
```
User Query → RecipeKnowledgeAgent.setup_pinecone() 
          → Pinecone client (API key only) 
          → Pinecone Index (free tier)
```

### Semantic Search:
1. User searches: "quick Italian pasta"
2. Agent embeds query using `all-MiniLM-L6-v2` (384 dims)
3. Pinecone finds top-K similar recipe vectors (cosine similarity)
4. Agent returns recipes with match percentages

### Hybrid Search (Leftovr mode):
1. User has pantry: `['chicken', 'lemon', 'garlic']`
2. Agent queries Pinecone with pantry embedding
3. Agent filters results:
   - ✅ Recipes with 0 missing ingredients (highest priority)
   - ✅ Recipes using MORE pantry items (better score)
   - ✅ Semantic similarity boost from query text
4. Returns ranked recipes: `(metadata, score, num_used, missing)`

---

## 📚 API Reference

### RecipeKnowledgeAgent Methods

```python
# Initialize agent
agent = RecipeKnowledgeAgent()
agent.setup_pinecone()  # Connect to Pinecone

# Get single recipe by ID
recipe = agent.get_recipe_by_id(123)
# Returns: {id, title, ingredients, source, link, ner}

# Batch get recipes
recipes = agent.get_recipes_by_ids([123, 456, 789])
# Returns: Dict[int, recipe_dict]

# Semantic search
results = agent.semantic_search(
    query="easy chicken dinner",
    pantry_items=["chicken", "lemon"],
    k=10
)
# Returns: List[(recipe_id, similarity_score)]

# Hybrid search (LEFTOVR MODE)
results = agent.hybrid_query(
    pantry_items=["chicken", "lemon", "garlic"],
    query_text="quick dinner",
    top_k=20,
    allow_missing=2,  # Willing to buy 2 ingredients
    use_semantic=True
)
# Returns: List[(recipe_metadata, score, num_pantry_used, missing)]
```

---

## 🎉 Benefits of Pinecone

### Before (Zilliz):
- ❌ Complex setup (cluster endpoint + token)
- ❌ Expensive ($0.10/hour minimum, ~$70/month)
- ❌ Overkill for demo project
- ❌ Confusing documentation

### After (Pinecone):
- ✅ Simple setup (API key only)
- ✅ Free tier (100K vectors)
- ✅ Perfect for job applications (industry standard)
- ✅ Great documentation + community support
- ✅ 5-minute setup time
- ✅ Serverless (no infrastructure management)

---

## 🚀 Ready to Go!

Your migration is complete. Follow the **Next Steps** above to:
1. Get Pinecone API key
2. Ingest recipes
3. Test integration
4. Start the app

**Questions?** Check the troubleshooting section or review the code changes in:
- `agents/recipe_knowledge_agent.py`
- `scripts/ingest_recipes_pinecone.py`

Good luck with your AI Search Agent job application! 🎯
