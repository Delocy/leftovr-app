"""Recipe Knowledge Agent with Zilliz Cloud (Milvus) Vector Database

Uses Zilliz Cloud (managed Milvus) for vector search with better stability and features.

Installation:
    pip install pymilvus sentence-transformers

Usage:
    agent = RecipeKnowledgeAgent(data_dir='data')
    agent.load_metadata()
    agent.load_ingredient_index()
    agent.setup_milvus()
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Dict, Tuple, Optional, Iterable, Set, Any
from pymilvus import MilvusClient, DataType

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
    def __init__(self, data_dir: str = 'data') -> None:
        self.data_dir = data_dir
        self.metadata: Dict[int, dict] = {}
        self.ingredient_index: Dict[str, List[int]] = {}
        self.milvus_client = None
        self.embed_model = None
        self.embed_dim = None
        self.collection_name = "recipes"
        self.pantry_agent = None  # Injected PantryAgent for inventory access

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

    def setup_milvus(self, embed_model_name: str = 'all-MiniLM-L6-v2') -> None:
        """
        Initialize Zilliz Cloud (Milvus) client and connect to existing collection

        Note: Collection must be created via ingest_recipes_milvus.py script first

        Args:
            embed_model_name: SentenceTransformer model name
        """
        if SentenceTransformer is None:
            print("⚠️  sentence-transformers not available, semantic search disabled")
            return

        try:
            # Get Zilliz Cloud credentials from environment
            ZILLIZ_CLUSTER_ENDPOINT = os.environ.get('ZILLIZ_CLUSTER_ENDPOINT')
            ZILLIZ_TOKEN = os.environ.get('ZILLIZ_TOKEN')
            
            if not ZILLIZ_CLUSTER_ENDPOINT or not ZILLIZ_TOKEN:
                print("❌ Error: ZILLIZ_CLUSTER_ENDPOINT and ZILLIZ_TOKEN env variables not set.")
                print("   Please set them before running with Milvus enabled")
                return

            # Initialize Zilliz Cloud client
            print(f"🔧 Connecting to Zilliz Cloud...")
            self.milvus_client = MilvusClient(uri=ZILLIZ_CLUSTER_ENDPOINT, token=ZILLIZ_TOKEN)

            # Load embedding model
            print(f"📦 Loading embedding model: {embed_model_name}...")
            self.embed_model = SentenceTransformer(embed_model_name)
            self.embed_dim = self.embed_model.get_sentence_embedding_dimension()

            # Check if collection exists
            collections = self.milvus_client.list_collections()
            collection_exists = self.collection_name in collections

            if collection_exists:
                print(f"✅ Connected to collection '{self.collection_name}'")
                # Get collection info
                stats = self.milvus_client.get_collection_stats(self.collection_name)
                print(f"   Vectors: {stats.get('row_count', 'unknown')}")
            else:
                print(f"❌ Collection '{self.collection_name}' not found!")
                print(f"   Please run: python scripts/ingest_recipes_milvus.py --input assets/full_dataset.csv --outdir data --build-milvus")
                self.milvus_client = None

        except Exception as e:
            print(f"❌ Zilliz Cloud setup failed: {e}")
            self.milvus_client = None

    def set_pantry_agent(self, pantry_agent) -> None:
        """
        Inject PantryAgent for inventory access.

        Args:
            pantry_agent: Instance of PantryAgent
        """
        self.pantry_agent = pantry_agent
        print(f"✅ Recipe Knowledge Agent: Pantry integration enabled")

    def get_pantry_items(self) -> List[str]:
        """
        Get current pantry items from injected PantryAgent.

        Returns:
            List of ingredient names from pantry
        """
        if not self.pantry_agent:
            print("⚠️ Recipe Knowledge Agent: No pantry agent connected")
            return []

        inventory = self.pantry_agent.get_inventory()
        pantry_items = [item.get('ingredient_name', '') for item in inventory]
        print(f"📦 Recipe Knowledge Agent: Retrieved {len(pantry_items)} items from pantry")
        return pantry_items

    def feasibility_with_pantry(
        self,
        recipe_meta: dict,
        allow_missing: int = 0
    ) -> Dict[str, Any]:
        """
        Check recipe feasibility using live pantry data.

        Args:
            recipe_meta: Recipe metadata with 'ner' field (ingredients)
            allow_missing: How many ingredients can be missing

        Returns:
            {feasible: bool, available: List[str], missing: List[str],
             num_available: int, num_missing: int}
        """
        if not self.pantry_agent:
            return {
                "feasible": False,
                "available": [],
                "missing": recipe_meta.get('ner', []),
                "num_available": 0,
                "num_missing": len(recipe_meta.get('ner', []))
            }

        pantry_items = set(self.normalize_ingredients(self.get_pantry_items()))
        recipe_ingredients = set(recipe_meta.get('ner', []))

        available = list(pantry_items & recipe_ingredients)
        missing = list(recipe_ingredients - pantry_items)

        return {
            "feasible": len(missing) <= allow_missing,
            "available": available,
            "missing": missing,
            "num_available": len(available),
            "num_missing": len(missing)
        }

    def normalize_ingredients(self, items: Iterable[str]) -> List[str]:
        """Normalize ingredient names"""
        return [t for t in (_normalize_token(x) for x in items) if t]

    def pantry_candidates(self, pantry_items: Iterable[str], allow_missing: int = 0, top_k: int = 200) -> List[Tuple[int, float, int, List[str]]]:
        """
        LEFTOVR MODE: Find recipes that use the MOST of your pantry items

        Philosophy: Using MORE leftovers = BETTER (not just coverage %)

        COMPLEMENTARY SIGNALS:
        • Exact match: "This recipe uses exactly these ingredients"
        • Semantic: "This recipe is similar to what you want"
        • Hybrid: "This recipe does BOTH!" (gets bonus points)

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

        # Find recipes that contain any pantry ingredients
        candidate_recipes: Set[int] = set()
        for ing in pantry:
            ids = self.ingredient_index.get(ing) or []
            candidate_recipes.update(ids)

        results = []
        for rid in candidate_recipes:
            meta = self.metadata.get(rid)
            if not meta:
                continue

            recipe_ingredients = set(meta.get('ner', []))
            if not recipe_ingredients:
                continue

            # Calculate how many UNIQUE pantry items this recipe uses
            num_pantry_used = len(pantry & recipe_ingredients)

            # Calculate missing ingredients
            missing = recipe_ingredients - pantry
            num_missing = len(missing)

            # Filter: only include if missing ingredients <= allowed
            if num_missing <= allow_missing:
                # LEFTOVR SCORING: Number of UNIQUE pantry items used (more = better)
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
        Semantic search using Zilliz Cloud (Milvus) with all-MiniLM-L6-v2 embeddings

        Model: all-MiniLM-L6-v2 (384 dimensions)
        - Understands semantic meaning of text
        - Can match ingredient combinations that work well together

        Args:
            query: Text description (e.g., "easy Italian pasta dinner")
            pantry_items: Your ingredient list (e.g., ['chicken', 'garlic', 'lemon'])
            k: Number of results
            filter_ingredients: Optional list of required ingredients (not yet supported)

        Note: You can provide query, pantry_items, or both!
              - query only: Find recipes matching description
              - pantry_items only: Find recipes with similar ingredients
              - both: Find recipes matching description AND similar ingredients

        Returns list of (recipe_id, similarity_score)
        """
        if self.milvus_client is None or self.embed_model is None:
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

        # Search using MilvusClient
        # Note: filter_ingredients filtering not yet implemented in simplified API
        results = self.milvus_client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=k,
            output_fields=["id"]
        )

        # Extract results (MilvusClient returns list of lists)
        if results and len(results) > 0:
            return [(hit['id'], hit['distance']) for hit in results[0]]
        return []
    def hybrid_query(
        self,
        pantry_items: Optional[Iterable[str]] = None,
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
            pantry_items: Your available ingredients (leftovers). If None, auto-pulls from PantryAgent
            query_text: What you feel like eating (e.g., "quick dinner", "Italian")
                       Optional - can search with just ingredients!
            top_k: Number of results to return
            allow_missing: How many ingredients you're willing to buy (0=none, 1-2=flexible)
            use_semantic: Whether to boost with semantic similarity

        Returns:
            List of (recipe_metadata, combined_score, num_pantry_used, missing_ingredients)

            recipe_metadata includes:
            - 'id': Recipe ID
            - 'title': Recipe name
            - 'ner': List of ingredients
            - 'directions': List of cooking steps
            - 'link': Source URL
            - 'source': Recipe source

        Philosophy:
            1. Prioritize using MORE leftovers (3 items > 1 item)
            2. Prefer recipes you can make NOW (zero shopping)
            3. Boost recipes semantically similar to your ingredients + preferences
        """
        # Auto-pull from pantry if not provided
        if pantry_items is None:
            if self.pantry_agent:
                print("📦 Recipe Knowledge Agent: Auto-loading pantry items...")
                pantry_items = self.get_pantry_items()
            else:
                print("⚠️ Recipe Knowledge Agent: No pantry items provided and no pantry agent connected")
                pantry_items = []

        pantry_list = list(pantry_items)

        # Get leftover-optimized candidates
        pantry_cands = self.pantry_candidates(
            pantry_list,
            allow_missing=allow_missing,
            top_k=500
        )

        # Get semantic matches if enabled
        sem_cands = []
        if use_semantic and self.milvus_client and self.embed_model:
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
    print('RecipeKnowledgeAgent - Zilliz Cloud (Milvus) based recipe retrieval')
    print('\nQuick start:')
    print('  # 1. First, ingest recipes using the dedicated script:')
    print('  #    python scripts/ingest_recipes_milvus.py --input assets/full_dataset.csv --outdir data --build-milvus')
    print('')
    print('  # 2. Then use the agent for search:')
    print('  agent = RecipeKnowledgeAgent()')
    print('  agent.load_metadata()')
    print('  agent.load_ingredient_index()')
    print('  agent.setup_milvus()')
    print('  # Now you can use semantic_search() and hybrid_query()')
