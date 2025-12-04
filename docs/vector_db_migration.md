# Vector Database Migration Guide

## Quick Comparison for Leftovr

| Database | Setup Time | Free Tier | Best For | Production Ready |
|----------|-----------|-----------|----------|------------------|
| **Pinecone** | 5 min | 100K vectors | Demos/Portfolio | ✅ Yes |
| **Qdrant** | 15 min | 1GB storage | Local Dev | ✅ Yes |
| **Chroma** | 1 min | Unlimited | Prototyping | ⚠️ Limited |
| **Weaviate** | 30 min | Self-hosted | Hybrid Search | ✅ Yes |
| **Zilliz** (current) | Done ✓ | Limited | Enterprise | ✅ Yes |
| **pgvector** | 10 min | Unlimited | Simple projects | ⚠️ Limited |

## 🚀 Migration to Pinecone (Recommended)

### Step 1: Install & Setup
```bash
pip install pinecone-client
```

### Step 2: Update Environment Variables
```bash
# .env
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=gcp-starter  # or your region
PINECONE_INDEX_NAME=recipes
```

### Step 3: Update recipe_knowledge_agent.py

**Replace Milvus initialization with:**

```python
import pinecone
from pinecone import Pinecone, ServerlessSpec

class RecipeKnowledgeAgent:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.pinecone_client = None
        self.index = None
        
    def setup_pinecone(self):
        """Initialize Pinecone connection"""
        api_key = os.getenv("PINECONE_API_KEY")
        environment = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
        index_name = os.getenv("PINECONE_INDEX_NAME", "recipes")
        
        # Initialize Pinecone
        pc = Pinecone(api_key=api_key)
        
        # Create index if it doesn't exist
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=384,  # all-MiniLM-L6-v2 dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=environment
                )
            )
        
        self.index = pc.Index(index_name)
        print(f"✅ Connected to Pinecone index: {index_name}")
        
    def hybrid_query(self, pantry_items=None, query_text=None, top_k=10, **kwargs):
        """Query recipes using Pinecone"""
        if not self.index:
            raise ValueError("Pinecone not initialized. Call setup_pinecone() first.")
        
        # Generate embedding for query
        query_embedding = self.embedding_model.encode(query_text).tolist()
        
        # Metadata filter for pantry items
        filter_dict = {}
        if pantry_items:
            # Pinecone filtering syntax
            filter_dict = {
                "NER": {"$in": pantry_items}
            }
        
        # Query Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter_dict if filter_dict else None,
            include_metadata=True
        )
        
        # Format results
        formatted_results = []
        for match in results['matches']:
            metadata = match['metadata']
            score = match['score']
            
            # Calculate pantry match
            recipe_ingredients = metadata.get('NER', [])
            num_used = len(set(recipe_ingredients) & set(pantry_items or []))
            missing = list(set(recipe_ingredients) - set(pantry_items or []))
            
            formatted_results.append((
                metadata,
                score,
                num_used,
                missing
            ))
        
        return formatted_results
```

### Step 4: Create Ingestion Script for Pinecone

```python
# scripts/ingest_recipes_pinecone.py
import pandas as pd
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

def ingest_to_pinecone(csv_path):
    # Initialize
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    index_name = "recipes"
    
    # Create index
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    
    index = pc.Index(index_name)
    
    # Load recipes
    df = pd.read_csv(csv_path)
    
    # Prepare vectors in batches
    batch_size = 100
    vectors = []
    
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        # Create text for embedding
        text = f"{row['title']}. Ingredients: {', '.join(eval(row['NER']))}"
        
        # Generate embedding
        embedding = embedding_model.encode(text).tolist()
        
        # Prepare metadata
        metadata = {
            "title": row['title'],
            "directions": row.get('directions', ''),
            "link": row.get('link', ''),
            "source": row.get('source', ''),
            "NER": eval(row['NER']) if isinstance(row['NER'], str) else row['NER']
        }
        
        vectors.append({
            "id": f"recipe_{idx}",
            "values": embedding,
            "metadata": metadata
        })
        
        # Upsert in batches
        if len(vectors) >= batch_size:
            index.upsert(vectors=vectors)
            vectors = []
    
    # Upsert remaining
    if vectors:
        index.upsert(vectors=vectors)
    
    print(f"✅ Ingested {len(df)} recipes to Pinecone!")

if __name__ == "__main__":
    ingest_to_pinecone("assets/full_dataset.csv")
```

### Step 5: Run Ingestion
```bash
python scripts/ingest_recipes_pinecone.py
```

### Step 6: Update main.py
```python
# In LeftovrWorkflow.__init__()
self.recipe_agent = RecipeKnowledgeAgent(data_dir='data')
try:
    # Use Pinecone instead of Milvus
    self.recipe_agent.setup_pinecone()
    print("✅ Recipe Knowledge Agent initialized with Pinecone")
except Exception as e:
    print(f"⚠️  Warning: {e}")
    self.recipe_agent = None
```

## 🔄 Alternative: Qdrant (Local + Free)

### Why Qdrant?
- Run locally during development
- Deploy to cloud for production
- No API costs during development
- Great documentation

### Quick Setup
```bash
# Start Qdrant locally
docker run -p 6333:6333 qdrant/qdrant

# Install client
pip install qdrant-client
```

### Code Changes
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Initialize
client = QdrantClient(host="localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="recipes",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

# Query
results = client.search(
    collection_name="recipes",
    query_vector=embedding,
    limit=10
)
```

## 💰 Cost Comparison (for 100K recipes)

| Database | Monthly Cost | Setup | Maintenance |
|----------|-------------|-------|-------------|
| Pinecone | FREE | Easy | None |
| Qdrant Cloud | FREE | Easy | None |
| Qdrant Local | $0 | Medium | Docker |
| Chroma | $0 | Easy | None |
| Zilliz Cloud | $100+ | Done ✓ | None |
| Weaviate Cloud | $25 | Hard | None |

## 🎯 Recommendation for Job Application

**Use Pinecone because:**
1. ✅ Shows you know industry-standard tools
2. ✅ Free tier is perfect for demos
3. ✅ Easy to set up and maintain
4. ✅ Professional and production-ready
5. ✅ Better for portfolio than DIY solutions

**Keep Zilliz if:**
- You want to show enterprise tool experience
- You already have credits/free tier
- You're comfortable with current setup

## 🚀 Quick Win: Add Both!

Show versatility by supporting multiple backends:

```python
class RecipeKnowledgeAgent:
    def __init__(self, backend='pinecone'):
        self.backend = backend
        
    def setup(self):
        if self.backend == 'pinecone':
            self.setup_pinecone()
        elif self.backend == 'milvus':
            self.setup_milvus()
        elif self.backend == 'qdrant':
            self.setup_qdrant()
```

This shows:
- System design skills
- Flexibility
- Understanding of trade-offs
