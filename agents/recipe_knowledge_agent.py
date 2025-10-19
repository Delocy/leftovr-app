"""Recipe Knowledge Agent with Qdrant Vector Database

Uses Qdrant for vector search with better stability and features.

Installation:
    pip install qdrant-client sentence-transformers

Usage:
    agent = RecipeKnowledgeAgent(data_dir='data')
    agent.load_metadata()
    agent.load_ingredient_index()
    agent.setup_qdrant()
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Dict, Tuple, Optional, Iterable
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchAny

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


_UNIT_QTY_RE = re.compile(r'(^|\s)\d+\/?\d*\s*(cups?|cup|tbsp|tbs|tbsp\.|tsp|grams?|g|kg|oz|ounces?)', re.I)


def _normalize_token(tok: str) -> str:
    s = tok.lower().strip()
    s = _UNIT_QTY_RE.sub(' ', s)
    s = re.sub(r"[^\w\s]", '', s)
    s = s.strip()
    if s.endswith('es') and len(s) > 4:
        s = s[:-2]
    elif s.endswith('s') and len(s) > 3:
        s = s[:-1]
    return s


class RecipeKnowledgeAgent:
    def __init__(self, data_dir: str = 'data', qdrant_path: str = './qdrant_data') -> None:
        self.data_dir = data_dir
        self.qdrant_path = qdrant_path
        self.metadata: Dict[int, dict] = {}
        self.ingredient_index: Dict[str, List[int]] = {}
        self.qdrant_client = None
        self.embed_model = None
        self.embed_dim = None
        self.collection_name = "recipes"

    def load_metadata(self, path: Optional[str] = None) -> None:
        """Load recipe metadata from JSONL file"""
        path = path or os.path.join(self.data_dir, 'recipe_metadata.jsonl')
        if not os.path.exists(path):
            raise FileNotFoundError(f"Metadata file not found: {path}")
        self.metadata = {}
        with open(path, 'r', encoding='utf8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                obj = json.loads(line)
                self.metadata[int(obj['id'])] = obj
        print(f"✅ Loaded {len(self.metadata):,} recipes")

    def load_ingredient_index(self, path: Optional[str] = None) -> None:
        """Load ingredient inverted index"""
        path = path or os.path.join(self.data_dir, 'ingredient_index.json')
        if not os.path.exists(path):
            raise FileNotFoundError(f"Ingredient index not found: {path}")
        with open(path, 'r', encoding='utf8') as fh:
            self.ingredient_index = json.load(fh)
        self.ingredient_index = {k: [int(x) for x in v] for k, v in self.ingredient_index.items()}
        print(f"✅ Loaded {len(self.ingredient_index):,} ingredients")

    def setup_qdrant(self, embed_model_name: str = 'all-MiniLM-L6-v2', force_recreate: bool = False) -> None:
        """
        Initialize Qdrant client and create collection
        
        Args:
            embed_model_name: SentenceTransformer model name
            force_recreate: If True, delete and recreate collection
        """
        if SentenceTransformer is None:
            print("⚠️  sentence-transformers not available, semantic search disabled")
            return
        
        try:
            # Initialize client (embedded mode - no Docker needed!)
            print(f"🔧 Initializing Qdrant (embedded mode)...")
            self.qdrant_client = QdrantClient(path=self.qdrant_path)
            
            # Load embedding model
            print(f"📦 Loading embedding model: {embed_model_name}...")
            self.embed_model = SentenceTransformer(embed_model_name)
            self.embed_dim = self.embed_model.get_sentence_embedding_dimension()
            
            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)
            
            if collection_exists and not force_recreate:
                print(f"✅ Collection '{self.collection_name}' already exists")
                # Get collection info
                info = self.qdrant_client.get_collection(self.collection_name)
                print(f"   Vectors: {info.points_count:,}")
            else:
                if collection_exists and force_recreate:
                    print(f"🗑️  Deleting existing collection...")
                    self.qdrant_client.delete_collection(self.collection_name)
                
                # Create new collection
                print(f"📝 Creating collection '{self.collection_name}'...")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embed_dim,
                        distance=Distance.COSINE  # or Distance.DOT for normalized vectors
                    )
                )
                print(f"✅ Collection created (ready to ingest recipes)")
                
        except Exception as e:
            print(f"❌ Qdrant setup failed: {e}")
            self.qdrant_client = None

    def ingest_recipes_to_qdrant(self, recipe_ids: Optional[List[int]] = None, batch_size: int = 100) -> None:
        """
        Ingest recipes into Qdrant
        
        Args:
            recipe_ids: List of recipe IDs to ingest (None = all recipes)
            batch_size: Number of recipes to process at once
        """
        if self.qdrant_client is None or self.embed_model is None:
            print("❌ Qdrant not initialized. Call setup_qdrant() first")
            return
        
        if recipe_ids is None:
            recipe_ids = list(self.metadata.keys())
        
        print(f"\n🔄 Ingesting {len(recipe_ids):,} recipes to Qdrant...")
        
        points = []
        for i, rid in enumerate(recipe_ids):
            recipe = self.metadata.get(rid)
            if not recipe:
                continue
            
            # Build text for embedding (same as FAISS version)
            text = f"{recipe['title']}. Ingredients: {', '.join(recipe['ner'])}"
            
            # Create embedding
            embedding = self.embed_model.encode(text, normalize_embeddings=True).tolist()
            
            # Create point with metadata (payload)
            point = PointStruct(
                id=rid,
                vector=embedding,
                payload={
                    "title": recipe['title'],
                    "ingredients": recipe['ner'],
                    "source": recipe.get('source', ''),
                    "link": recipe.get('link', ''),
                }
            )
            points.append(point)
            
            # Upload in batches
            if len(points) >= batch_size or i == len(recipe_ids) - 1:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                points = []
                if (i + 1) % 1000 == 0:
                    print(f"   Ingested {i+1:,} / {len(recipe_ids):,} recipes...")
        
        print(f"✅ Ingestion complete!")

    def normalize_ingredients(self, items: Iterable[str]) -> List[str]:
        """Normalize ingredient names"""
        return [t for t in (_normalize_token(x) for x in items) if t]

    def pantry_candidates(self, pantry_items: Iterable[str], min_overlap: int = 1, top_k: int = 200) -> List[Tuple[int, float]]:
        """
        Find recipes using ingredient index (exact matching)
        
        Returns list of (recipe_id, overlap_score) sorted by score
        """
        pantry = set(self.normalize_ingredients(pantry_items))
        if not pantry:
            return []

        cand_scores: Dict[int, int] = {}
        for ing in pantry:
            ids = self.ingredient_index.get(ing) or []
            for rid in ids:
                cand_scores[rid] = cand_scores.get(rid, 0) + 1

        scored = []
        for rid, overlap in cand_scores.items():
            meta = self.metadata.get(rid)
            if not meta:
                continue
            ner = meta.get('ner', [])
            denom = max(1, len(ner))
            score = float(overlap) / denom
            if overlap >= min_overlap:
                scored.append((rid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def semantic_search(self, query: str, k: int = 10, filter_ingredients: Optional[List[str]] = None) -> List[Tuple[int, float]]:
        """
        Semantic search using Qdrant
        
        Args:
            query: Text query
            k: Number of results
            filter_ingredients: Optional list of required ingredients
            
        Returns list of (recipe_id, score)
        """
        if self.qdrant_client is None or self.embed_model is None:
            return []
        
        # Encode query
        query_vector = self.embed_model.encode(query, normalize_embeddings=True).tolist()
        
        # Build filter if ingredients specified
        search_filter = None
        if filter_ingredients:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="ingredients",
                        match=MatchAny(any=filter_ingredients)
                    )
                ]
            )
        
        # Search
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=k,
            query_filter=search_filter
        )
        
        return [(hit.id, hit.score) for hit in results]

    def hybrid_query(self, pantry_items: Iterable[str], query_text: str, top_k: int = 20) -> List[Tuple[dict, float]]:
        """
        Hybrid search combining ingredient matching and semantic similarity
        
        Returns list of (recipe_metadata, combined_score)
        """
        pantry_cands = self.pantry_candidates(pantry_items, min_overlap=1, top_k=500)
        sem_cands = self.semantic_search(query_text, k=500)

        score_map: Dict[int, float] = {}
        
        # Semantic scores
        for rid, s in sem_cands:
            score_map[rid] = score_map.get(rid, 0.0) + 0.6 * float(s)
        
        # Pantry overlap scores
        for rid, frac in pantry_cands:
            score_map[rid] = score_map.get(rid, 0.0) + 0.6 * float(frac) + 0.4

        ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.metadata.get(rid, {}), float(score)) for rid, score in ranked]


if __name__ == '__main__':
    print('RecipeKnowledgeAgent - Qdrant-based recipe retrieval')
    print('\nQuick start:')
    print('  agent = RecipeKnowledgeAgent()')
    print('  agent.load_metadata()')
    print('  agent.load_ingredient_index()')
    print('  agent.setup_qdrant()')
    print('  agent.ingest_recipes_to_qdrant(list(agent.metadata.keys())[:10000])  # Ingest 10k recipes')
