"""
RAG Evaluation - Multi-Level Relevance & Better Metrics

Key Improvements:
1. **Graded Relevance**: Not just binary (relevant/not), but multiple levels
2. **Ingredient Overlap Score**: Measure how well retrieved recipes match query
3. **Diversity Metrics**: Ensure varied results, not just duplicates
4. **User-Centric Metrics**: Would a real user be satisfied?    

New Metrics:
- Success@K: Would user find ANY usable recipe in top-K?
- Average Ingredient Match: How well do top results match the query?
- nDCG with graded relevance (0-2 scale instead of binary)
- Diversity: Are top results different from each other?

Usage:
    python scripts/evaluate_rag.py --sample 20 --k 10
"""

import argparse
import json
import os
import sys
from typing import List, Dict, Tuple, Optional, Any, Set
from collections import defaultdict
import math
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.recipe_knowledge_agent import RecipeKnowledgeAgent

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError:
    print("❌ Error: Required packages not installed")
    sys.exit(1)


class AdvancedRAGEvaluator:
    """Advanced RAG evaluation with graded relevance and user-centric metrics"""
    
    def __init__(self, recipe_agent: RecipeKnowledgeAgent):
        self.recipe_agent = recipe_agent
        self.recipe_agent.setup_milvus()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_cases": [],
            "aggregate_metrics": {},
            "insights": {}
        }
    
    def calculate_ingredient_overlap(self, recipe_ingredients: List[str], 
                                    query_ingredients: List[str]) -> float:
        """
        Calculate how well a recipe matches query ingredients.
        
        Returns:
            Overlap score between 0.0 and 1.0
        """
        if not query_ingredients or not recipe_ingredients:
            return 0.0
        
        recipe_set = set(recipe_ingredients)
        query_set = set(query_ingredients)
        
        # Overlap: how many query ingredients are in the recipe
        overlap = len(query_set & recipe_set)
        
        # Normalize by query size (what user has)
        overlap_score = overlap / len(query_set)
        
        return overlap_score
    
    def assign_relevance_grade(self, recipe_id: int, 
                               query_ingredients: List[str],
                               expected_id: int) -> int:
        """
        Assign graded relevance score (0-2).
        
        Grades:
        - 2 (Highly Relevant): The exact recipe OR >80% ingredient match
        - 1 (Relevant): 50-80% ingredient match
        - 0 (Not Relevant): <50% ingredient match
        
        Args:
            recipe_id: ID of recipe to evaluate
            query_ingredients: Ingredients in query
            expected_id: Original recipe ID (gets automatic grade 2)
            
        Returns:
            Relevance grade (0, 1, or 2)
        """
        # Exact match gets highest grade
        if recipe_id == expected_id:
            return 2
        
        # Calculate ingredient overlap
        recipe_meta = self.recipe_agent.metadata.get(recipe_id)
        if not recipe_meta:
            return 0
        
        recipe_ingredients = recipe_meta.get('ner', [])
        overlap_score = self.calculate_ingredient_overlap(recipe_ingredients, query_ingredients)
        
        # Graded relevance based on overlap
        if overlap_score >= 0.8:
            return 2  # Highly relevant (uses most of your ingredients)
        elif overlap_score >= 0.5:
            return 1  # Relevant (uses some of your ingredients)
        else:
            return 0  # Not relevant
    
    def create_test_cases(self, sample_recipes: List[Dict]) -> List[Dict]:
        """Create realistic test cases"""
        test_cases = []
        
        for recipe in sample_recipes:
            ingredients = recipe.get('ner', [])
            num_ingredients = len(ingredients)
            
            if num_ingredients < 4 or num_ingredients > 12:
                continue
            
            # Use 75% of ingredients (realistic pantry scenario)
            partial_ingredients = ingredients[:max(3, int(num_ingredients * 0.75))]
            
            # Only test ingredient-based search (most realistic)
            test_cases.append({
                "test_id": f"recipe_{recipe['id']}_ingredients",
                "recipe_id": recipe['id'],
                "recipe_title": recipe['title'],
                "query_ingredients": partial_ingredients,
                "expected_recipe_id": recipe['id'],
                "num_ingredients": num_ingredients,
                "num_query_ingredients": len(partial_ingredients),
                "ground_truth_ingredients": ingredients
            })
        
        return test_cases
    
    def run_test_case(self, test_case: Dict, k: int = 10) -> Dict:
        """Run test case with graded relevance evaluation"""
        test_id = test_case['test_id']
        recipe_title = test_case['recipe_title']
        
        print(f"\n🧪 {test_id}")
        print(f"   Recipe: {recipe_title}")
        print(f"   Query: {len(test_case['query_ingredients'])}/{test_case['num_ingredients']} ingredients")
        
        query_ingredients = test_case['query_ingredients']
        expected_id = test_case['expected_recipe_id']
        
        try:
            # Ingredient-based search
            results = self.recipe_agent.pantry_candidates(
                pantry_items=query_ingredients,
                allow_missing=2,
                top_k=k
            )
            retrieved_ids = [(rid, score) for rid, score, num_used, missing in results]
            
            # Assign relevance grades to all retrieved recipes
            relevance_grades = []
            ingredient_matches = []
            
            for rid, score in retrieved_ids:
                grade = self.assign_relevance_grade(rid, query_ingredients, expected_id)
                relevance_grades.append(grade)
                
                # Calculate ingredient match for analysis
                recipe_meta = self.recipe_agent.metadata.get(rid)
                if recipe_meta:
                    match_score = self.calculate_ingredient_overlap(
                        recipe_meta.get('ner', []),
                        query_ingredients
                    )
                    ingredient_matches.append(match_score)
                else:
                    ingredient_matches.append(0.0)
            
            # Calculate advanced metrics
            metrics = self._calculate_advanced_metrics(
                retrieved_ids=retrieved_ids,
                relevance_grades=relevance_grades,
                ingredient_matches=ingredient_matches,
                expected_id=expected_id,
                k=k
            )
            
            # Diagnostic output
            exact_rank = metrics['exact_match_rank']
            success_k = metrics['success_at_k']
            avg_relevance = metrics['avg_relevance_in_top_k']
            
            if exact_rank:
                print(f"   ✅ Exact match at rank {exact_rank}")
            else:
                print(f"   ⚠️  Exact match NOT in top-{k}")
            
            print(f"   📊 Success@{k}: {success_k} | Avg Relevance: {avg_relevance:.2f} | Top-3 Grades: {relevance_grades[:3]}")
            
            # Show top 3 results with relevance
            print(f"   🔝 Top 3 results:")
            for i, (rid, score) in enumerate(retrieved_ids[:3], 1):
                recipe_meta = self.recipe_agent.metadata.get(rid)
                title = recipe_meta.get('title', 'Unknown') if recipe_meta else 'Unknown'
                grade = relevance_grades[i-1] if i-1 < len(relevance_grades) else 0
                match = ingredient_matches[i-1] if i-1 < len(ingredient_matches) else 0
                marker = "🎯" if rid == expected_id else ("✓" if grade >= 1 else "✗")
                print(f"      {i}. {marker} [{grade}] {title[:40]} (match: {match:.0%})")
            
            return {
                "test_case": test_case,
                "retrieved_ids": [rid for rid, score in retrieved_ids],
                "retrieved_scores": [score for rid, score in retrieved_ids],
                "relevance_grades": relevance_grades,
                "ingredient_matches": ingredient_matches,
                "metrics": metrics
            }
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                "test_case": test_case,
                "error": str(e)
            }
    
    def _calculate_advanced_metrics(
        self,
        retrieved_ids: List[Tuple[int, float]],
        relevance_grades: List[int],
        ingredient_matches: List[float],
        expected_id: int,
        k: int
    ) -> Dict[str, Any]:
        """
        Calculate advanced metrics with graded relevance.
        """
        metrics = {}
        
        result_ids = [rid for rid, score in retrieved_ids[:k]]
        grades_at_k = relevance_grades[:k]
        matches_at_k = ingredient_matches[:k]
        
        # 1. EXACT MATCH RANK (traditional)
        try:
            rank = result_ids.index(expected_id) + 1
            metrics['exact_match_rank'] = rank
            metrics['exact_match_mrr'] = 1.0 / rank
        except ValueError:
            metrics['exact_match_rank'] = None
            metrics['exact_match_mrr'] = 0.0
        
        # 2. SUCCESS@K: Did we find ANY highly relevant recipe (grade >= 1)?
        # This is more realistic: user just needs *a* good recipe
        has_relevant = any(grade >= 1 for grade in grades_at_k)
        metrics['success_at_k'] = 1.0 if has_relevant else 0.0
        
        # 3. BEST RELEVANCE RANK: Position of first highly relevant result (grade 2)
        try:
            best_rank = grades_at_k.index(2) + 1
            metrics['best_relevance_rank'] = best_rank
            metrics['best_relevance_mrr'] = 1.0 / best_rank
        except ValueError:
            # No grade-2 results, try grade-1
            try:
                best_rank = grades_at_k.index(1) + 1
                metrics['best_relevance_rank'] = best_rank
                metrics['best_relevance_mrr'] = 1.0 / best_rank
            except ValueError:
                metrics['best_relevance_rank'] = None
                metrics['best_relevance_mrr'] = 0.0
        
        # 4. nDCG with GRADED relevance (0-2 scale)
        dcg = sum(grade / math.log2(i + 2) for i, grade in enumerate(grades_at_k))
        
        # Ideal DCG: all grade-2 results at top
        ideal_grades = sorted(grades_at_k, reverse=True)
        idcg = sum(grade / math.log2(i + 2) for i, grade in enumerate(ideal_grades))
        
        metrics['ndcg_at_k_graded'] = dcg / idcg if idcg > 0 else 0.0
        
        # 5. AVERAGE RELEVANCE in top-K (how good are results overall?)
        metrics['avg_relevance_in_top_k'] = sum(grades_at_k) / len(grades_at_k) if grades_at_k else 0.0
        
        # 6. AVERAGE INGREDIENT MATCH in top-K
        metrics['avg_ingredient_match'] = sum(matches_at_k) / len(matches_at_k) if matches_at_k else 0.0
        
        # 7. PRECISION@K with graded relevance (how many good results in top-K?)
        num_relevant = sum(1 for grade in grades_at_k if grade >= 1)
        metrics['precision_at_k_relevant'] = num_relevant / k
        
        # 8. DIVERSITY: Are top results different from each other?
        # (Simple version: check if ingredient sets are distinct)
        metrics['num_unique_results'] = len(set(result_ids))
        
        return metrics
    
    def calculate_aggregate_metrics(self, test_results: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregate metrics"""
        print("\n📊 Calculating aggregate metrics...")
        
        valid_results = [r for r in test_results 
                        if 'metrics' in r and 'error' not in r]
        
        if not valid_results:
            return {}
        
        print(f"   Valid test cases: {len(valid_results)}")
        
        aggregate = {}
        
        # Extract all metrics
        all_metrics = [r['metrics'] for r in valid_results]
        
        # Traditional exact-match metrics
        exact_mrr_values = [m['exact_match_mrr'] for m in all_metrics]
        exact_ranks = [m['exact_match_rank'] for m in all_metrics if m['exact_match_rank']]
        
        aggregate['exact_match'] = {
            'mrr': sum(exact_mrr_values) / len(exact_mrr_values),
            'avg_rank': sum(exact_ranks) / len(exact_ranks) if exact_ranks else None,
            'median_rank': sorted(exact_ranks)[len(exact_ranks) // 2] if exact_ranks else None,
            'found_in_top_k_pct': sum(1 for m in all_metrics if m['exact_match_rank']) / len(all_metrics)
        }
        
        # NEW: User-centric metrics (better!)
        success_values = [m['success_at_k'] for m in all_metrics]
        best_mrr_values = [m['best_relevance_mrr'] for m in all_metrics]
        best_ranks = [m['best_relevance_rank'] for m in all_metrics if m['best_relevance_rank']]
        
        aggregate['user_centric'] = {
            'success_at_k': sum(success_values) / len(success_values),
            'best_relevance_mrr': sum(best_mrr_values) / len(best_mrr_values),
            'avg_best_rank': sum(best_ranks) / len(best_ranks) if best_ranks else None,
            'median_best_rank': sorted(best_ranks)[len(best_ranks) // 2] if best_ranks else None
        }
        
        # Quality metrics
        ndcg_values = [m['ndcg_at_k_graded'] for m in all_metrics]
        relevance_values = [m['avg_relevance_in_top_k'] for m in all_metrics]
        match_values = [m['avg_ingredient_match'] for m in all_metrics]
        precision_values = [m['precision_at_k_relevant'] for m in all_metrics]
        
        aggregate['quality'] = {
            'avg_ndcg_graded': sum(ndcg_values) / len(ndcg_values),
            'avg_relevance': sum(relevance_values) / len(relevance_values),
            'avg_ingredient_match': sum(match_values) / len(match_values),
            'avg_precision_relevant': sum(precision_values) / len(precision_values)
        }
        
        return aggregate
    
    def run_evaluation(self, num_samples: int = 20, k: int = 10) -> Dict:
        """Run advanced evaluation"""
        print(f"\n{'='*70}")
        print(f"🎯 RAG EVALUATION V3 - Advanced Metrics & Graded Relevance")
        print(f"{'='*70}")
        print(f"📏 Sample: {num_samples} recipes | Top-K: {k}")
        
        # Sample recipes
        all_recipe_ids = list(self.recipe_agent.metadata.keys())
        sample_ids = all_recipe_ids[:num_samples]
        sample_recipes = [self.recipe_agent.metadata[rid] for rid in sample_ids]
        
        print(f"✅ Loaded {len(sample_recipes)} recipes")
        
        # Create test cases
        print("\n🧪 Creating test cases...")
        test_cases = self.create_test_cases(sample_recipes)
        print(f"   Created {len(test_cases)} test cases")
        
        # Run tests
        print(f"\n🚀 Running evaluation...")
        test_results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}]", end=" ")
            result = self.run_test_case(test_case, k=k)
            test_results.append(result)
        
        # Calculate metrics
        aggregate_metrics = self.calculate_aggregate_metrics(test_results)
        
        # Store results
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "num_samples": num_samples,
                "k": k,
                "num_test_cases": len(test_cases)
            },
            "test_results": test_results,
            "aggregate_metrics": aggregate_metrics
        }
        
        return self.results
    
    def print_summary(self):
        """Print comprehensive summary"""
        if not self.results.get('aggregate_metrics'):
            print("⚠️  No results to summarize")
            return
        
        metrics = self.results['aggregate_metrics']
        k = self.results['config']['k']
        
        print("\n" + "="*70)
        print("📊 EVALUATION SUMMARY (V3 - Advanced Metrics)")
        print("="*70)
        
        # Traditional metrics (for comparison)
        exact = metrics.get('exact_match', {})
        print(f"\n📌 Traditional Metrics (Exact Match Only):")
        print(f"   Found exact recipe in top-{k}: {exact.get('found_in_top_k_pct', 0):.1%}")
        print(f"   MRR (exact): {exact.get('mrr', 0):.3f}")
        print(f"   Avg Rank (exact): {exact.get('avg_rank', 'N/A'):.1f}" if exact.get('avg_rank') else f"   Avg Rank: N/A")
        print(f"   Median Rank (exact): {exact.get('median_rank', 'N/A')}")
        
        # NEW: User-centric metrics (better!)
        user = metrics.get('user_centric', {})
        print(f"\n✨ User-Centric Metrics (Graded Relevance):")
        print(f"   Success@{k}: {user.get('success_at_k', 0):.1%} ⭐")
        print(f"      → User finds ANY usable recipe in top-{k}")
        print(f"   Best Relevance MRR: {user.get('best_relevance_mrr', 0):.3f}")
        print(f"   Avg Best Rank: {user.get('avg_best_rank', 'N/A'):.1f}" if user.get('avg_best_rank') else f"   Avg Best Rank: N/A")
        print(f"      → Position of first highly relevant result")
        
        # Quality metrics
        quality = metrics.get('quality', {})
        print(f"\n📈 Result Quality:")
        print(f"   nDCG (graded): {quality.get('avg_ndcg_graded', 0):.3f}")
        print(f"   Avg Relevance: {quality.get('avg_relevance', 0):.2f} / 2.0")
        print(f"   Avg Ingredient Match: {quality.get('avg_ingredient_match', 0):.1%}")
        print(f"   Precision@{k} (relevant): {quality.get('avg_precision_relevant', 0):.1%}")
        
        print(f"\n💡 Interpretation:")
        success_rate = user.get('success_at_k', 0)
        if success_rate >= 0.9:
            print(f"   ✅ EXCELLENT: Users find usable recipes {success_rate:.0%} of the time")
        elif success_rate >= 0.7:
            print(f"   ✓ GOOD: Users find usable recipes {success_rate:.0%} of the time")
        elif success_rate >= 0.5:
            print(f"   ⚠️  FAIR: Users find usable recipes only {success_rate:.0%} of the time")
        else:
            print(f"   ❌ POOR: Users find usable recipes only {success_rate:.0%} of the time")
        
        print("\n" + "="*70)
    
    def save_results(self, output_path: str):
        """Save results"""
        print(f"\n💾 Saving to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"   ✅ Saved")


def load_local_metadata(data_dir: str, num_samples: int) -> Dict[int, Dict]:
    """Load metadata"""
    metadata_path = os.path.join(data_dir, 'recipe_metadata.jsonl')
    
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")
    
    print(f"📂 Loading metadata...")
    metadata = {}
    
    with open(metadata_path, 'r', encoding='utf8') as fh:
        for i, line in enumerate(fh):
            if i >= num_samples:
                break
            if not line.strip():
                continue
            obj = json.loads(line)
            metadata[int(obj['id'])] = obj
    
    print(f"   ✅ Loaded {len(metadata):,} recipes")
    return metadata


def load_ingredient_index(data_dir: str) -> Dict[str, List[int]]:
    """Load ingredient index"""
    index_path = os.path.join(data_dir, 'ingredient_index.json')
    
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"Index not found: {index_path}")
    
    print(f"📂 Loading ingredient index...")
    
    with open(index_path, 'r', encoding='utf8') as fh:
        ingredient_index = json.load(fh)
    
    ingredient_index = {k: [int(x) for x in v] for k, v in ingredient_index.items()}
    print(f"   ✅ Loaded {len(ingredient_index):,} ingredients")
    
    return ingredient_index


def main():
    parser = argparse.ArgumentParser(description='RAG Evaluation V3 - Advanced')
    parser.add_argument('--sample', type=int, default=20)
    parser.add_argument('--k', type=int, default=10)
    parser.add_argument('--output', type=str, default='evaluation_v3_results.json')
    parser.add_argument('--data-dir', type=str, default='data')
    args = parser.parse_args()
    
    print("\n🚀 Initializing...")
    
    agent = RecipeKnowledgeAgent(data_dir=args.data_dir)
    
    try:
        metadata = load_local_metadata(args.data_dir, args.sample)
        ingredient_index = load_ingredient_index(args.data_dir)
        
        agent.metadata = metadata
        agent.ingredient_index = ingredient_index
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    evaluator = AdvancedRAGEvaluator(agent)
    
    results = evaluator.run_evaluation(num_samples=args.sample, k=args.k)
    
    evaluator.print_summary()
    evaluator.save_results(args.output)
    
    print("\n✅ Complete!")


if __name__ == '__main__':
    main()
