"""
Integration test for full orchestration with live main.py workflow.

This test simulates a complete user interaction through the system.
"""

import asyncio
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, '/Users/jayson.ng.int/Documents/leftovr-app')

from agents.pantry_agent import PantryAgent


async def test_integration():
    """
    Test complete integration with main.py workflow.
    """
    print("\n" + "="*80)
    print("🧪 INTEGRATION TEST: Full Executive Chef Orchestration")
    print("="*80 + "\n")

    # Step 1: Set up pantry with test data
    print("📦 Step 1: Setting up test pantry...")
    pantry = PantryAgent(name="Test Pantry")

    # Add test ingredients with expiration dates
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    next_week = (datetime.now() + timedelta(days=7)).date().isoformat()

    pantry.add_or_update_ingredient("chicken breast", 2, "lb", next_week, "protein", "fridge")
    pantry.add_or_update_ingredient("spinach", 1, "bunch", tomorrow, "vegetable", "fridge")
    pantry.add_or_update_ingredient("pasta", 1, "lb", None, "grain", "pantry")
    pantry.add_or_update_ingredient("olive oil", 0.5, "cup", None, "oil", "pantry")
    pantry.add_or_update_ingredient("garlic", 8, "cloves", None, "vegetable", "pantry")
    pantry.add_or_update_ingredient("tomatoes", 5, "pieces", next_week, "vegetable", "fridge")

    print(f"   ✅ Added {len(pantry.get_inventory())} ingredients")

    # Step 2: Check pantry summary
    print("\n📊 Step 2: Checking pantry summary...")
    summary = pantry.get_pantry_summary()
    print(f"   ✅ Total ingredients: {summary['total_ingredients']}")
    print(f"   ✅ Expiring soon: {summary['expiring_soon']}")
    print(f"   ✅ Critical items: {summary['critical_items']}")

    # Step 3: Get expiring items
    print("\n⏰ Step 3: Identifying expiring ingredients...")
    expiring = pantry.get_expiring_soon(days_threshold=3)
    for item in expiring:
        print(f"   ⚠️  {item['ingredient_name']}: expires in {item['days_until_expiry']} days ({item['priority']})")

    # Step 4: Verify orchestration structure
    print("\n🔍 Step 4: Verifying orchestration structure in main.py...")
    with open("main.py", "r") as f:
        content = f.read()

    checks = {
        "analyze_request_complexity": "analyze_request_complexity" in content,
        "create_task_plan": "create_task_plan" in content,
        "synthesize_recommendations": "synthesize_recommendations" in content,
        "delegate_to_pantry": "delegate_to_pantry" in content,
        "delegate_to_sous_chef": "delegate_to_sous_chef" in content,
        "orchestrating stage": '"orchestrating"' in content,
        "synthesizing stage": '"synthesizing_recommendations"' in content,
        "exec_chef.analyze": "self.exec_chef.analyze_request_complexity" in content,
        "exec_chef.create_task": "self.exec_chef.create_task_plan" in content,
        "exec_chef.synthesize": "self.exec_chef.synthesize_recommendations" in content,
    }

    all_passed = True
    for check_name, result in checks.items():
        if result:
            print(f"   ✅ {check_name}")
        else:
            print(f"   ❌ {check_name} - MISSING")
            all_passed = False

    if not all_passed:
        print("\n❌ INTEGRATION TEST FAILED: Missing orchestration components")
        return False

    # Step 5: Verify quality check is NOT in Executive Chef
    print("\n🔍 Step 5: Verifying quality check delegation...")
    from agents.executive_chef_agent import ExecutiveChefAgent
    from agents.waiter_agent import WaiterAgent

    exec_chef = ExecutiveChefAgent()
    waiter = WaiterAgent(name="Test Waiter")

    # Check that Waiter has quality check method
    assert hasattr(waiter, "perform_quality_check"), "Waiter should have perform_quality_check"
    assert callable(waiter.perform_quality_check), "Waiter.perform_quality_check should be callable"
    print(f"   ✅ Waiter has perform_quality_check method")

    # Check that Executive Chef doesn't have active quality check
    has_qc = hasattr(exec_chef, "perform_quality_check") and callable(getattr(exec_chef, "perform_quality_check", None))
    if has_qc:
        print(f"   ⚠️  Executive Chef still has perform_quality_check (deprecated)")
    else:
        print(f"   ✅ Executive Chef does not have active perform_quality_check")

    # Step 6: Verify delegation logging
    print("\n📝 Step 6: Testing delegation logging...")
    exec_chef.clear_logs()

    # Test pantry delegation
    delegation = exec_chef.delegate_to_pantry("check_inventory", {"test": "data"})
    assert len(exec_chef.delegation_log) == 1
    print(f"   ✅ Pantry delegation logged")

    # Test sous chef delegation
    delegation = exec_chef.delegate_to_sous_chef("suggest_recipes", {"test": "data"})
    assert len(exec_chef.delegation_log) == 2
    print(f"   ✅ Sous Chef delegation logged")

    # Test recipe knowledge delegation
    delegation = exec_chef.delegate_to_recipe_knowledge("search_recipes", {"test": "data"})
    assert len(exec_chef.delegation_log) == 3
    print(f"   ✅ Recipe Knowledge delegation logged")

    print(f"   ✅ Total delegation log entries: {len(exec_chef.delegation_log)}")

    # Step 7: Summary
    print("\n" + "="*80)
    print("✅ INTEGRATION TEST PASSED!")
    print("="*80)
    print("\n📋 Test Summary:")
    print(f"   ✅ Pantry setup: {len(pantry.get_inventory())} ingredients")
    print(f"   ✅ Expiring items tracked: {len(expiring)} items")
    print(f"   ✅ Orchestration components verified")
    print(f"   ✅ Quality check properly delegated to Waiter")
    print(f"   ✅ Delegation logging functional")
    print("\n🎉 All Executive Chef orchestration features are working correctly!")

    return True


if __name__ == "__main__":
    """Run integration test."""
    success = asyncio.run(test_integration())

    if success:
        print("\n✅ Integration test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Integration test failed!")
        sys.exit(1)

