#!/usr/bin/env python3
"""
Simple Recipe Finder - Focus on Recipe Knowledge Agent only

Usage:
    python recipe_finder.py

This script provides a clean interface to the Recipe Knowledge Agent
without the complexity of the full multi-agent workflow.
"""

import os
from agents.recipe_knowledge_agent import RecipeKnowledgeAgent


class RecipeFinder:
    """Simple wrapper around Recipe Knowledge Agent for easy use"""
    
    def __init__(self, data_dir='data'):
        self.agent = None
        self.data_dir = data_dir
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize and load the Recipe Knowledge Agent"""
        print("🔧 Initializing Recipe Knowledge Agent...")
        
        try:
            self.agent = RecipeKnowledgeAgent(data_dir=self.data_dir)
            self.agent.load_metadata()
            self.agent.load_ingredient_index()
            self.agent.try_load_faiss()
            
            print(f"✅ Loaded {len(self.agent.metadata):,} recipes")
            print(f"✅ Loaded {len(self.agent.ingredient_index):,} unique ingredients")
            
            if self.agent.faiss_index:
                print("✅ Semantic search enabled (FAISS index loaded)")
            else:
                print("⚠️  Semantic search disabled (FAISS index not found)")
                print("   Run: python scripts/ingest_recipes.py --input assets/full_dataset.csv --outdir data --build-faiss")
            
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            print("\n⚠️  Please run the ingestion script first:")
            print("   python scripts/ingest_recipes.py --input assets/full_dataset.csv --outdir data")
            self.agent = None
    
    def find_by_ingredients(self, ingredients, min_overlap=1, top_k=10):
        """
        Find recipes based on ingredients you have
        
        Args:
            ingredients: List of ingredient names (e.g., ['chicken', 'tomatoes', 'garlic'])
            min_overlap: Minimum number of matching ingredients required
            top_k: Number of results to return
        
        Returns:
            List of (recipe_metadata, overlap_score) tuples
        """
        if not self.agent:
            print("❌ Agent not initialized")
            return []
        
        if not ingredients:
            print("❌ No ingredients provided")
            return []
        
        print(f"\n🔍 Searching for recipes with: {', '.join(ingredients)}")
        print(f"   (Requiring at least {min_overlap} matching ingredient{'s' if min_overlap > 1 else ''})")
        
        matches = self.agent.pantry_candidates(ingredients, min_overlap=min_overlap, top_k=top_k)
        
        results = []
        for recipe_id, score in matches:
            recipe = self.agent.metadata.get(recipe_id)
            if recipe:
                results.append((recipe, score))
        
        return results
    
    def find_by_description(self, query, top_k=10):
        """
        Find recipes by semantic search (description, cuisine, style, etc.)
        
        Args:
            query: Text description (e.g., "easy Italian pasta", "quick weeknight dinner")
            top_k: Number of results to return
        
        Returns:
            List of (recipe_metadata, similarity_score) tuples
        """
        if not self.agent:
            print("❌ Agent not initialized")
            return []
        
        if not self.agent.faiss_index:
            print("❌ Semantic search not available (FAISS index not loaded)")
            return []
        
        print(f"\n🔍 Searching for: '{query}'")
        
        results_with_ids = self.agent.semantic_search(query, k=top_k)
        
        results = []
        for recipe_id, score in results_with_ids:
            recipe = self.agent.metadata.get(recipe_id)
            if recipe:
                results.append((recipe, score))
        
        return results
    
    def find_hybrid(self, ingredients, query, top_k=10):
        """
        Find recipes using both ingredient matching and semantic similarity
        
        Args:
            ingredients: List of ingredient names
            query: Text description of what you want to cook
            top_k: Number of results to return
        
        Returns:
            List of (recipe_metadata, combined_score) tuples
        """
        if not self.agent:
            print("❌ Agent not initialized")
            return []
        
        if not ingredients:
            print("❌ No ingredients provided")
            return []
        
        print(f"\n🔍 Hybrid search:")
        print(f"   Ingredients: {', '.join(ingredients)}")
        print(f"   Query: '{query}'")
        
        results = self.agent.hybrid_query(
            pantry_items=ingredients,
            query_text=query,
            top_k=top_k
        )
        
        return results
    
    def display_results(self, results, show_count=5):
        """Pretty print recipe results"""
        if not results:
            print("\n❌ No recipes found. Try:")
            print("   - Different ingredients")
            print("   - Fewer required matches (lower min_overlap)")
            print("   - Different search terms")
            return
        
        print(f"\n{'='*70}")
        print(f"📋 Found {len(results)} recipes (showing top {min(show_count, len(results))}):")
        print(f"{'='*70}\n")
        
        for i, (recipe, score) in enumerate(results[:show_count], 1):
            print(f"{i}. {recipe['title']}")
            print(f"   Score: {score:.2f}")
            
            # Show ingredients
            ingredients = recipe.get('ner', [])
            if ingredients:
                ing_display = ', '.join(ingredients[:6])
                if len(ingredients) > 6:
                    ing_display += f" ... (+{len(ingredients) - 6} more)"
                print(f"   Ingredients: {ing_display}")
            
            # Show source/link
            if recipe.get('source'):
                print(f"   Source: {recipe['source']}")
            if recipe.get('link'):
                print(f"   Link: {recipe['link']}")
            
            print()


def interactive_mode():
    """Run an interactive recipe finder session"""
    print("=" * 70)
    print("🍽️  Welcome to Recipe Finder!")
    print("=" * 70)
    
    finder = RecipeFinder()
    
    if not finder.agent:
        print("\n❌ Cannot start - agent initialization failed")
        return
    
    print("\n📝 Choose search mode:")
    print("   1 - Search by ingredients")
    print("   2 - Search by description (requires FAISS)")
    print("   3 - Hybrid search (both)")
    print("   q - Quit")
    
    while True:
        print("\n" + "-" * 70)
        choice = input("\nMode (1/2/3/q): ").strip().lower()
        
        if choice == 'q':
            print("👋 Goodbye!")
            break
        
        elif choice == '1':
            # Ingredient search
            ing_input = input("Enter ingredients (comma-separated): ").strip()
            if not ing_input:
                print("⚠️  No ingredients provided")
                continue
            
            ingredients = [ing.strip() for ing in ing_input.split(',') if ing.strip()]
            
            try:
                min_overlap = int(input(f"Minimum matching ingredients (1-{len(ingredients)}): ").strip() or "1")
            except ValueError:
                min_overlap = 1
            
            results = finder.find_by_ingredients(ingredients, min_overlap=min_overlap, top_k=10)
            finder.display_results(results)
        
        elif choice == '2':
            # Semantic search
            if not finder.agent.faiss_index:
                print("❌ Semantic search not available - FAISS index not loaded")
                continue
            
            query = input("Describe what you want to cook: ").strip()
            if not query:
                print("⚠️  No query provided")
                continue
            
            results = finder.find_by_description(query, top_k=10)
            finder.display_results(results)
        
        elif choice == '3':
            # Hybrid search
            ing_input = input("Enter ingredients (comma-separated): ").strip()
            if not ing_input:
                print("⚠️  No ingredients provided")
                continue
            
            ingredients = [ing.strip() for ing in ing_input.split(',') if ing.strip()]
            
            query = input("Describe what you want to cook: ").strip()
            if not query:
                query = "dinner recipe"
            
            results = finder.find_hybrid(ingredients, query, top_k=10)
            finder.display_results(results)
        
        else:
            print("⚠️  Invalid choice. Please enter 1, 2, 3, or q")


def example_usage():
    """Show example usage of the RecipeFinder"""
    print("=" * 70)
    print("📚 Recipe Finder - Example Usage")
    print("=" * 70)
    
    finder = RecipeFinder()
    
    if not finder.agent:
        return
    
    # Example 1: Ingredient search
    print("\n" + "=" * 70)
    print("Example 1: Search by ingredients")
    print("=" * 70)
    results = finder.find_by_ingredients(
        ingredients=['chicken', 'tomatoes', 'garlic', 'onion'],
        min_overlap=2,
        top_k=5
    )
    finder.display_results(results, show_count=3)
    
    # Example 2: Semantic search (if available)
    if finder.agent.faiss_index:
        print("\n" + "=" * 70)
        print("Example 2: Search by description")
        print("=" * 70)
        results = finder.find_by_description(
            query="easy weeknight pasta dinner",
            top_k=5
        )
        finder.display_results(results, show_count=3)
    
    # Example 3: Hybrid search
    print("\n" + "=" * 70)
    print("Example 3: Hybrid search")
    print("=" * 70)
    results = finder.find_hybrid(
        ingredients=['pasta', 'tomatoes', 'basil', 'garlic'],
        query="quick Italian dinner",
        top_k=5
    )
    finder.display_results(results, show_count=3)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--example':
        example_usage()
    else:
        interactive_mode()
