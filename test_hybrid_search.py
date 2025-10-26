#!/usr/bin/env python3
"""
Test the Hybrid Search - The Final Production Method for LEFTOVR

This is the ONLY test file you need for the recipe knowledge agent.
It demonstrates:
  1. Exact ingredient matching (pantry_candidates)
  2. Semantic similarity (enhanced with ingredients + preferences)
  3. LEFTOVR scoring (prioritize using MORE leftovers)
  4. Full recipe details including DIRECTIONS (from metadata)
"""

from agents.recipe_knowledge_agent import RecipeKnowledgeAgent

def print_separator(title="", char="="):
    if title:
        print(f"\n{char*80}")
        print(f"  {title}")
        print(f"{char*80}\n")
    else:
        print(f"\n{char*80}\n")

def print_recipe(idx, recipe, score, num_used, missing, show_directions=False):
    """Pretty print a recipe result"""
    title = recipe.get('title', 'Unknown')
    ingredients = recipe.get('ner', [])
    directions = recipe.get('directions', [])
    
    print(f"{idx}. [{score:.1f} pts] {title}")
    print(f"   ✓ Uses {num_used} of your pantry items")
    
    if missing:
        print(f"   ⚠️  Missing {len(missing)} ingredient(s): {', '.join(missing[:3])}")
        if len(missing) > 3:
            print(f"      ... and {len(missing) - 3} more")
    else:
        print(f"   ✅ You can make this NOW (no shopping needed!)")
    
    if ingredients:
        print(f"   📝 Ingredients: {', '.join(ingredients[:6])}")
        if len(ingredients) > 6:
            print(f"      ... and {len(ingredients) - 6} more ingredients")
    
    if show_directions and directions:
        print(f"   👨‍🍳 Directions ({len(directions)} steps):")
        for i, step in enumerate(directions[:3], 1):
            # Truncate long steps
            step_text = step[:100] + "..." if len(step) > 100 else step
            print(f"      {i}. {step_text}")
        if len(directions) > 3:
            print(f"      ... and {len(directions) - 3} more steps")
    print()


