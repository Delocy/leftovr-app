"""Ingestion script for recipe dataset with Pinecone support

Usage:
  # 1. Set your Pinecone API key in .env file:
  #    PINECONE_API_KEY="your-api-key"
  #
  # 2. Install dependencies:
  #    pip install pinecone sentence-transformers python-dotenv
  #
  # 3. Run the script:

  # Create metadata, ingredient index, and populate Pinecone
  python scripts/ingest_recipes_pinecone.py --input assets/full_dataset.csv --outdir data

  # Process only first N recipes (for testing)
  python scripts/ingest_recipes_pinecone.py --input assets/full_dataset.csv --outdir data --sample 10000

Produces:
  - data/recipe_metadata.jsonl (recipe metadata)
  - data/ingredient_index.json (ingredient→recipe_ids mapping for fast lookup)
  - An index named "leftovr-recipes" in your Pinecone account
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from collections import defaultdict
from itertools import islice
from typing import List, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

try:
    from sentence_transformers import SentenceTransformer
    from pinecone import Pinecone, ServerlessSpec
except Exception:
    SentenceTransformer = None
    Pinecone = None


UNIT_QTY_RE = re.compile(r'(^|\s)\d+\/?\d*\s*(cups?|cup|tbsp|tbs|tbsp\.|tsp|grams?|g|kg|oz|ounces?)', re.I)


def normalize_token(tok: str) -> str:
    s = tok.lower().strip()
    s = UNIT_QTY_RE.sub(' ', s)
    s = re.sub(r'[^\w\s]', '', s)
    s = s.strip()
    if s.endswith('es') and len(s) > 4:
        s = s[:-2]
    elif s.endswith('s') and len(s) > 3:
        s = s[:-1]
    return s


def read_csv_rows(path: str):
    """Stream CSV rows one at a time to handle large files"""
    with open(path, newline='', encoding='utf8') as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            # Handle unnamed first column or missing 'index' column
            if 'index' not in row and '' in row:
                row['index'] = row['']
            elif 'index' not in row:
                row['index'] = str(idx)
            yield row


def build_indices(
    input_path: str,
    outdir: str,
    embed_model_name: str = 'all-MiniLM-L6-v2',
    sample_size: Optional[int] = None,
    batch_size: int = 100,
    offset: int = 0
):
    """
    Build recipe indices and upload to Pinecone
    
    Args:
        input_path: Path to recipes CSV
        outdir: Output directory for metadata/ingredient index
        embed_model_name: SentenceTransformer model name
        sample_size: If set, only ingest first N recipes
        batch_size: Batch size for Pinecone upserts
        offset: Number of rows to skip from the beginning
    """
    os.makedirs(outdir, exist_ok=True)
    
    # Handle metadata file in append mode if resuming
    metadata_path = os.path.join(outdir, 'recipe_metadata.jsonl')
    file_mode = 'a' if offset > 0 else 'w'
    if offset > 0:
        print(f"   ℹ️  Appending to existing metadata file")
    
    ingredient_index = defaultdict(list)

    # Setup Pinecone
    pc = None
    index = None
    model = None
    
    if SentenceTransformer is None or Pinecone is None:
        print("❌ Error: sentence-transformers and pinecone-client required")
        print("   Install with: pip install sentence-transformers pinecone-client")
        return
    
    # 1. Get Pinecone credentials
    PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
    
    if not PINECONE_API_KEY:
        print("❌ Error: PINECONE_API_KEY env variable not set.")
        print("   Please set it before running")
        return

    print(f"🔧 Setting up Pinecone connection...")
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        print("   ✅ Connected to Pinecone")
    except Exception as e:
        print(f"   ❌ Failed to connect to Pinecone: {e}")
        return
    
    print(f"📦 Loading embedding model: {embed_model_name}...")
    model = SentenceTransformer(embed_model_name)
    embed_dim = model.get_sentence_embedding_dimension()
    
    # 2. Create or connect to index
    index_name = "leftovr-recipes"
    
    # Check if index exists
    existing_indexes = pc.list_indexes()
    index_names = [idx['name'] for idx in existing_indexes]
    
    if index_name not in index_names:
        print(f"   Creating new Pinecone index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=embed_dim,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        # Wait for index to be ready
        print("   ⏳ Waiting for index to be ready...")
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
        print(f"   ✅ Created '{index_name}' index")
    else:
        print(f"   ℹ️  Using existing '{index_name}' index")
    
    # Connect to the index
    index = pc.Index(index_name)
    print(f"   ✅ Connected to index '{index_name}'")

    # Process recipes
    print(f"\n📂 Processing recipes from {input_path}...")
    if offset > 0:
        print(f"   ⏩ Skipping first {offset:,} rows (resuming from row {offset:,})")
    if sample_size:
        print(f"   📏 Sample mode: Processing {sample_size:,} recipes after offset")
    
    count = 0
    pinecone_count = 0
    skipped = 0
    
    # Batch list for Pinecone upserts
    data_batch = []
    
    # Get all recipe rows
    recipe_rows = read_csv_rows(input_path)
    
    # Skip offset rows
    if offset > 0:
        recipe_rows = islice(recipe_rows, offset, None)
    
    # Limit the iterator if sample_size is specified
    if sample_size is not None:
        recipe_rows = islice(recipe_rows, sample_size)
    
    with open(metadata_path, file_mode, encoding='utf8') as meta_fh:
        for row in recipe_rows:
            count += 1
            if count % 10000 == 0:
                print(f"   Processed {count:,} recipes...")
            
            # Parse recipe data
            rid = int(row['index'])
            ner_raw = row.get('NER') or ''
            try:
                ner_list = json.loads(ner_raw) if ner_raw.strip().startswith('[') else [x.strip() for x in ner_raw.split(',') if x.strip()]
            except Exception:
                ner_list = [x.strip() for x in ner_raw.split(',') if x.strip()]

            ner_norm = [normalize_token(x) for x in ner_list if x]
            
            # Parse directions
            directions_raw = row.get('directions') or ''
            try:
                directions_list = json.loads(directions_raw) if directions_raw.strip().startswith('[') else [directions_raw]
            except Exception:
                directions_list = [directions_raw] if directions_raw else []
            
            # Build metadata
            meta = {
                'id': rid,
                'title': row.get('title') or '',
                'link': row.get('link') or '',
                'source': row.get('source') or '',
                'ner': ner_norm,
                'directions': directions_list,
            }
            meta_fh.write(json.dumps(meta) + '\n')
            
            # Build ingredient index
            for ing in ner_norm:
                if ing:
                    ingredient_index[ing].append(rid)
            
            # Prepare for Pinecone
            if not ner_norm:
                skipped += 1
                continue
            
            # Create embedding text (same format as agent uses)
            title = row.get('title') or ''
            embed_text = f"Ingredients: {', '.join(ner_norm)}"
            if title:
                embed_text = f"{title}. {embed_text}"
            
            # Generate embedding
            embedding = model.encode(embed_text, normalize_embeddings=True).tolist()
            
            # Add to batch
            data_batch.append({
                'id': str(rid),
                'values': embedding,
                'metadata': {
                    'title': row.get('title') or '',
                    'ingredients': ner_norm,
                    'source': row.get('source') or '',
                    'link': row.get('link') or ''
                }
            })
            
            # Upsert batch when full
            if len(data_batch) >= batch_size:
                try:
                    index.upsert(vectors=data_batch)
                    pinecone_count += len(data_batch)
                    data_batch = []
                except Exception as e:
                    print(f"   ❌ Error upserting batch: {e}")
                    data_batch = []
    
    # Upsert remaining batch
    if data_batch:
        try:
            index.upsert(vectors=data_batch)
            pinecone_count += len(data_batch)
        except Exception as e:
            print(f"   ❌ Error upserting final batch: {e}")

    print(f"\n✅ Processing complete!")
    print(f"   - Processed {count:,} recipes")
    print(f"   - Uploaded {pinecone_count:,} recipes to Pinecone")
    print(f"   - Skipped {skipped:,} recipes (no ingredients)")
    
    # Write ingredient index
    ingredient_index_path = os.path.join(outdir, 'ingredient_index.json')
    with open(ingredient_index_path, 'w', encoding='utf8') as fh:
        json.dump(ingredient_index, fh, indent=2)
    
    print(f"   - Created ingredient index: {ingredient_index_path}")
    print(f"   - Created metadata file: {metadata_path}")
    
    # Show index stats
    stats = index.describe_index_stats()
    print(f"\n📊 Pinecone Index Stats:")
    print(f"   - Total vectors: {stats.get('total_vector_count', 0):,}")
    print(f"   - Dimension: {stats.get('dimension', 0)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest recipe dataset into Pinecone')
    parser.add_argument('--input', required=True, help='Path to recipes CSV')
    parser.add_argument('--outdir', default='data', help='Output directory for metadata/index')
    parser.add_argument('--embed-model', default='all-MiniLM-L6-v2', help='SentenceTransformer model name')
    parser.add_argument('--sample', type=int, help='Only ingest first N recipes (for testing)')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for Pinecone upserts')
    parser.add_argument('--offset', type=int, default=0, help='Skip first N rows (for resuming)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🍳 Leftovr Recipe Ingestion - Pinecone Edition")
    print("=" * 70)
    
    build_indices(
        input_path=args.input,
        outdir=args.outdir,
        embed_model_name=args.embed_model,
        sample_size=args.sample,
        batch_size=args.batch_size,
        offset=args.offset
    )
    
    print("\n" + "=" * 70)
    print("✅ Done! Your recipes are ready in Pinecone.")
    print("=" * 70)
