#!/usr/bin/env python3
"""
Pinecone Recipe Ingestion Script for Leftovr App

This script ingests recipe data into Pinecone vector database.
It processes the recipe dataset, generates embeddings, and uploads to Pinecone.

Usage:
    python scripts/ingest_recipes_pinecone.py --input assets/full_dataset.csv --outdir data

Requirements:
    - PINECONE_API_KEY environment variable
    - pinecone==8.0.0
    - sentence-transformers
    - pandas
"""

import os
import sys
import json
import argparse
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
from dotenv import load_dotenv

try:
    from pinecone import Pinecone, ServerlessSpec
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"❌ Error: {e}")
    print("Please install required packages:")
    print("  pip install pinecone sentence-transformers pandas tqdm")
    sys.exit(1)

# Load environment variables
load_dotenv()

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'recipes')
PINECONE_CLOUD = os.getenv('PINECONE_CLOUD', 'aws')
PINECONE_REGION = os.getenv('PINECONE_REGION', 'us-east-1')

# Embedding model configuration
EMBED_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBED_DIM = 384  # Dimension for all-MiniLM-L6-v2

# Batch size for Pinecone upserts
BATCH_SIZE = 100


def validate_environment():
    """Validate required environment variables"""
    if not PINECONE_API_KEY:
        print("❌ Error: PINECONE_API_KEY environment variable not set")
        print("   Please set it in your .env file or export it:")
        print("   export PINECONE_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    print(f"✅ PINECONE_API_KEY found")
    print(f"📝 Index name: {PINECONE_INDEX_NAME}")
    print(f"☁️  Cloud provider: {PINECONE_CLOUD}")
    print(f"🌍 Region: {PINECONE_REGION}")


def initialize_pinecone():
    """Initialize Pinecone client"""
    print(f"\n🔧 Initializing Pinecone client...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    print("✅ Pinecone client initialized")
    return pc


def create_or_get_index(pc: Pinecone, index_name: str):
    """Create Pinecone index if it doesn't exist, otherwise connect to it"""
    print(f"\n📊 Checking for index '{index_name}'...")
    
    existing_indexes = pc.list_indexes().names()
    
    if index_name in existing_indexes:
        print(f"✅ Index '{index_name}' already exists")
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        print(f"   Current vector count: {stats.get('total_vector_count', 0):,}")
        
        # Ask user if they want to delete and recreate
        response = input(f"\n⚠️  Do you want to delete and recreate the index? (y/N): ").strip().lower()
        if response == 'y':
            print(f"🗑️  Deleting index '{index_name}'...")
            pc.delete_index(index_name)
            print("✅ Index deleted")
        else:
            print("📝 Will append to existing index")
            return index
    
    # Create new index
    print(f"\n🔨 Creating new index '{index_name}'...")
    print(f"   Dimensions: {EMBED_DIM}")
    print(f"   Metric: cosine")
    print(f"   Spec: Serverless ({PINECONE_CLOUD}/{PINECONE_REGION})")
    
    pc.create_index(
        name=index_name,
        dimension=EMBED_DIM,
        metric='cosine',
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION
        )
    )
    
    print(f"✅ Index '{index_name}' created successfully")
    return pc.Index(index_name)


def load_embedding_model():
    """Load SentenceTransformer model"""
    print(f"\n📦 Loading embedding model: {EMBED_MODEL_NAME}...")
    model = SentenceTransformer(EMBED_MODEL_NAME)
    print(f"✅ Model loaded (dimension: {model.get_sentence_embedding_dimension()})")
    return model


def load_recipe_data(input_path: str) -> pd.DataFrame:
    """Load recipe data from CSV"""
    print(f"\n📂 Loading recipe data from: {input_path}")
    
    if not os.path.exists(input_path):
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)
    
    df = pd.read_csv(input_path)
    print(f"✅ Loaded {len(df):,} recipes")
    print(f"   Columns: {list(df.columns)}")
    
    return df


def process_ner_field(ner_value) -> List[str]:
    """Process NER field which might be string or list"""
    if pd.isna(ner_value):
        return []
    
    if isinstance(ner_value, str):
        # Try to parse as JSON
        try:
            return json.loads(ner_value.replace("'", '"'))
        except:
            # Split by comma if not JSON
            return [x.strip() for x in ner_value.split(',') if x.strip()]
    elif isinstance(ner_value, list):
        return ner_value
    else:
        return []


