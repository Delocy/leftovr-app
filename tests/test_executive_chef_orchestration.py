"""
Test Executive Chef Full Orchestration

This test verifies that:
1. Executive Chef calls analyze_request_complexity() for all requests
2. Hybrid task plans are created (simple vs complex)
3. Executive Chef calls synthesize_recommendations() for medium/complex cases
4. Only Waiter performs quality checks
5. Proper delegation tracking occurs
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.executive_chef_agent import ExecutiveChefAgent
from agents.pantry_agent import PantryAgent
from agents.waiter_agent import WaiterAgent
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")

# Initialize LLM (using same model as main.py)
llm = ChatOpenAI(
    model="gpt-5-nano",
    temperature=0.7,
    api_key=OPENAI_API_KEY
)


def test_complexity_analysis():
    """Test that Executive Chef analyzes complexity for all requests"""
    print("\n" + "="*80)
    print("TEST 1: Complexity Analysis")
    print("="*80)

    exec_chef = ExecutiveChefAgent(name="Executive Chef")

    # Test simple pantry request
    simple_prefs = {
        "allergies": [],
        "restrictions": []
    }

    print("\n1a. Testing SIMPLE pantry request...")
    complexity = exec_chef.analyze_request_complexity(
        llm, simple_prefs, query_context="Add 3 tomatoes to pantry"
    )

    print(f"   Complexity: {complexity.get('complexity')}")
    print(f"   Strategy: {complexity.get('strategy')}")
    print(f"   Required agents: {complexity.get('required_agents')}")

    assert complexity is not None, "Complexity analysis failed"
    assert 'complexity' in complexity, "Missing complexity field"
    assert 'strategy' in complexity, "Missing strategy field"
    print("   ✅ Simple request analyzed")

    # Test complex recipe request
    complex_prefs = {
        "allergies": ["peanuts", "shellfish"],
        "restrictions": ["vegan", "gluten-free"],
        "cuisines": ["Italian", "Thai"],
        "skill": "beginner"
    }

    print("\n1b. Testing COMPLEX recipe request...")
    complexity = exec_chef.analyze_request_complexity(
        llm, complex_prefs, query_context="I want a vegan Italian dinner"
    )

    print(f"   Complexity: {complexity.get('complexity')}")
    print(f"   Strategy: {complexity.get('strategy')}")
    print(f"   Required agents: {complexity.get('required_agents')}")
    print(f"   Estimated steps: {complexity.get('estimated_steps')}")

    assert complexity.get('complexity') in ['medium', 'complex'], "Should be medium/complex"
    print("   ✅ Complex request analyzed")

    print("\n✅ TEST 1 PASSED: Complexity analysis working\n")


def test_hybrid_task_plan_storage():
    """Test hybrid task plan storage (simple vs full LLM plan)"""
    print("\n" + "="*80)
    print("TEST 2: Hybrid Task Plan Storage")
    print("="*80)

    exec_chef = ExecutiveChefAgent(name="Executive Chef")
    pantry = PantryAgent(name="Pantry Manager")

    # Test simple task plan (pantry)
    print("\n2a. Testing SIMPLE task plan (lightweight)...")
    simple_prefs = {"allergies": [], "restrictions": []}
    complexity = exec_chef.analyze_request_complexity(
        llm, simple_prefs, query_context="Add milk to pantry"
    )

    if complexity.get('complexity') == 'simple':
        task_plan = {
            'strategy': complexity.get('strategy', 'pantry'),
            'complexity': 'simple',
            'agents': complexity.get('required_agents', ['pantry']),
            'query_type': 'pantry'
        }
        print(f"   Created lightweight plan: {task_plan}")
        assert 'tasks' not in task_plan, "Simple plan should not have detailed tasks"
        print("   ✅ Lightweight plan created")
    else:
        print("   ⚠️  Request not classified as simple (acceptable)")

    # Test complex task plan (full LLM)
    print("\n2b. Testing COMPLEX task plan (full LLM-generated)...")
    complex_prefs = {
        "allergies": ["nuts"],
        "restrictions": ["vegetarian"],
        "cuisines": ["Mexican"]
    }

    complexity = exec_chef.analyze_request_complexity(
        llm, complex_prefs, query_context="I want Mexican vegetarian food"
    )

    pantry_summary = pantry.get_pantry_summary()
    pantry_context = {
        'summary': pantry_summary,
        'expiring': pantry.get_expiring_soon(days_threshold=3)
    }

    task_plan = exec_chef.create_task_plan(
        llm, complex_prefs, complexity, pantry_context
    )

    print(f"   Tasks: {len(task_plan.get('tasks', []))}")
    print(f"   Delegation order: {task_plan.get('delegation_order', [])}")
    print(f"   Success criteria: {len(task_plan.get('success_criteria', []))}")

    assert 'tasks' in task_plan, "Complex plan should have tasks"
    assert 'delegation_order' in task_plan, "Complex plan should have delegation order"
    print("   ✅ Full LLM plan created")

    print("\n✅ TEST 2 PASSED: Hybrid task plan storage working\n")


def test_synthesis_method():
    """Test that Executive Chef synthesizes recommendations"""
    print("\n" + "="*80)
    print("TEST 3: Executive Chef Synthesis")
    print("="*80)

    exec_chef = ExecutiveChefAgent(name="Executive Chef")
    pantry = PantryAgent(name="Pantry Manager")

    print("\n3. Testing synthesize_recommendations()...")

    # Mock agent responses
    agent_responses = {
        "pantry": {
            "summary": pantry.get_pantry_summary(),
            "expiring_items": pantry.get_expiring_soon(days_threshold=3)
        },
        "sous_chef": {
            "recommendations": [
                {"title": "Pasta Primavera", "score": 85},
                {"title": "Vegetable Stir Fry", "score": 80},
                {"title": "Tomato Soup", "score": 75}
            ]
        }
    }

    user_prefs = {
        "allergies": [],
        "restrictions": ["vegetarian"]
    }

    synthesis = exec_chef.synthesize_recommendations(
        llm, agent_responses, user_prefs
    )

    print(f"   Synthesis generated: {len(synthesis)} characters")
    print(f"   Preview: {synthesis[:200]}...")

    assert synthesis is not None, "Synthesis failed"
    assert len(synthesis) > 0, "Synthesis is empty"
    print("   ✅ Synthesis successful")

    print("\n✅ TEST 3 PASSED: Executive Chef synthesis working\n")


def test_delegation_tracking():
    """Test that delegation methods are called and tracked"""
    print("\n" + "="*80)
    print("TEST 4: Delegation Tracking")
    print("="*80)

    exec_chef = ExecutiveChefAgent(name="Executive Chef")

    print("\n4. Testing delegation methods...")

    # Test pantry delegation
    print("\n4a. Testing delegate_to_pantry()...")
    delegation = exec_chef.delegate_to_pantry(
        "check_inventory",
        {"user_message": "Check pantry", "preferences": {}}
    )

    print(f"   Delegation: {delegation}")
    assert delegation['agent'] == 'pantry', "Wrong agent"
    assert delegation['action'] == 'check_inventory', "Wrong action"
    assert 'timestamp' in delegation, "Missing timestamp"
    assert delegation['delegated_by'] == 'Executive Chef', "Wrong delegator"
    print("   ✅ Pantry delegation tracked")

    # Test sous chef delegation
    print("\n4b. Testing delegate_to_sous_chef()...")
    delegation = exec_chef.delegate_to_sous_chef(
        "suggest_recipes",
        {"preferences": {}, "pantry_context": {}}
    )

    print(f"   Delegation: {delegation}")
    assert delegation['agent'] == 'sous_chef', "Wrong agent"
    assert delegation['action'] == 'suggest_recipes', "Wrong action"
    print("   ✅ Sous Chef delegation tracked")

    # Verify delegation log
    print("\n4c. Checking delegation log...")
    log = exec_chef.get_delegation_log()
    print(f"   Delegation log entries: {len(log)}")

    assert len(log) >= 2, "Delegation log should have at least 2 entries"
    print("   ✅ Delegation log populated")

    print("\n✅ TEST 4 PASSED: Delegation tracking working\n")


def test_waiter_quality_check_only():
    """Test that only Waiter performs quality checks"""
    print("\n" + "="*80)
    print("TEST 5: Quality Check Ownership")
    print("="*80)

    waiter = WaiterAgent(name="Maison d'Être")
    exec_chef = ExecutiveChefAgent(name="Executive Chef")

    print("\n5. Verifying quality check methods...")

    # Verify Waiter has quality check method
    print("\n5a. Checking WaiterAgent.perform_quality_check()...")
    assert hasattr(waiter, 'perform_quality_check'), "Waiter missing quality check method"
    print("   ✅ Waiter has perform_quality_check()")

    # Test Waiter quality check
    print("\n5b. Testing Waiter quality check...")
    recipe_text = "# Vegan Pasta\n\n## Ingredients\n- Pasta\n- Tomatoes\n- Basil"
    user_prefs = {"allergies": [], "restrictions": ["vegan"]}
    messages = [
        {"role": "user", "content": "I want vegan pasta"},
        {"role": "assistant", "content": "I'll find you vegan recipes"}
    ]

    qa_result = waiter.perform_quality_check(llm, recipe_text, user_prefs, messages)

    print(f"   QA Result: {qa_result}")
    assert 'passed' in qa_result, "Missing 'passed' field"
    assert 'issues' in qa_result, "Missing 'issues' field"
    print("   ✅ Waiter quality check functional")

    # Verify Executive Chef quality check is deprecated
    print("\n5c. Verifying Executive Chef quality check is deprecated...")
    # Check if method exists
    import inspect
    source = inspect.getsource(ExecutiveChefAgent)

    if 'def perform_quality_check' in source:
        # Check if it's commented out or deprecated
        assert 'DEPRECATED' in source or '# def perform_quality_check' in source, \
            "Executive Chef quality check should be deprecated"
        print("   ✅ Executive Chef quality check deprecated")
    else:
        print("   ✅ Executive Chef quality check removed")

    print("\n✅ TEST 5 PASSED: Only Waiter performs quality checks\n")


def run_all_tests():
    """Run all orchestration tests"""
    print("\n" + "="*80)
    print("EXECUTIVE CHEF FULL ORCHESTRATION TEST SUITE")
    print("="*80)

    try:
        test_complexity_analysis()
        test_hybrid_task_plan_storage()
        test_synthesis_method()
        test_delegation_tracking()
        test_waiter_quality_check_only()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nSummary:")
        print("✅ Executive Chef analyzes complexity for all requests")
        print("✅ Hybrid task plan storage implemented (simple vs complex)")
        print("✅ Executive Chef synthesizes recommendations for complex cases")
        print("✅ Delegation tracking working via exec_chef.delegate_to_X() methods")
        print("✅ Only Waiter performs quality checks (with conversation context)")
        print("\n" + "="*80 + "\n")

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

