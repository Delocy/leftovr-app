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

    def pantry_candidates(self, pantry_items: Iterable[str], allow_missing: int = 0, top_k: int = 200) -> List[Tuple[int, float, int, List[str]]]:
        """
        LEFTOVR MODE: Find recipes that use the MOST of your pantry items
        
        Philosophy: Using MORE leftovers = BETTER (not just coverage %)
        
        Args:
            pantry_items: Your available ingredients/leftovers
            allow_missing: 0 = only recipes you can make now, 1-2 = willing to shop
            top_k: Maximum results
            
        Returns:
            List of (recipe_id, score, num_pantry_used, missing_ingredients)
        """
        pantry = set(self.normalize_ingredients(pantry_items))
        if not pantry:
            return []

        cand_scores: Dict[int, int] = {}
        for ing in pantry:
            ids = self.ingredient_index.get(ing) or []
            for rid in ids:
                cand_scores[rid] = cand_scores.get(rid, 0) + 1

        results = []
        for rid, num_pantry_used in cand_scores.items():
            meta = self.metadata.get(rid)
            if not meta:
                continue
            
            recipe_ingredients = set(meta.get('ner', []))
            if not recipe_ingredients:
                continue
            
            # Calculate missing ingredients
            missing = recipe_ingredients - pantry
            num_missing = len(missing)
            
            # Filter: only include if missing ingredients <= allowed
            if num_missing <= allow_missing:
                # LEFTOVR SCORING: Number of pantry items used (more = better)
                # Bonus for recipes you can make now (0 missing)
                score = num_pantry_used * 100 + (1000 if num_missing == 0 else 0) - len(recipe_ingredients)
                results.append((rid, float(score), num_pantry_used, list(missing)))
        
        # Sort by score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def semantic_search(
        self, 
        query: Optional[str] = None,
        pantry_items: Optional[List[str]] = None,
        k: int = 10, 
        filter_ingredients: Optional[List[str]] = None
    ) -> List[Tuple[int, float]]:
        """
        Semantic search using Qdrant with all-MiniLM-L6-v2 embeddings
        
        Model: all-MiniLM-L6-v2 (384 dimensions)
        - Understands semantic meaning of text
        - Can match ingredient combinations that work well together
        
        Args:
            query: Text description (e.g., "easy Italian pasta dinner")
            pantry_items: Your ingredient list (e.g., ['chicken', 'garlic', 'lemon'])
            k: Number of results
            filter_ingredients: Optional list of required ingredients
            
        Note: You can provide query, pantry_items, or both!
              - query only: Find recipes matching description
              - pantry_items only: Find recipes with similar ingredients
              - both: Find recipes matching description AND similar ingredients
            
        Returns list of (recipe_id, similarity_score)
        """
        if self.qdrant_client is None or self.embed_model is None:
            return []
        
        # Build query text from provided inputs
        query_parts = []
        if query:
            query_parts.append(query)
        if pantry_items:
            # Format like recipe embeddings: "Ingredients: chicken, garlic, lemon"
            query_parts.append(f"Ingredients: {', '.join(pantry_items)}")
        
        if not query_parts:
            print("⚠️  No query or pantry_items provided for semantic search")
            return []
        
        query_text = ". ".join(query_parts)
        
        # Encode query using the same model (all-MiniLM-L6-v2)
        query_vector = self.embed_model.encode(query_text, normalize_embeddings=True).tolist()
        
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
    def hybrid_query(
        self, 
        pantry_items: Iterable[str], 
        query_text: Optional[str] = None,
        top_k: int = 20,
        allow_missing: int = 0,
        use_semantic: bool = True
    ) -> List[Tuple[dict, float, int, List[str]]]:
        """
        LEFTOVR HYBRID: Find recipes using semantic search + LEFTOVR scoring
        
        Uses all-MiniLM-L6-v2 to find recipes semantically similar to:
        - Your ingredients (pantry_items)
        - Your preferences (query_text) - optional!
        
        Args:
            pantry_items: Your available ingredients (leftovers)
            query_text: What you feel like eating (e.g., "quick dinner", "Italian")
                       Optional - can search with just ingredients!
            top_k: Number of results to return
            allow_missing: How many ingredients you're willing to buy (0=none, 1-2=flexible)
            use_semantic: Whether to boost with semantic similarity
        
        Returns:
            List of (recipe_metadata, combined_score, num_pantry_used, missing_ingredients)
            
        Philosophy:
            1. Prioritize using MORE leftovers (3 items > 1 item)
            2. Prefer recipes you can make NOW (zero shopping)
            3. Boost recipes semantically similar to your ingredients + preferences
        """
        pantry_list = list(pantry_items)
        
        # Get leftover-optimized candidates
        pantry_cands = self.pantry_candidates(
            pantry_list, 
            allow_missing=allow_missing,
            top_k=500
        )
        
        # Get semantic matches if enabled
        sem_cands = []
        if use_semantic and self.qdrant_client and self.embed_model:
            # Pass BOTH query text AND pantry items to semantic search!
            # The model finds recipes similar to your ingredients + preferences
            sem_cands = self.semantic_search(
                query=query_text,
                pantry_items=pantry_list,
                k=500
            )

        # Build combined scores
        score_map: Dict[int, Tuple[float, int, List[str]]] = {}  # rid -> (score, num_used, missing)
        
        # Start with leftover scores (already optimized)
        for rid, leftover_score, num_used, missing in pantry_cands:
            score_map[rid] = (leftover_score, num_used, missing)
        
        # Boost with semantic similarity if available
        if sem_cands:
            for rid, sem_score in sem_cands:
                if rid in score_map:
                    current_score, num_used, missing = score_map[rid]
                    # Add semantic bonus (scaled to be meaningful but not dominant)
                    # Max semantic boost: ~50 points (less than using 1 extra ingredient = 100 points)
                    boosted_score = current_score + (sem_score * 50)
                    score_map[rid] = (boosted_score, num_used, missing)
        
        # Sort and return
        ranked = sorted(score_map.items(), key=lambda x: x[1][0], reverse=True)[:top_k]
        return [
            (self.metadata.get(rid, {}), float(score), num_used, missing) 
            for rid, (score, num_used, missing) in ranked
        ]


if __name__ == '__main__':
    print('RecipeKnowledgeAgent - Qdrant-based recipe retrieval')
    print('\nQuick start:')
    print('  agent = RecipeKnowledgeAgent()')
    print('  agent.load_metadata()')
    print('  agent.load_ingredient_index()')
    print('  agent.setup_qdrant()')
    print('  agent.ingest_recipes_to_qdrant(list(agent.metadata.keys())[:10000])  # Ingest 10k recipes')
