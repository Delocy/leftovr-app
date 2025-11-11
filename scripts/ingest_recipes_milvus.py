"""Ingestion script for recipe dataset with Zilliz Cloud (Milvus) support
   using the modern MilvusClient API.

Usage:
  # 1. Set your Zilliz Cloud credentials as environment variables:
  #    export ZILLIZ_CLOUD_URI="https://your-cluster-endpoint.zillizcloud.com"
  #    export ZILLIZ_CLOUD_TOKEN="your-api-key"
  #
  # 2. Install dependencies:
  #    pip install pymilvus sentence-transformers
  #
  # 3. Run the script:

  # Just create metadata and ingredient index (fast)
  python scripts/ingest_recipes_milvus.py --input assets/full_dataset.csv --outdir data

  # Also populate Zilliz Cloud with all recipes (slow)
  python scripts/ingest_recipes_milvus.py --input assets/full_dataset.csv --outdir data --build-milvus

  # Process only first N recipes (for testing)
  python scripts/ingest_recipes_milvus.py --input assets/full_dataset.csv --outdir data --build-milvus --sample 10000

Produces:
  - data/recipe_metadata.jsonl (recipe metadata)
  - data/ingredient_index.json (ingredient→recipe_ids mapping for fast lookup)
  - A collection named "recipes" in your Zilliz Cloud cluster (if --build-milvus used)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import defaultdict
from itertools import islice
from typing import List, Optional

try:
    from sentence_transformers import SentenceTransformer
    from pymilvus import MilvusClient, FieldSchema, CollectionSchema, DataType
except Exception:
    SentenceTransformer = None
    MilvusClient = None


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
    build_milvus: bool = False,
    embed_model_name: str = 'all-MiniLM-L6-v2',
    sample_size: Optional[int] = None,
    batch_size: int = 100,
    offset: int = 0
):
    """
    Build recipe indices
    
    Args:
        input_path: Path to recipes CSV
        outdir: Output directory for metadata/ingredient index
        build_milvus: Whether to build Milvus vector index
        embed_model_name: SentenceTransformer model name
        sample_size: If set, only ingest first N recipes
        batch_size: Batch size for Milvus ingestion
        offset: Number of rows to skip from the beginning
    """
    os.makedirs(outdir, exist_ok=True)
    
    # Handle metadata file in append mode if resuming
    metadata_path = os.path.join(outdir, 'recipe_metadata.jsonl')
    file_mode = 'a' if offset > 0 else 'w'
    if offset > 0:
        print(f"   ℹ️  Appending to existing metadata file")
    
    ingredient_index = defaultdict(list)

    # Setup Milvus if needed
    client = None
    model = None
    if build_milvus:
        if SentenceTransformer is None or MilvusClient is None:
            print("❌ Error: sentence-transformers and pymilvus required for --build-milvus")
            print("   Install with: pip install sentence-transformers pymilvus")
            return
        
        # 1. Get Zilliz Cloud credentials
        ZILLIZ_CLUSTER_ENDPOINT = os.environ.get('ZILLIZ_CLUSTER_ENDPOINT')
        ZILLIZ_TOKEN = os.environ.get('ZILLIZ_TOKEN')
        
        if not ZILLIZ_CLUSTER_ENDPOINT or not ZILLIZ_TOKEN:
            print("❌ Error: ZILLIZ_CLUSTER_ENDPOINT and ZILLIZ_TOKEN env variables not set.")
            print("   Please set them before running with --build-milvus")
            return

        print(f"🔧 Setting up Zilliz Cloud (Milvus) connection...")
        try:
            client = MilvusClient(uri=ZILLIZ_CLUSTER_ENDPOINT, token=ZILLIZ_TOKEN)
            print("   ✅ Connected to Zilliz Cloud")
        except Exception as e:
            print(f"   ❌ Failed to connect to Zilliz Cloud: {e}")
            return
        
        print(f"📦 Loading embedding model: {embed_model_name}...")
        model = SentenceTransformer(embed_model_name)
        embed_dim = model.get_sentence_embedding_dimension()
        
        # 2. Define Collection Schema
        collection_name = "recipes"
        
        # Don't drop collection if we're resuming from an offset
        if offset == 0:
            # Drop old collection if it exists
            try:
                if collection_name in client.list_collections():
                    client.drop_collection(collection_name)
                    print(f"   Deleted existing '{collection_name}' collection")
            except Exception as e:
                print(f"   Could not delete existing collection (may not exist): {e}")
                pass
        else:
            print(f"   ⚠️  Resuming ingestion from row {offset:,} - NOT dropping existing collection")
        
        # Define fields
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="ingredients", dtype=DataType.ARRAY, element_type=DataType.VARCHAR, max_capacity=500, max_length=256),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="link", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=embed_dim)
        ]
        schema = CollectionSchema(fields=fields, description="Recipe collection")
        
        # 3. Create Collection (only if it doesn't exist)
        if collection_name not in client.list_collections():
            client.create_collection(
                collection_name=collection_name,
                schema=schema,
                consistency_level="Strong" # Good default
            )
            print(f"   ✅ Created '{collection_name}' collection")
        else:
            print(f"   ℹ️  Using existing '{collection_name}' collection")
        
        # 4. Create Index (if not already exists)
        print("   Creating vector index (AUTOINDEX, COSINE)...")
        try:
            index_params = client.prepare_index_params(
                field_name="embedding",
                metric_type="COSINE",
                index_type="AUTOINDEX",
            )
            client.create_index(
                collection_name=collection_name,
                index_params=index_params
            )
        except Exception as e:
            print(f"   ℹ️  Index may already exist: {e}")
        
        client.load_collection(collection_name=collection_name)
        print("   ✅ Index created and collection loaded.")


    # Process recipes
    print(f"\n📂 Processing recipes from {input_path}...")
    if offset > 0:
        print(f"   ⏩ Skipping first {offset:,} rows (resuming from row {offset:,})")
    if sample_size:
        print(f"   📏 Sample mode: Processing {sample_size:,} recipes after offset")
    
    count = 0
    milvus_count = 0
    skipped = 0
    
    # Batch list for Milvus insertion (list of dictionaries)
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
            for t in ner_norm:
                ingredient_index[t].append(rid)

            # Add to Milvus (if enabled)
            if build_milvus:
                # Truncate ingredient list if too long (safety check)
                MAX_INGREDIENTS = 500
                ingredients_for_milvus = ner_norm[:MAX_INGREDIENTS] if len(ner_norm) > MAX_INGREDIENTS else ner_norm
                
                # Create embedding text
                title = meta['title']
                ingredients_str = ', '.join(ingredients_for_milvus)
                text = f"{title}. Ingredients: {ingredients_str}"
                
                # Create embedding
                embedding = model.encode(text, normalize_embeddings=True).tolist()
                
                # Append data as a dictionary
                data_batch.append({
                    "id": rid,
                    "title": meta['title'],
                    "ingredients": ingredients_for_milvus,
                    "source": meta['source'],
                    "link": meta['link'],
                    "embedding": embedding
                })
                
                milvus_count += 1
                
                # Upload batch
                if len(data_batch) >= batch_size:
                    client.insert(collection_name=collection_name, data=data_batch)
                    data_batch = [] # Clear batch
                    
                    if milvus_count % 1000 == 0:
                        print(f"   📥 Ingested {milvus_count:,} vectors into Milvus...")

    # Upload remaining points
    if build_milvus and data_batch:
        client.insert(collection_name=collection_name, data=data_batch)
        print(f"   📥 Ingested final batch of {len(data_batch)} vectors.")
    
    print(f"\n✅ Finished processing {count:,} recipes")
    
    # Flush and disconnect
    if build_milvus:
        print("   Flushing data to disk...")
        client.flush(collection_name=collection_name)
        client.close()
        print("   Disconnected from Zilliz Cloud.")
    
    # Write ingredient index
    print("💾 Writing ingredient index...")
    ing_path = os.path.join(outdir, 'ingredient_index.json')
    with open(ing_path, 'w', encoding='utf8') as fh:
        json.dump(ingredient_index, fh)

    # Summary
    print('\n' + '='*60)
    print('✅ INGESTION COMPLETE!')
    print('='*60)
    print(f'📄 Metadata: {metadata_path} ({count:,} recipes)')
    print(f'📇 Ingredient index: {ing_path} ({len(ingredient_index):,} ingredients)')
    if build_milvus:
        print(f'☁️ Zilliz Cloud vectors: {milvus_count:,} vectors in "recipes" collection')


def main():
    p = argparse.ArgumentParser(description='Ingest recipes and build search indices')
    p.add_argument('--input', required=True, help='Path to recipes CSV')
    p.add_argument('--outdir', default='data', help='Output directory for metadata/indices')
    p.add_argument('--build-milvus', action='store_true', help='Build Milvus vector index in Zilliz Cloud')
    p.add_argument('--embed-model', default='all-MiniLM-L6-v2', help='SentenceTransformer model name')
    p.add_argument('--sample', type=int, help='Only ingest N recipes (for testing)')
    p.add_argument('--offset', type=int, default=0, help='Skip first N rows (for resuming)')
    p.add_argument('--batch-size', type=int, default=100, help='Batch size for Milvus ingestion')
    args = p.parse_args()
    
    build_indices(
        input_path=args.input,
        outdir=args.outdir,
        build_milvus=args.build_milvus,
        embed_model_name=args.embed_model,
        sample_size=args.sample,
        batch_size=args.batch_size,
        offset=args.offset
    )


if __name__ == '__main__':
    main()