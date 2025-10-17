"""Ingestion script for recipe dataset

Usage:
  python scripts/ingest_recipes.py --input path/to/recipes.csv --outdir data --build-faiss

Produces:
  - data/recipe_metadata.jsonl
  - data/ingredient_index.json
  - optionally data/recipe_index.faiss (if sentence-transformers and faiss installed)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import defaultdict
from typing import List

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except Exception:
    SentenceTransformer = None  # type: ignore
    faiss = None  # type: ignore


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
    # naive reader that yields dicts; supports large files by streaming
    with open(path, newline='', encoding='utf8') as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            # Handle unnamed first column or missing 'index' column
            if 'index' not in row and '' in row:
                row['index'] = row['']  # use unnamed column as index
            elif 'index' not in row:
                row['index'] = str(idx)  # fallback to enumerate index
            yield row


def build_indices(input_path: str, outdir: str, build_faiss: bool = False, embed_model_name: str = 'all-MiniLM-L6-v2'):
    os.makedirs(outdir, exist_ok=True)
    metadata_path = os.path.join(outdir, 'recipe_metadata.jsonl')
    ingredient_index = defaultdict(list)

    # If building faiss, prepare lists
    build_emb = build_faiss and SentenceTransformer is not None and faiss is not None
    if build_emb:
        print(f"Loading embedding model: {embed_model_name}...")
        model = SentenceTransformer(embed_model_name)
        texts = []
        ids = []

    print(f"Processing recipes from {input_path}...")
    count = 0
    with open(metadata_path, 'w', encoding='utf8') as meta_fh:
        for row in read_csv_rows(input_path):
            count += 1
            if count % 10000 == 0:
                print(f"Processed {count:,} recipes...")
            # expected columns: index,title,ingredients,directions,link,source,NER
            rid = int(row['index'])
            ner_raw = row.get('NER') or ''
            # assume NER column is JSON-like list or comma separated
            try:
                ner_list = json.loads(ner_raw) if ner_raw.strip().startswith('[') else [x.strip() for x in ner_raw.split(',') if x.strip()]
            except Exception:
                ner_list = [x.strip() for x in ner_raw.split(',') if x.strip()]

            ner_norm = [normalize_token(x) for x in ner_list if x]
            meta = {
                'id': rid,
                'title': row.get('title') or '',
                'link': row.get('link') or '',
                'source': row.get('source') or '',
                'ner': ner_norm,
            }
            meta_fh.write(json.dumps(meta) + '\n')

            for t in ner_norm:
                ingredient_index[t].append(rid)

            if build_emb:
                txt = (row.get('title') or '') + '. Ingredients: ' + (row.get('ingredients') or '') + '. Directions: ' + (row.get('directions') or '')
                texts.append(txt)
                ids.append(rid)

    print(f"\nFinished processing {count:,} recipes")
    
    # write ingredient index
    print("Writing ingredient index...")
    ing_path = os.path.join(outdir, 'ingredient_index.json')
    with open(ing_path, 'w', encoding='utf8') as fh:
        json.dump(ingredient_index, fh)

    # optionally build FAISS
    if build_emb:
        print(f"Building FAISS index with {len(texts):,} embeddings...")
        print("This may take 30-60 minutes for large datasets...")
        dim = model.get_sentence_embedding_dimension()
        import numpy as np
        embs = model.encode(texts, convert_to_numpy=True, show_progress_bar=True, normalize_embeddings=True, batch_size=32)
        # build flat index with ids
        print("Creating FAISS index...")
        index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
        index.add_with_ids(embs, np.array(ids, dtype='int64'))
        faiss_path = os.path.join(outdir, 'recipe_index.faiss')
        print(f"Saving FAISS index to {faiss_path}...")
        faiss.write_index(index, faiss_path)

    print('\n✅ Done!')
    print(f'Wrote metadata to {metadata_path}')
    print(f'Wrote ingredient index to {ing_path}')
    if build_emb:
        print(f'Wrote faiss index to {os.path.join(outdir, "recipe_index.faiss")}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Path to recipes CSV')
    p.add_argument('--outdir', default='data', help='Output directory')
    p.add_argument('--build-faiss', action='store_true', help='Build FAISS index (requires sentence-transformers + faiss)')
    p.add_argument('--embed-model', default='all-MiniLM-L6-v2', help='SentenceTransformer model name')
    args = p.parse_args()
    build_indices(args.input, args.outdir, build_faiss=args.build_faiss, embed_model_name=args.embed_model)


if __name__ == '__main__':
    main()
