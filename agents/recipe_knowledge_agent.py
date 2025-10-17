"""Recipe Knowledge Agent

Provides retrieval helpers for pantry-first and hybrid retrieval.
This module expects precomputed metadata JSONL and an ingredient inverted index
produced by the ingestion script. Embedding-based search is optional and used
if a FAISS index and sentence-transformers are available.

Files produced by ingestion (expected):
- data/recipe_metadata.jsonl  (one JSON per line with keys: id,title,link,source,ner)
- data/ingredient_index.json  (mapping ingredient -> [ids])
- data/recipe_index.faiss    (optional FAISS index of recipe embeddings)
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Dict, Tuple, Optional, Iterable

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except Exception:
    SentenceTransformer = None  # type: ignore
    faiss = None  # type: ignore


_UNIT_QTY_RE = re.compile(r'(^|\s)\d+\/?\d*\s*(cups?|cup|tbsp|tbs|tbsp\.|tsp|grams?|g|kg|oz|ounces?)', re.I)


def _normalize_token(tok: str) -> str:
    s = tok.lower().strip()
    s = _UNIT_QTY_RE.sub(' ', s)
    s = re.sub(r"[^\w\s]", '', s)
    s = s.strip()
    # simple plural handling
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
        self.faiss_index = None
        self.embed_model = None
        self.embed_dim = None

    def load_metadata(self, path: Optional[str] = None) -> None:
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

    def load_ingredient_index(self, path: Optional[str] = None) -> None:
        path = path or os.path.join(self.data_dir, 'ingredient_index.json')
        if not os.path.exists(path):
            raise FileNotFoundError(f"Ingredient index not found: {path}")
        with open(path, 'r', encoding='utf8') as fh:
            self.ingredient_index = json.load(fh)
        # ensure keys normalized
        self.ingredient_index = {k: [int(x) for x in v] for k, v in self.ingredient_index.items()}

    def try_load_faiss(self, path: Optional[str] = None, embed_model_name: str = 'all-MiniLM-L6-v2') -> None:
        if faiss is None or SentenceTransformer is None:
            return
        path = path or os.path.join(self.data_dir, 'recipe_index.faiss')
        if not os.path.exists(path):
            return
        # load model and index
        self.embed_model = SentenceTransformer(embed_model_name)
        self.faiss_index = faiss.read_index(path)
        self.embed_dim = self.embed_model.get_sentence_embedding_dimension()

    def normalize_ingredients(self, items: Iterable[str]) -> List[str]:
        return [t for t in (_normalize_token(x) for x in items) if t]

    def pantry_candidates(self, pantry_items: Iterable[str], min_overlap: int = 1, top_k: int = 200) -> List[Tuple[int, float]]:
        """Return candidate recipe ids scored by overlap fraction.

        Returns a list of (id, score) sorted descending. Score is overlap_fraction = overlap / recipe_ner_size
        """
        pantry = set(self.normalize_ingredients(pantry_items))
        if not pantry:
            return []

        # gather candidate ids from ingredient_index
        cand_scores: Dict[int, int] = {}
        for ing in pantry:
            ids = self.ingredient_index.get(ing) or []
            for rid in ids:
                cand_scores[rid] = cand_scores.get(rid, 0) + 1

        # compute overlap fraction
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

    def semantic_search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """Use FAISS index if available to run semantic search.

        Returns list of (id, score). If FAISS not available returns [].
        """
        if self.faiss_index is None or self.embed_model is None:
            return []
        qvec = self.embed_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        D, I = self.faiss_index.search(qvec, k)
        results: List[Tuple[int, float]] = []
        for idx, dist in zip(I[0], D[0]):
            if int(idx) == -1:
                continue
            results.append((int(idx), float(dist)))
        return results

    def hybrid_query(self, pantry_items: Iterable[str], query_text: str, top_k: int = 20) -> List[Tuple[dict, float]]:
        """Combine pantry overlap candidates with semantic search to produce final ranked list of metadata objects.

        Returns list of tuples (metadata, score)
        """
        pantry_cands = self.pantry_candidates(pantry_items, min_overlap=1, top_k=500)
        sem_cands = self.semantic_search(query_text, k=500)

        score_map: Dict[int, float] = {}
        for rid, s in sem_cands:
            score_map[rid] = score_map.get(rid, 0.0) + 0.6 * float(s)
        for rid, frac in pantry_cands:
            score_map[rid] = score_map.get(rid, 0.0) + 0.6 * float(frac) + 0.4

        ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.metadata.get(rid, {}), float(score)) for rid, score in ranked]


if __name__ == '__main__':
    print('RecipeKnowledgeAgent module - import and use in programs; run ingestion script to prepare data.')
