# Pinecone Setup Guide for Leftovr App

## ⚠️ Important Notice

Your code is currently configured for **Milvus (Zilliz Cloud)** but you want to use **Pinecone** instead.

## Current State

**What's Implemented:** Milvus/Zilliz Cloud
- ❌ `agents/recipe_knowledge_agent.py` - Uses Milvus client
- ❌ `scripts/ingest_recipes_milvus.py` - Milvus ingestion script
- ❌ Environment variables expect `ZILLIZ_CLUSTER_ENDPOINT` and `ZILLIZ_TOKEN`

**What You Need:** Pinecone
- ✅ `requirements.txt` - Now includes `pinecone==8.0.0`
- ❌ Need to modify `recipe_knowledge_agent.py` to use Pinecone
- ❌ Need Pinecone ingestion script (was deleted, need to recreate)

## Changes Needed

### 1. Update requirements.txt ✅ DONE

Changed from:
```
pymilvus==2.6.3
```

To:
```
pinecone==8.0.0
```

### 2. Modify `agents/recipe_knowledge_agent.py`

The agent currently uses Milvus. You need to replace the Milvus client code with Pinecone client code.

**Current (Milvus):**
```python
from pymilvus import MilvusClient, DataType

def setup_milvus(self):
    self.milvus_client = MilvusClient(
        uri=os.environ.get('ZILLIZ_CLUSTER_ENDPOINT'),
        token=os.environ.get('ZILLIZ_TOKEN')
    )
```

**Should be (Pinecone):**
```python
from pinecone import Pinecone, ServerlessSpec

def setup_pinecone(self):
    pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
    self.index = pc.Index(os.environ.get('PINECONE_INDEX_NAME'))
```

### 3. Create Pinecone Ingestion Script

You need a script to upload your recipes to Pinecone. Here's the structure:

```python
# scripts/ingest_recipes_pinecone.py
import os
import pandas as pd
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

# Initialize Pinecone
pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])

# Create or connect to index
index_name = "recipes"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,  # for all-MiniLM-L6-v2
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )

index = pc.Index(index_name)

# Load and embed recipes
model = SentenceTransformer('all-MiniLM-L6-v2')
df = pd.read_csv('assets/full_dataset.csv')

# Prepare vectors
vectors = []
for idx, row in df.iterrows():
    text = f"{row['title']} {' '.join(row['NER'])}"
    embedding = model.encode(text).tolist()
    
    vectors.append({
        'id': str(row['id']),
        'values': embedding,
        'metadata': {
            'title': row['title'],
            'ingredients': row['NER'],
            'link': row['link'],
            'source': row['source']
        }
    })
    
    # Batch upsert every 100
    if len(vectors) >= 100:
        index.upsert(vectors)
        vectors = []

# Upsert remaining
if vectors:
    index.upsert(vectors)
```

### 4. Update Environment Variables

**Remove (Milvus):**
```bash
ZILLIZ_CLUSTER_ENDPOINT=https://...
ZILLIZ_TOKEN=...
```

**Add (Pinecone):**
```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=recipes
PINECONE_ENVIRONMENT=us-east-1  # or your region
```

## Step-by-Step Migration

### Step 1: Install Pinecone
```bash
pip install pinecone==8.0.0
```

### Step 2: Set Up Pinecone Account
1. Go to [https://www.pinecone.io/](https://www.pinecone.io/)
2. Sign up or log in
3. Create a new project
4. Create a serverless index named "recipes"
   - Dimensions: 384 (for all-MiniLM-L6-v2)
   - Metric: cosine
   - Region: us-east-1 (or your preferred region)
5. Get your API key from the console

### Step 3: Update .env
```bash
# Add to .env
PINECONE_API_KEY=your_api_key_here
PINECONE_INDEX_NAME=recipes
```

### Step 4: Modify recipe_knowledge_agent.py

I can help you modify the agent file to use Pinecone instead of Milvus. The main changes:

1. Replace `setup_milvus()` with `setup_pinecone()`
2. Replace Milvus query calls with Pinecone query calls
3. Update hybrid search to use Pinecone's filtering

Would you like me to create the modified version?

## Quick Reference: Milvus vs Pinecone API

| Operation | Milvus | Pinecone |
|-----------|--------|----------|
| **Initialize** | `MilvusClient(uri, token)` | `Pinecone(api_key=...)` |
| **Connect to Index** | `client.list_collections()` | `pc.Index(name)` |
| **Query by ID** | `client.query(filter="id==123")` | `index.fetch(ids=['123'])` |
| **Vector Search** | `client.search(data=[vector])` | `index.query(vector=vector, top_k=10)` |
| **Hybrid Search** | `client.search()` with filter | `index.query()` with filter |
| **Upsert** | `client.insert()` | `index.upsert()` |

## What I Can Do for You

I can help you:

1. ✅ Create a complete Pinecone ingestion script
2. ✅ Modify `recipe_knowledge_agent.py` to use Pinecone
3. ✅ Update all documentation to reference Pinecone
4. ✅ Create helper scripts for Pinecone operations
5. ✅ Update the backend to work with Pinecone

Would you like me to proceed with these changes?

## Estimated Migration Time

- Modify agent code: 15 minutes
- Create ingestion script: 10 minutes
- Ingest data to Pinecone: 5-30 minutes (depending on dataset size)
- Test integration: 10 minutes

**Total: ~1 hour**

## Benefits of Pinecone

✅ Fully managed (no infrastructure setup)  
✅ Serverless (pay per usage)  
✅ Fast vector search  
✅ Easy filtering and metadata  
✅ Good Python SDK  

## Next Steps

Let me know if you want me to:
1. Create the Pinecone ingestion script
2. Modify the recipe_knowledge_agent.py to use Pinecone
3. Update all related files and documentation
