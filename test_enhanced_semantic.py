#!/usr/bin/env python3
"""
Test the enhanced semantic search with ingredients + query text
Shows how pantry_candidates and semantic_search complement each other
"""

from agents.recipe_knowledge_agent import RecipeKnowledgeAgent

def print_separator(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_recipe(idx, recipe, score, num_used, missing, show_ingredients=False):
    """Pretty print a recipe result"""
    print(f"{idx}. [{score:.1f} pts] {recipe['title']}")
    print(f"   ✓ Uses {num_used} of your items")
    if missing:
        print(f"   ⚠ Missing: {', '.join(missing)}")
    if show_ingredients:
        # Ingredients are stored in 'ner' field (Named Entity Recognition)
        ingredients = recipe.get('ner', [])
        if ingredients:
            print(f"   📝 All ingredients: {', '.join(ingredients[:8])}{'...' if len(ingredients) > 8 else ''}")
        else:
            print(f"   📝 All ingredients: (not available)")
    print()

def main():
    print_separator("🧪 Testing Enhanced LEFTOVR Search")
    
    # Initialize agent
    print("Loading RecipeKnowledgeAgent...")
    agent = RecipeKnowledgeAgent()
    agent.load_metadata()
    agent.load_ingredient_index()
    agent.setup_qdrant()
    print(f"✓ Loaded {len(agent.metadata)} recipes")
    print(f"✓ Qdrant collection: {agent.collection_name}")
    
    # Test scenario: Common leftovers in fridge
    pantry = ["chicken breast", "garlic", "olive oil", "lemon", "parsley"]
    
    print(f"\n🥘 Your pantry items:")
    for item in pantry:
        print(f"   • {item}")
    
    # ============================================================================
    # TEST 1: Pantry Candidates Only (Exact Matching)
    # ============================================================================
    print_separator("TEST 1: Pantry Candidates (Exact Match + LEFTOVR Scoring)")
    print("Method: pantry_candidates()")
    print("How it works: Fast exact matching via inverted index")
    print("Scoring: num_used × 100 + 1000 - total_ingredients\n")
    
    pantry_results = agent.pantry_candidates(pantry, allow_missing=2, top_k=5)
    
    if pantry_results:
        for i, (rid, score, num_used, missing) in enumerate(pantry_results, 1):
            recipe = agent.metadata.get(rid, {})
            print_recipe(i, recipe, score, num_used, missing, show_ingredients=True)
    else:
        print("❌ No results found")
    
    # ============================================================================
    # TEST 2: Semantic Search Only (Ingredients + Preferences)
    # ============================================================================
    print_separator("TEST 2: Semantic Search (Ingredients + Preferences)")
    print("Method: semantic_search(query, pantry_items)")
    print("How it works: all-MiniLM-L6-v2 finds recipes semantically similar to:")
    print("  • Your ingredients: chicken breast, garlic, olive oil, lemon, parsley")
    print("  • Your preference: 'Mediterranean healthy dinner'\n")
    
    query = "Mediterranean healthy dinner"
    sem_results = agent.semantic_search(
        query=query, 
        pantry_items=pantry,
        k=5
    )
    
    if sem_results:
        for i, (rid, sim_score) in enumerate(sem_results, 1):
            recipe = agent.metadata.get(rid, {})
            print(f"{i}. [Similarity: {sim_score:.3f}] {recipe['title']}")
            ingredients = recipe.get('ner', [])
            if ingredients:
                print(f"   📝 Ingredients: {', '.join(ingredients[:8])}{'...' if len(ingredients) > 8 else ''}")
            print()
    else:
        print("❌ No results found")
    
    # ============================================================================
    # TEST 3: Hybrid Query (Best of Both Worlds!)
    # ============================================================================
    print_separator("TEST 3: Hybrid Query (Pantry + Semantic Combined)")
    print("Method: hybrid_query()")
    print("How it works:")
    print("  1. Get 500 candidates from exact matching (pantry_candidates)")
    print("  2. Get 500 candidates from semantic search (with ingredients + query)")
    print("  3. Recipes in BOTH get +50 semantic bonus on top of LEFTOVR score")
    print("\nWhy this is powerful:")
    print("  • Exact matching ensures you don't miss perfect ingredient matches")
    print("  • Semantic search finds recipes even with ingredient variations")
    print("  • Combined scoring rewards recipes that match BOTH ways\n")
    
    hybrid_results = agent.hybrid_query(
        pantry_items=pantry,
        query_text=query,
        top_k=10,
        allow_missing=2,
        use_semantic=True
    )
    
    if hybrid_results:
        for i, (recipe, score, num_used, missing) in enumerate(hybrid_results, 1):
            print_recipe(i, recipe, score, num_used, missing, show_ingredients=True)
    else:
        print("❌ No results found")
    
    # ============================================================================
    # TEST 4: Just Ingredients, No Preference (Flexible Search)
    # ============================================================================
    print_separator("TEST 4: Semantic Search with ONLY Ingredients")
    print("Method: semantic_search(pantry_items=..., query=None)")
    print("Use case: 'I have these leftovers, what can I make?'\n")
    
    sem_only_ingredients = agent.semantic_search(
        pantry_items=pantry,
        k=5
    )
    
    if sem_only_ingredients:
        for i, (rid, sim_score) in enumerate(sem_only_ingredients, 1):
            recipe = agent.metadata.get(rid, {})
            print(f"{i}. [Similarity: {sim_score:.3f}] {recipe['title']}")
            ingredients = recipe.get('ner', [])
            if ingredients:
                print(f"   📝 Ingredients: {', '.join(ingredients[:8])}{'...' if len(ingredients) > 8 else ''}")
            print()
    else:
        print("❌ No results found")
    
    # ============================================================================
    # TEST 5: Different Pantry Scenarios
    # ============================================================================
    print_separator("TEST 5: Different Leftover Scenarios")
    
    scenarios = [
        {
            "name": "Asian Ingredients",
            "pantry": ["soy sauce", "ginger", "rice", "green onions"],
            "query": "quick stir fry"
        },
        {
            "name": "Breakfast Items",
            "pantry": ["eggs", "milk", "flour", "butter"],
            "query": "easy breakfast"
        },
        {
            "name": "Minimal Leftovers",
            "pantry": ["tomato", "onion"],
            "query": "simple recipe"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{'─'*80}")
        print(f"Scenario: {scenario['name']}")
        print(f"Pantry: {', '.join(scenario['pantry'])}")
        print(f"Looking for: {scenario['query']}\n")
        
        results = agent.hybrid_query(
            pantry_items=scenario['pantry'],
            query_text=scenario['query'],
            top_k=3,
            allow_missing=1
        )
        
        if results:
            for i, (recipe, score, num_used, missing) in enumerate(results, 1):
                print(f"{i}. [{score:.1f}] {recipe['title']} (uses {num_used} items)")
        else:
            print("No results found")
    
    # ============================================================================
    # Summary
    # ============================================================================
    print_separator("✨ Summary: Why Keep Both Methods?")
    print("""
1. SPEED vs UNDERSTANDING:
   • pantry_candidates(): Fast exact matching (milliseconds)
   • semantic_search(): Slower but understands synonyms & variations
   
2. PRECISION vs RECALL:
   • pantry_candidates(): Precise - only exact matches
   • semantic_search(): Broad - finds similar ingredient combinations
   
3. COMPLEMENTARY SIGNALS:
   • Exact match: "This recipe uses exactly these ingredients"
   • Semantic: "This recipe is similar to what you want"
   • Hybrid: "This recipe does BOTH!" (gets bonus points)
   
4. REAL-WORLD BENEFITS:
   • User has "chicken breast" → finds recipes with "chicken"
   • Recipe says "lemon juice" → matches your "lemon"
   • Mediterranean query → boosts Greek/Italian recipes
   • LEFTOVR scoring → prioritizes using MORE leftovers
   
🎯 The hybrid approach gives you robust search that works even when:
   - Ingredient names vary ("scallions" vs "green onions")
   - Users want flavor profiles, not just ingredient matches
   - You need to rank by leftover usage, not just relevance
""")

if __name__ == "__main__":
    main()
