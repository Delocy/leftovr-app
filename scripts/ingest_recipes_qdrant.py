"""Ingestion script for recipe dataset with Qdrant support

Usage:
  # Just create metadata and ingredient index (fast)
  python scripts/ingest_recipes_qdrant.py --input assets/full_dataset.csv --outdir data

  # Also populate Qdrant with all recipes (slow - 3-4 hours for 2.2M recipes)
  python scripts/ingest_recipes_qdrant.py --input assets/full_dataset.csv --outdir data --build-qdrant

  # Process only first N recipes (for testing) - limits BOTH metadata AND Qdrant
  python scripts/ingest_recipes_qdrant.py --input assets/full_dataset.csv --outdir data --build-qdrant --sample 10000

Produces:
  - data/recipe_metadata.jsonl (recipe metadata)
  - data/ingredient_index.json (ingredient→recipe_ids mapping for fast lookup)
  - ./qdrant_data/ (vector database - if --build-qdrant used)

Note: --sample limits the total number of recipes processed (not just Qdrant ingestion)
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
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except Exception:
    SentenceTransformer = None
    QdrantClient = None


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
    build_qdrant: bool = False,
    qdrant_path: str = './qdrant_data',
    embed_model_name: str = 'all-MiniLM-L6-v2',
    sample_size: Optional[int] = None,
    batch_size: int = 100
):
    """
    Build recipe indices
    
    Args:
        input_path: Path to recipes CSV
        outdir: Output directory for metadata/ingredient index
        build_qdrant: Whether to build Qdrant vector index
        qdrant_path: Path for Qdrant storage
        embed_model_name: SentenceTransformer model name
        sample_size: If set, only ingest first N recipes into Qdrant
        batch_size: Batch size for Qdrant ingestion
    """
    os.makedirs(outdir, exist_ok=True)
    metadata_path = os.path.join(outdir, 'recipe_metadata.jsonl')
    ingredient_index = defaultdict(list)

    # Setup Qdrant if needed
    qdrant_client = None
    model = None
    if build_qdrant:
        if SentenceTransformer is None or QdrantClient is None:
            print("❌ Error: sentence-transformers and qdrant-client required for --build-qdrant")
            print("   Install with: pip install sentence-transformers qdrant-client")
            return
        
        print(f"🔧 Setting up Qdrant...")
        print(f"   Storage path: {qdrant_path}")
        qdrant_client = QdrantClient(path=qdrant_path)
        
        print(f"📦 Loading embedding model: {embed_model_name}...")
        model = SentenceTransformer(embed_model_name)
        embed_dim = model.get_sentence_embedding_dimension()
        
        # Create collection
        collection_name = "recipes"
        try:
            qdrant_client.delete_collection(collection_name)
            print(f"   Deleted existing '{collection_name}' collection")
        except:
            pass
        
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=embed_dim, distance=Distance.COSINE)
        )
        print(f"✅ Created '{collection_name}' collection")

    # Process recipes
    print(f"\n📂 Processing recipes from {input_path}...")
    if sample_size:
        print(f"   📏 Sample mode: Processing first {sample_size:,} recipes only")
    
    count = 0
    qdrant_count = 0
    points_batch = []
    
    # Limit the iterator if sample_size is specified
    recipe_rows = read_csv_rows(input_path)
    if sample_size is not None:
        recipe_rows = islice(recipe_rows, sample_size)
    
    with open(metadata_path, 'w', encoding='utf8') as meta_fh:
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
                'directions': directions_list,  # Add directions!
            }
            meta_fh.write(json.dumps(meta) + '\n')

            # Build ingredient index
            for t in ner_norm:
                ingredient_index[t].append(rid)

            # Add to Qdrant (if enabled)
            if build_qdrant:
                # Create embedding text
                title = row.get('title') or ''
                ingredients = ', '.join(ner_norm)
                text = f"{title}. Ingredients: {ingredients}"
                
                # Create embedding
                embedding = model.encode(text, normalize_embeddings=True).tolist()
                
                # Create point
                point = PointStruct(
                    id=rid,
                    vector=embedding,
                    payload={
                        "title": meta['title'],
                        "ingredients": ner_norm,
                        "source": meta['source'],
                        "link": meta['link'],
                    }
                )
                points_batch.append(point)
                qdrant_count += 1
                
                # Upload batch
                if len(points_batch) >= batch_size:
                    qdrant_client.upsert(collection_name="recipes", points=points_batch)
                    points_batch = []
                    if qdrant_count % 1000 == 0:
                        print(f"   📥 Ingested {qdrant_count:,} vectors into Qdrant...")

    # Upload remaining points
    if build_qdrant and points_batch:
        qdrant_client.upsert(collection_name="recipes", points=points_batch)
    
    print(f"\n✅ Finished processing {count:,} recipes")
    
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
    if build_qdrant:
        print(f'🔍 Qdrant vectors: {qdrant_path} ({qdrant_count:,} vectors)')


def main():
    p = argparse.ArgumentParser(description='Ingest recipes and build search indices')
    p.add_argument('--input', required=True, help='Path to recipes CSV')
    p.add_argument('--outdir', default='data', help='Output directory for metadata/indices')
    p.add_argument('--build-qdrant', action='store_true', help='Build Qdrant vector index')
    p.add_argument('--qdrant-path', default='./qdrant_data', help='Path for Qdrant storage')
    p.add_argument('--embed-model', default='all-MiniLM-L6-v2', help='SentenceTransformer model name')
    p.add_argument('--sample', type=int, help='Only ingest first N recipes into Qdrant (for testing)')
    p.add_argument('--batch-size', type=int, default=100, help='Batch size for Qdrant ingestion')
    args = p.parse_args()
    
    build_indices(
        input_path=args.input,
        outdir=args.outdir,
        build_qdrant=args.build_qdrant,
        qdrant_path=args.qdrant_path,
        embed_model_name=args.embed_model,
        sample_size=args.sample,
        batch_size=args.batch_size
    )


if __name__ == '__main__':
    main()