def prepare_vectors(df: pd.DataFrame, model: SentenceTransformer, outdir: str) -> List[Dict[str, Any]]:
    """Prepare vectors for Pinecone upsert"""
    print(f"\n🔄 Preparing vectors for {len(df):,} recipes...")
    
    vectors = []
    metadata_file = os.path.join(outdir, 'recipe_metadata.jsonl')
    
    # Create output directory
    os.makedirs(outdir, exist_ok=True)
    
    # Open metadata file for writing
    with open(metadata_file, 'w', encoding='utf8') as meta_f:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing recipes"):
            try:
                recipe_id = str(row['id']) if 'id' in row else str(idx)
                title = str(row.get('title', ''))
                
                # Process ingredients
                ner = process_ner_field(row.get('NER', ''))
                ingredients_text = ' '.join(ner) if ner else ''
                
                # Create text for embedding
                embedding_text = f"{title} {ingredients_text}"
                
                # Generate embedding
                embedding = model.encode(embedding_text, show_progress_bar=False).tolist()
                
                # Prepare metadata for Pinecone
                metadata = {
                    'title': title,
                    'ingredients': ner,
                    'source': str(row.get('source', '')),
                    'link': str(row.get('link', '')),
                    'num_ingredients': len(ner)
                }
                
                # Add optional fields if present
                if 'directions' in row and pd.notna(row['directions']):
                    directions = row['directions']
                    if isinstance(directions, str):
                        try:
                            directions = json.loads(directions.replace("'", '"'))
                        except:
                            directions = [directions]
                    metadata['has_directions'] = True
                
                # Prepare vector for Pinecone
                vectors.append({
                    'id': recipe_id,
                    'values': embedding,
                    'metadata': metadata
                })
                
                # Write full recipe data to JSONL (for directions, etc.)
                recipe_data = {
                    'id': int(recipe_id) if recipe_id.isdigit() else idx,
                    'title': title,
                    'ingredients': ner,
                    'source': str(row.get('source', '')),
                    'link': str(row.get('link', '')),
                }
                
                if 'directions' in row and pd.notna(row['directions']):
                    recipe_data['directions'] = directions if isinstance(directions, list) else [str(directions)]
                
                meta_f.write(json.dumps(recipe_data) + '\n')
                
            except Exception as e:
                print(f"\n⚠️  Error processing recipe {idx}: {e}")
                continue
    
    print(f"✅ Prepared {len(vectors):,} vectors")
    print(f"✅ Saved metadata to: {metadata_file}")
    
    return vectors


def upsert_to_pinecone(index, vectors: List[Dict[str, Any]]):
    """Upload vectors to Pinecone in batches"""
    print(f"\n⬆️  Uploading {len(vectors):,} vectors to Pinecone...")
    
    batch = []
    uploaded = 0
    
    for vector in tqdm(vectors, desc="Uploading"):
        batch.append(vector)
        
        if len(batch) >= BATCH_SIZE:
            index.upsert(vectors=batch)
            uploaded += len(batch)
            batch = []
    
    # Upload remaining vectors
    if batch:
        index.upsert(vectors=batch)
        uploaded += len(batch)
    
    print(f"✅ Uploaded {uploaded:,} vectors to Pinecone")


def verify_upload(index):
    """Verify the upload was successful"""
    print(f"\n🔍 Verifying upload...")
    
    stats = index.describe_index_stats()
    total_count = stats.get('total_vector_count', 0)
    
    print(f"✅ Index stats:")
    print(f"   Total vectors: {total_count:,}")
    print(f"   Dimensions: {stats.get('dimension', 'unknown')}")
    
    # Test a sample query
    print(f"\n🧪 Testing sample query...")
    try:
        results = index.query(
            vector=[0.0] * EMBED_DIM,
            top_k=3,
            include_metadata=True
        )
        
        print(f"✅ Sample query successful!")
        if results.matches:
            print(f"   Found {len(results.matches)} results")
            for match in results.matches[:3]:
                print(f"   - {match.metadata.get('title', 'No title')}")
    except Exception as e:
        print(f"⚠️  Sample query failed: {e}")


def main():
    parser = argparse.ArgumentParser(description='Ingest recipes into Pinecone')
    parser.add_argument('--input', required=True, help='Path to input CSV file')
    parser.add_argument('--outdir', default='data', help='Output directory for metadata')
    parser.add_argument('--skip-upload', action='store_true', help='Skip uploading to Pinecone')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🍳 PINECONE RECIPE INGESTION FOR LEFTOVR APP")
    print("=" * 70)
    
    # Validate environment
    validate_environment()
    
    # Load data
    df = load_recipe_data(args.input)
    
    # Load embedding model
    model = load_embedding_model()
    
    # Prepare vectors
    vectors = prepare_vectors(df, model, args.outdir)
    
    if args.skip_upload:
        print("\n⏭️  Skipping Pinecone upload (--skip-upload flag)")
        return
    
    # Initialize Pinecone
    pc = initialize_pinecone()
    
    # Create or get index
    index = create_or_get_index(pc, PINECONE_INDEX_NAME)
    
    # Upload vectors
    upsert_to_pinecone(index, vectors)
    
    # Verify
    verify_upload(index)
    
    print("\n" + "=" * 70)
    print("✅ INGESTION COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   - Recipes processed: {len(df):,}")
    print(f"   - Vectors uploaded: {len(vectors):,}")
    print(f"   - Pinecone index: {PINECONE_INDEX_NAME}")
    print(f"   - Metadata saved to: {os.path.join(args.outdir, 'recipe_metadata.jsonl')}")
    print(f"\n💡 Next steps:")
    print(f"   1. Update your .env file with Pinecone credentials")
    print(f"   2. Run the backend: python api/server.py")
    print(f"   3. Test the recipe search!")


if __name__ == '__main__':
    main()