def main():
    print_separator("🍳 LEFTOVR Hybrid Search - Production Test Suite")
    
    # Initialize agent
    print("⚙️  Initializing RecipeKnowledgeAgent...")
    agent = RecipeKnowledgeAgent()
    agent.load_metadata()
    agent.load_ingredient_index()
    agent.setup_qdrant()
    
    print(f"✅ Ready! Loaded {len(agent.metadata):,} recipes")
    print(f"✅ Qdrant vector search available")
    print(f"✅ Ingredient index loaded\n")
    
    # ============================================================================
    # TEST 1: Basic Usage - Minimal Leftovers, No Preferences
    # ============================================================================
    print_separator("TEST 1: Basic Usage - Just Leftovers", "-")
    print("Scenario: User has basic leftovers, no specific preferences")
    print("Expected: Recipes that use the MOST items, even if missing some\n")
    
    pantry = ["chicken", "rice", "soy sauce"]
    
    print(f"🥘 Pantry Items: {', '.join(pantry)}\n")
    
    results = agent.hybrid_query(
        pantry_items=pantry,
        query_text=None,  # No preferences!
        top_k=5,
        allow_missing=2,  # Willing to buy up to 2 items
        use_semantic=True
    )
    
    print(f"Found {len(results)} recipes:\n")
    for i, (recipe, score, num_used, missing) in enumerate(results, 1):
        print_recipe(i, recipe, score, num_used, missing)
    
    # ============================================================================
    # TEST 2: With Preferences - Leftovers + Cooking Style
    # ============================================================================
    print_separator("TEST 2: Leftovers + Preferences", "-")
    print("Scenario: User has leftovers AND knows what they want to eat")
    print("Expected: Recipes matching BOTH ingredients AND preferences\n")
    
    pantry = ["ground beef", "tomatoes", "onion", "garlic"]
    query = "Italian comfort food"
    
    print(f"🥘 Pantry Items: {', '.join(pantry)}")
    print(f"🎯 User Preference: '{query}'\n")
    
    results = agent.hybrid_query(
        pantry_items=pantry,
        query_text=query,
        top_k=5,
        allow_missing=3,
        use_semantic=True
    )
    
    print(f"Found {len(results)} recipes:\n")
    for i, (recipe, score, num_used, missing) in enumerate(results, 1):
        print_recipe(i, recipe, score, num_used, missing)
    
    # ============================================================================
    # TEST 3: Zero Missing - Must Use Only Pantry Items
    # ============================================================================
    print_separator("TEST 3: Zero Shopping - Use Only What You Have", "-")
    print("Scenario: User doesn't want to buy ANYTHING")
    print("Expected: Only recipes using pantry items (zero missing)\n")
    
    pantry = ["eggs", "milk", "flour", "sugar", "butter"]
    query = "breakfast"
    
    print(f"🥘 Pantry Items: {', '.join(pantry)}")
    print(f"🎯 User Preference: '{query}'")
    print(f"🚫 Allow Missing: 0 (must use only pantry items!)\n")
    
    results = agent.hybrid_query(
        pantry_items=pantry,
        query_text=query,
        top_k=5,
        allow_missing=0,  # ZERO missing!
        use_semantic=True
    )
    
    print(f"Found {len(results)} recipes:\n")
    if results:
        for i, (recipe, score, num_used, missing) in enumerate(results, 1):
            print_recipe(i, recipe, score, num_used, missing)
    else:
        print("❌ No recipes found that use ONLY your pantry items")
        print("💡 Try increasing allow_missing to 1 or 2\n")
    
    # ============================================================================
    # TEST 4: Many Leftovers - Maximize Usage
    # ============================================================================
    print_separator("TEST 4: Many Leftovers - Prioritize Using MORE", "-")
    print("Scenario: User has lots of leftovers, wants to use up as many as possible")
    print("Expected: Recipes ranked by number of items used (LEFTOVR philosophy)\n")
    
    pantry = [
        "chicken breast", "garlic", "olive oil", "lemon", "parsley",
        "cherry tomatoes", "pasta", "parmesan", "butter", "white wine"
    ]
    query = "Mediterranean dinner"
    
    print(f"🥘 Pantry Items ({len(pantry)} items):")
    for item in pantry:
        print(f"   • {item}")
    print(f"\n🎯 User Preference: '{query}'\n")
    
    results = agent.hybrid_query(
        pantry_items=pantry,
        query_text=query,
        top_k=10,
        allow_missing=2,
        use_semantic=True
    )
    
    print(f"Found {len(results)} recipes:\n")
    for i, (recipe, score, num_used, missing) in enumerate(results, 1):
        print_recipe(i, recipe, score, num_used, missing)
    
    # ============================================================================
    # TEST 5: Dietary Restrictions / Specific Ingredients
    # ============================================================================
    print_separator("TEST 5: Dietary Restrictions", "-")
    print("Scenario: User has specific dietary needs (e.g., vegan, gluten-free)")
    print("Expected: Recipes that respect dietary restrictions\n")
    
    pantry = ["tofu", "quinoa", "kale", "tahini", "lemon juice"]
    query = "vegan protein bowl"
    
    print(f"🥘 Pantry Items: {', '.join(pantry)}")
    print(f"🎯 User Preference: '{query}'\n")
    
    results = agent.hybrid_query(
        pantry_items=pantry,
        query_text=query,
        top_k=5,
        allow_missing=3,
        use_semantic=True
    )
    
    print(f"Found {len(results)} recipes:\n")
    for i, (recipe, score, num_used, missing) in enumerate(results, 1):
        print_recipe(i, recipe, score, num_used, missing)
    
    # ============================================================================
    # TEST 6: Without Semantic Search (Fallback Mode)
    # ============================================================================
    print_separator("TEST 6: Exact Match Only (No Semantic)", "-")
    print("Scenario: Testing with use_semantic=False")
    print("Expected: Only exact ingredient matches, no semantic boosting\n")
    
    pantry = ["pasta", "tomato sauce", "mozzarella"]
    
    print(f"🥘 Pantry Items: {', '.join(pantry)}\n")
    
    results = agent.hybrid_query(
        pantry_items=pantry,
        query_text=None,
        top_k=5,
        allow_missing=2,
        use_semantic=False  # Disabled!
    )
    
    print(f"Found {len(results)} recipes (exact match only):\n")
    for i, (recipe, score, num_used, missing) in enumerate(results, 1):
        print_recipe(i, recipe, score, num_used, missing)
    
    # ============================================================================
    # TEST 7: Real-World Scenarios
    # ============================================================================
    print_separator("TEST 7: Real-World Usage Scenarios", "-")
    
    scenarios = [
        {
            "name": "🌅 Quick Weeknight Dinner",
            "pantry": ["chicken", "broccoli", "garlic", "ginger"],
            "query": "quick 30 minute dinner",
            "allow_missing": 3,
            "top_k": 3
        },
        {
            "name": "🎉 Weekend Cooking Project",
            "pantry": ["beef", "red wine", "carrots", "thyme"],
            "query": "slow cooked comfort food",
            "allow_missing": 5,
            "top_k": 3
        },
        {
            "name": "🥗 Healthy Lunch Prep",
            "pantry": ["spinach", "chickpeas", "feta", "cucumber"],
            "query": "healthy salad",
            "allow_missing": 2,
            "top_k": 3
        },
        {
            "name": "🍰 Dessert Craving",
            "pantry": ["chocolate chips", "eggs", "vanilla"],
            "query": "easy chocolate dessert",
            "allow_missing": 4,
            "top_k": 3
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print(f"Pantry: {', '.join(scenario['pantry'])}")
        print(f"Looking for: {scenario['query']}\n")
        
        results = agent.hybrid_query(
            pantry_items=scenario['pantry'],
            query_text=scenario['query'],
            top_k=scenario['top_k'],
            allow_missing=scenario['allow_missing'],
            use_semantic=True
        )
        
        if results:
            for i, (recipe, score, num_used, missing) in enumerate(results, 1):
                title = recipe.get('title', 'Unknown')
                print(f"   {i}. [{score:.0f} pts] {title}")
                print(f"      Uses {num_used} items | Missing: {len(missing)}")
        else:
            print("   No results found")
        print()
    
    # ============================================================================
    # Summary
    # ============================================================================
    print_separator("✅ Test Summary")
    
    print("""
🎯 HYBRID SEARCH - Your Production Method

Parameters:
  • pantry_items: List of ingredients you have (required)
  • query_text: What you want to eat (optional, but recommended)
  • top_k: Number of results to return (default: 20)
  • allow_missing: Max ingredients you're willing to buy (default: 0)
  • use_semantic: Enable semantic boosting (default: True)

How It Works:
  1. 📊 Exact Match: Finds recipes with your exact ingredients (all 2.2M recipes)
  2. 🧠 Semantic Search: Finds similar recipes (100k embedded recipes)
  3. 💯 LEFTOVR Scoring: Prioritizes using MORE leftovers
  4. ✨ Boost: Recipes in BOTH get +50 semantic bonus

Scoring Formula:
  Base Score = (num_used × 100) + 1000 - total_ingredients
  Final Score = Base Score + (semantic_similarity × 50) [if found in both]

Why This Works:
  ✓ Uses MORE leftovers = higher rank (3 items > 1 item)
  ✓ Fewer missing items = higher rank
  ✓ Semantic boost rewards matching your preferences
  ✓ Exact matching ensures you never miss perfect matches

Usage Examples:

  # Basic: Just leftovers
  results = agent.hybrid_query(
      pantry_items=["chicken", "rice", "soy sauce"],
      top_k=10,
      allow_missing=2
  )

  # Advanced: Leftovers + preferences
  results = agent.hybrid_query(
      pantry_items=["beef", "tomatoes", "pasta"],
      query_text="Italian comfort food",
      top_k=10,
      allow_missing=3,
      use_semantic=True
  )

  # Strict: Zero shopping
  results = agent.hybrid_query(
      pantry_items=["eggs", "milk", "flour"],
      query_text="breakfast",
      allow_missing=0  # Must use only pantry items!
  )

Return Format:
  List of (recipe_dict, score, num_used, missing_ingredients)
  
  Example:
    recipe_dict = {
        'id': 12345,
        'title': 'Lemon Chicken',
        'ner': ['chicken breast', 'lemon', 'garlic', ...],
        'directions': ['Step 1...', 'Step 2...', ...],  # ✅ Available!
        'link': 'http://...',
        'source': 'allrecipes.com'
    }
    score = 1496.0
    num_used = 5
    missing = ['white wine']

💡 NOTE: Directions are NOT in embeddings (keeping them lightweight),
         but ARE in metadata and returned with every recipe!

🚀 This is your production-ready method!
""")
    
    # ============================================================================
    # BONUS: Show Full Recipe Details with Directions
    # ============================================================================
    print_separator("🍳 BONUS: Full Recipe Details with Directions")
    print("Demonstrating that directions are available in metadata")
    print("even though they're NOT included in embeddings\n")
    
    pantry = ["chicken", "garlic", "lemon"]
    print(f"🥘 Pantry: {', '.join(pantry)}")
    print(f"🎯 Looking for: simple chicken recipe\n")
    
    results = agent.hybrid_query(
        pantry_items=pantry,
        query_text="simple easy chicken",
        top_k=2,
        allow_missing=2
    )
    
    for i, (recipe, score, num_used, missing) in enumerate(results, 1):
        print(f"\n{'='*80}")
        print(f"  RECIPE {i}: {recipe.get('title', 'Unknown')}")
        print(f"{'='*80}")
        
        print(f"\n💯 LEFTOVR Score: {score:.0f} points")
        print(f"✓ Uses {num_used} of your pantry items")
        if missing:
            print(f"⚠️  Missing: {', '.join(missing)}")
        else:
            print(f"✅ You have everything!")
        
        # Ingredients
        ingredients = recipe.get('ner', [])
        if ingredients:
            print(f"\n📝 INGREDIENTS ({len(ingredients)} total):")
            for ing in ingredients[:10]:
                print(f"   • {ing}")
            if len(ingredients) > 10:
                print(f"   ... and {len(ingredients) - 10} more")
        
        # Directions - Available from metadata!
        directions = recipe.get('directions', [])
        if directions:
            print(f"\n👨‍🍳 COOKING DIRECTIONS ({len(directions)} steps):")
            for j, step in enumerate(directions[:5], 1):
                step_text = step[:100] + "..." if len(step) > 100 else step
                print(f"   {j}. {step_text}")
            if len(directions) > 5:
                print(f"   ... and {len(directions) - 5} more steps")
        else:
            print(f"\n👨‍🍳 COOKING DIRECTIONS: Not available for this recipe")
        
        # Source
        print(f"\n🔗 Source: {recipe.get('source', 'Unknown')}")
        if recipe.get('link'):
            print(f"🌐 Link: {recipe.get('link')}")
        
        print(f"\n{'='*80}")

if __name__ == "__main__":
    main()
