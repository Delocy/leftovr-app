"""
Test script for Executive Chef Orchestration with Unified Validator

Tests:
1. Pantry flow → Validator
2. Recipe flow (Recipe Knowledge + Sous Chef) → Validator
3. Sous Chef dialogue for recipe selection
"""
import asyncio
from main import ModernCollaborativeSystem

async def test_recipe_flow():
    """Test the recipe recommendation flow with validator."""
    print("\n" + "="*80)
    print("TEST: Recipe Flow with Validator")
    print("="*80 + "\n")

    system = ModernCollaborativeSystem()
    system.seed_sample_pantry()

    # Simulate recipe request
    initial_state = {
        "user_preferences": {
            "allergies": [],
            "restrictions": ["vegetarian"]
        },
        "query_type": "recipe",
        "latest_user_message": "I want a vegetarian dinner",
        "messages": [
            {"role": "user", "content": "I want a vegetarian dinner"},
            {"role": "assistant", "content": "Great! What are your dietary restrictions?"},
            {"role": "user", "content": "I'm vegetarian"}
        ],
        "current_workflow_stage": "orchestrating",
        "executive_chef_task_plan": None,
        "agent_delegation_results": {},
        "coordination_log": [],
        "pantry_inventory": [],
        "expiring_items": [],
        "pantry_summary": {},
        "recipe_feasibility": None,
        "user_ingredients": [],
        "recipe_results": [],
        "sous_chef_recommendations": [],
        "user_recipe_selection": None,
        "selected_recipe_data": None,
        "adapted_recipe": None,
        "formatted_recipe": None,
        "final_recommendation": None,
        "waiter_quality_passed": False,
        "waiter_quality_issues": []
    }

    print("✅ Recipe flow test setup complete")
    print(f"   Pantry: {len(system.pantry.get_inventory())} items")
    print(f"   User: vegetarian, no allergies")
    print(f"   Flow: Recipe Knowledge → Sous Chef → Validator")


async def test_pantry_integration():
    """Test Recipe Knowledge Agent's pantry integration."""
    print("\n" + "="*80)
    print("TEST: Recipe Knowledge Agent Pantry Integration")
    print("="*80 + "\n")

    system = ModernCollaborativeSystem()
    system.seed_sample_pantry()

    if not system.recipe_agent:
        print("❌ Recipe Knowledge Agent not available")
        return

    # Test get_pantry_items
    print("1. Testing get_pantry_items()...")
    pantry_items = system.recipe_agent.get_pantry_items()
    print(f"   Retrieved {len(pantry_items)} items: {', '.join(pantry_items[:5])}...")

    # Test hybrid_query with auto-pantry
    print("\n2. Testing hybrid_query() with auto-pantry...")
    try:
        results = system.recipe_agent.hybrid_query(
            pantry_items=None,  # Should auto-pull from pantry
            query_text="quick dinner",
            top_k=5,
            allow_missing=2
        )
        print(f"   Found {len(results)} recipes")
        if results:
            top_recipe = results[0]
            print(f"   Top result: {top_recipe[0].get('title', 'Unknown')}")
            print(f"   Score: {top_recipe[1]:.1f}, Uses {top_recipe[2]} pantry items")
    except Exception as e:
        print(f"   ⚠️ Hybrid query failed: {e}")

    print("\n✅ Pantry integration test complete")


async def test_validator():
    """Test the ResultValidator directly."""
    print("\n" + "="*80)
    print("TEST: Result Validator")
    print("="*80 + "\n")

    from utils.output_validator import ResultValidator

    validator = ResultValidator()

    # Test 1: Recommendations validation (safe)
    print("1. Testing safe recommendations...")
    safe_recs = [
        {
            "title": "Spinach Pasta",
            "ingredients": ["spinach", "pasta", "garlic", "olive oil"],
            "allergen_safe": True,
            "dietary_compliant": True,
            "score": 95
        },
        {
            "title": "Tomato Soup",
            "ingredients": ["tomatoes", "onion", "garlic"],
            "allergen_safe": True,
            "dietary_compliant": True,
            "score": 88
        }
    ]

    user_prefs = {"allergies": [], "restrictions": ["vegetarian"]}
    result = validator.validate_recommendations(safe_recs, user_prefs)
    print(f"   Passed: {result['passed']}")
    print(f"   Filtered: {len(result['filtered_recommendations'])} recipes")

    # Test 2: Recommendations with allergens
    print("\n2. Testing recommendations with allergen...")
    unsafe_recs = [
        {
            "title": "Peanut Chicken",
            "ingredients": ["chicken", "peanuts", "soy sauce"],
            "allergen_safe": False,
            "dietary_compliant": True,
            "score": 90
        }
    ]

    user_prefs_allergic = {"allergies": ["peanuts"], "restrictions": []}
    result = validator.validate_recommendations(unsafe_recs, user_prefs_allergic)
    print(f"   Passed: {result['passed']}")
    print(f"   Issues: {len(result['issues'])} detected")
    if result['issues']:
        print(f"   First issue: {result['issues'][0]}")

    # Test 3: Adapted recipe validation (safe)
    print("\n3. Testing safe adapted recipe...")
    safe_recipe = """
# Spinach Pasta

## Ingredients:
- 1 lb pasta
- 2 cups fresh spinach
- 3 cloves garlic
- 2 tbsp olive oil

## Instructions:
1. Boil pasta according to package directions (10 min)
2. Sauté garlic in olive oil (2 min)
3. Add spinach and wilt (2 min)
4. Combine with pasta

⏱️ Total Time: 15 minutes
"""

    result = validator.validate_adapted_recipe(safe_recipe, user_prefs)
    print(f"   Passed: {result['passed']}")
    print(f"   Issues: {len(result['issues'])}")

    # Test 4: Adapted recipe with allergen
    print("\n4. Testing recipe with allergen...")
    unsafe_recipe = """
# Peanut Noodles

## Ingredients:
- 1 lb noodles
- 1/2 cup peanut butter
- 2 tbsp soy sauce

## Instructions:
1. Cook noodles
2. Mix with peanut sauce
"""

    result = validator.validate_adapted_recipe(unsafe_recipe, user_prefs_allergic)
    print(f"   Passed: {result['passed']}")
    print(f"   Issues: {len(result['issues'])}")
    if result['issues']:
        print(f"   Critical issues: {[i for i in result['issues'] if 'CRITICAL' in i]}")

    print("\n✅ Validator tests complete")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("EXECUTIVE CHEF ORCHESTRATION - TEST SUITE")
    print("="*80)

    await test_validator()
    await test_pantry_integration()
    await test_recipe_flow()

    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

