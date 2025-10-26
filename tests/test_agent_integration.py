"""
Comprehensive Integration Test for Leftovr Multi-Agent System

This test validates:
1. Waiter Agent: Collects user preferences
2. Pantry Agent: Manages inventory and expiration tracking
3. Executive Chef Agent: Orchestrates workflow and synthesizes recommendations
4. Inter-agent communication and data flow
5. End-to-end workflow execution
"""

import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, Any
from langchain_openai import ChatOpenAI

from agents.waiter_agent import WaiterAgent
from agents.executive_chef_agent import ExecutiveChefAgent
from agents.pantry_agent import PantryAgent

# Load environment
load_dotenv()

# Initialize LLM for testing (using same model as main.py)
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key=os.getenv("OPEN_AI_API_KEY")
)

# Test utilities
def print_section(title: str):
    """Print a formatted test section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def print_test(test_name: str, passed: bool):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")


# Mock data setup
def get_mock_inventory():
    """Return mock inventory data for testing."""
    return [
        {
            'ingredient_name': 'Chicken Breast',
            'quantity': 2.5,
            'unit': 'lb',
            'expiration_date': (datetime.now() + timedelta(days=2)).date().isoformat(),
            'category': 'protein',
            'location': 'fridge',
            'last_updated': datetime.now().isoformat()
        },
        {
            'ingredient_name': 'Milk',
            'quantity': 1.0,
            'unit': 'quart',
            'expiration_date': (datetime.now() + timedelta(days=1)).date().isoformat(),
            'category': 'dairy',
            'location': 'fridge',
            'last_updated': datetime.now().isoformat()
        },
        {
            'ingredient_name': 'Eggs',
            'quantity': 12.0,
            'unit': 'piece',
            'expiration_date': (datetime.now() + timedelta(days=7)).date().isoformat(),
            'category': 'protein',
            'location': 'fridge',
            'last_updated': datetime.now().isoformat()
        },
        {
            'ingredient_name': 'Pasta',
            'quantity': 2.0,
            'unit': 'lb',
            'expiration_date': (datetime.now() + timedelta(days=180)).date().isoformat(),
            'category': 'carbs',
            'location': 'pantry',
            'last_updated': datetime.now().isoformat()
        },
        {
            'ingredient_name': 'Tomatoes',
            'quantity': 6.0,
            'unit': 'piece',
            'expiration_date': (datetime.now() + timedelta(days=3)).date().isoformat(),
            'category': 'vegetable',
            'location': 'fridge',
            'last_updated': datetime.now().isoformat()
        },
        {
            'ingredient_name': 'Olive Oil',
            'quantity': 16.0,
            'unit': 'oz',
            'expiration_date': (datetime.now() + timedelta(days=365)).date().isoformat(),
            'category': 'oil',
            'location': 'pantry',
            'last_updated': datetime.now().isoformat()
        },
        {
            'ingredient_name': 'Garlic',
            'quantity': 8.0,
            'unit': 'clove',
            'expiration_date': (datetime.now() + timedelta(days=14)).date().isoformat(),
            'category': 'vegetable',
            'location': 'pantry',
            'last_updated': datetime.now().isoformat()
        },
        {
            'ingredient_name': 'Onion',
            'quantity': 3.0,
            'unit': 'piece',
            'expiration_date': (datetime.now() + timedelta(days=10)).date().isoformat(),
            'category': 'vegetable',
            'location': 'pantry',
            'last_updated': datetime.now().isoformat()
        }
    ]


def get_mock_user_preferences():
    """Return mock user preferences for testing."""
    return {
        'diet': 'omnivore',
        'allergies': ['peanuts', 'shellfish'],
        'restrictions': ['no-pork'],
        'cuisines': ['Italian', 'Mediterranean'],
        'skill': 'home cook'
    }


# =============================================================================
# TEST 1: AGENT INITIALIZATION
# =============================================================================

def test_agent_initialization():
    """Test that all agents can be initialized properly."""
    print_section("TEST 1: Agent Initialization")

    try:
        waiter = WaiterAgent(name="Maison d'Être")
        print_test("Waiter Agent initialized", True)
        assert waiter.name == "Maison d'Être"

        exec_chef = ExecutiveChefAgent(name="Executive Chef")
        print_test("Executive Chef Agent initialized", True)
        assert exec_chef.name == "Executive Chef"

        pantry = PantryAgent(name="Pantry Manager")
        print_test("Pantry Agent initialized", True)
        assert pantry.name == "Pantry Manager"

        print("\n✅ All agents initialized successfully")
        return True

    except Exception as e:
        print(f"\n❌ Initialization failed: {str(e)}")
        return False


# =============================================================================
# TEST 2: WAITER AGENT - PREFERENCE EXTRACTION
# =============================================================================

def test_waiter_preference_extraction():
    """Test Waiter Agent's ability to extract user preferences."""
    print_section("TEST 2: Waiter Agent - Preference Extraction")

    waiter = WaiterAgent(name="Maison d'Être")

    # Test 1: Simple preference extraction
    user_input = "I'm vegan and allergic to nuts. I love Italian food and I'm a beginner cook."
    prefs = waiter.extract_preferences(llm, user_input)

    print(f"User input: '{user_input}'")
    print(f"Extracted preferences: {prefs}")

    has_diet = prefs.get('diet') is not None
    has_allergies = len(prefs.get('allergies', [])) > 0
    has_cuisines = len(prefs.get('cuisines', [])) > 0
    has_skill = prefs.get('skill') is not None

    print_test("Diet extracted", has_diet)
    print_test("Allergies extracted", has_allergies)
    print_test("Cuisines extracted", has_cuisines)
    print_test("Skill level extracted", has_skill)

    # Test 2: Complex preference extraction
    user_input2 = "I don't eat dairy or gluten. I'm allergic to shellfish and soy. I like Thai and Indian cuisine."
    prefs2 = waiter.extract_preferences(llm, user_input2)

    print(f"\nUser input 2: '{user_input2}'")
    print(f"Extracted preferences: {prefs2}")

    has_restrictions = len(prefs2.get('restrictions', [])) > 0
    print_test("Restrictions extracted", has_restrictions)

    success = has_diet and has_allergies and has_cuisines and has_skill and has_restrictions
    print(f"\n{'✅' if success else '❌'} Waiter preference extraction {'passed' if success else 'failed'}")
    return success


# =============================================================================
# TEST 3: PANTRY AGENT - INVENTORY MANAGEMENT
# =============================================================================

def test_pantry_inventory_management():
    """Test Pantry Agent's inventory management capabilities."""
    print_section("TEST 3: Pantry Agent - Inventory Management")

    pantry = PantryAgent(name="Pantry Manager")

    # Populate inventory
    mock_inventory = get_mock_inventory()
    for item in mock_inventory:
        pantry.inventory_cache[item['ingredient_name']] = item

    print(f"Loaded {len(mock_inventory)} items into pantry")

    # Test 1: Get inventory
    inventory = pantry.get_inventory()
    test_inventory = len(inventory) == len(mock_inventory)
    print_test(f"Get inventory ({len(inventory)} items)", test_inventory)

    # Test 2: Get pantry summary
    summary = pantry.get_pantry_summary()
    print(f"\nPantry Summary:")
    print(f"  Total ingredients: {summary['total_ingredients']}")
    print(f"  Expiring soon: {summary['expiring_soon']}")
    print(f"  Critical items: {summary['critical_items']}")
    print(f"  High priority items: {summary['high_priority_items']}")
    print(f"  Categories: {summary['categories']}")
    print(f"  Locations: {summary['locations']}")

    test_summary = summary['total_ingredients'] == len(mock_inventory)
    print_test("Pantry summary accurate", test_summary)

    # Test 3: Get expiring items
    expiring = pantry.get_expiring_soon(days_threshold=3)
    print(f"\nExpiring items (within 3 days): {len(expiring)}")
    for item in expiring:
        print(f"  • {item['ingredient_name']}: {item['priority']} priority "
              f"({item['days_until_expiry']} day(s) left)")

    test_expiring = len(expiring) > 0
    print_test("Expiring items detected", test_expiring)

    # Test 4: Get specific ingredient
    chicken = pantry.get_ingredient('Chicken Breast')
    test_get_ingredient = chicken is not None and chicken['quantity'] == 2.5
    print_test("Get specific ingredient", test_get_ingredient)

    success = test_inventory and test_summary and test_expiring and test_get_ingredient
    print(f"\n{'✅' if success else '❌'} Pantry inventory management {'passed' if success else 'failed'}")
    return success


# =============================================================================
# TEST 4: PANTRY AGENT - RECIPE FEASIBILITY
# =============================================================================

def test_pantry_recipe_feasibility():
    """Test Pantry Agent's recipe feasibility checking."""
    print_section("TEST 4: Pantry Agent - Recipe Feasibility")

    pantry = PantryAgent(name="Pantry Manager")

    # Populate inventory
    mock_inventory = get_mock_inventory()
    for item in mock_inventory:
        pantry.inventory_cache[item['ingredient_name']] = item

    # Test 1: Fully feasible recipe
    recipe1 = [
        {'name': 'Chicken Breast', 'quantity': 1.0, 'unit': 'lb'},
        {'name': 'Eggs', 'quantity': 4.0, 'unit': 'piece'},
        {'name': 'Olive Oil', 'quantity': 2.0, 'unit': 'oz'}
    ]

    result1 = pantry.check_recipe_feasibility(recipe1)
    print(f"Recipe 1 (Fully available):")
    print(f"  Feasible: {result1['feasible']}")
    print(f"  Completion: {result1['completion_percentage']:.0f}%")
    print(f"  Available: {len(result1['available_ingredients'])}")
    print(f"  Missing: {len(result1['missing_ingredients'])}")

    test_feasible = result1['feasible']
    print_test("Fully feasible recipe detected", test_feasible)

    # Test 2: Partially feasible recipe
    recipe2 = [
        {'name': 'Chicken Breast', 'quantity': 1.0, 'unit': 'lb'},
        {'name': 'Bacon', 'quantity': 0.5, 'unit': 'lb'},  # Not available
        {'name': 'Eggs', 'quantity': 4.0, 'unit': 'piece'}
    ]

    result2 = pantry.check_recipe_feasibility(recipe2)
    print(f"\nRecipe 2 (Partially available):")
    print(f"  Feasible: {result2['feasible']}")
    print(f"  Partially feasible: {result2['partially_feasible']}")
    print(f"  Completion: {result2['completion_percentage']:.0f}%")
    print(f"  Missing items:")
    for item in result2['missing_ingredients']:
        print(f"    • {item['ingredient']}: need {item['required']}")

    test_partial = result2['partially_feasible'] and not result2['feasible']
    print_test("Partially feasible recipe detected", test_partial)

    # Test 3: Insufficient quantity
    recipe3 = [
        {'name': 'Chicken Breast', 'quantity': 5.0, 'unit': 'lb'},  # Need more than available
    ]

    result3 = pantry.check_recipe_feasibility(recipe3)
    print(f"\nRecipe 3 (Insufficient quantity):")
    print(f"  Feasible: {result3['feasible']}")
    print(f"  Insufficient items:")
    for item in result3['insufficient_ingredients']:
        print(f"    • {item['ingredient']}: need {item['required']}, have {item['available']}")

    test_insufficient = len(result3['insufficient_ingredients']) > 0
    print_test("Insufficient quantity detected", test_insufficient)

    success = test_feasible and test_partial and test_insufficient
    print(f"\n{'✅' if success else '❌'} Recipe feasibility checking {'passed' if success else 'failed'}")
    return success


# =============================================================================
# TEST 5: PANTRY AGENT - INVENTORY UPDATES
# =============================================================================

def test_pantry_inventory_updates():
    """Test Pantry Agent's inventory update capabilities."""
    print_section("TEST 5: Pantry Agent - Inventory Updates")

    pantry = PantryAgent(name="Pantry Manager")

    # Populate inventory
    mock_inventory = get_mock_inventory()
    for item in mock_inventory:
        pantry.inventory_cache[item['ingredient_name']] = item

    initial_chicken = pantry.get_ingredient('Chicken Breast')['quantity']
    initial_eggs = pantry.get_ingredient('Eggs')['quantity']

    print(f"Initial quantities:")
    print(f"  Chicken Breast: {initial_chicken} lb")
    print(f"  Eggs: {initial_eggs} piece")

    # Test consumption
    consumption = [
        {'name': 'Chicken Breast', 'quantity': 1.0, 'unit': 'lb'},
        {'name': 'Eggs', 'quantity': 4.0, 'unit': 'piece'}
    ]

    result = pantry.consume_ingredients(consumption)

    print(f"\nConsumption result:")
    print(f"  Success: {result['success']}")
    print(f"  Updates: {len(result['updates'])}")

    for upd in result['updates']:
        print(f"    • {upd['ingredient']}: {upd['old_quantity']} → {upd['new_quantity']} {upd['unit']}")

    final_chicken = pantry.get_ingredient('Chicken Breast')['quantity']
    final_eggs = pantry.get_ingredient('Eggs')['quantity']

    print(f"\nFinal quantities:")
    print(f"  Chicken Breast: {final_chicken} lb")
    print(f"  Eggs: {final_eggs} piece")

    test_chicken = final_chicken == initial_chicken - 1.0
    test_eggs = final_eggs == initial_eggs - 4.0
    test_success = result['success']

    print_test("Chicken quantity updated correctly", test_chicken)
    print_test("Eggs quantity updated correctly", test_eggs)
    print_test("Update operation successful", test_success)

    success = test_chicken and test_eggs and test_success
    print(f"\n{'✅' if success else '❌'} Inventory updates {'passed' if success else 'failed'}")
    return success


# =============================================================================
# TEST 6: INTER-AGENT COMMUNICATION
# =============================================================================

def test_inter_agent_communication():
    """Test communication between agents."""
    print_section("TEST 6: Inter-Agent Communication")

    pantry = PantryAgent(name="Pantry Manager")
    exec_chef = ExecutiveChefAgent(name="Executive Chef")

    # Populate pantry
    mock_inventory = get_mock_inventory()
    for item in mock_inventory:
        pantry.inventory_cache[item['ingredient_name']] = item

    # Test 1: Pantry sends message to Executive Chef
    expiring = pantry.get_expiring_soon(days_threshold=3)
    message = pantry.create_message_to_agent(
        target_agent='executive_chef',
        action='expiration_alert',
        data={
            'expiring_items': expiring,
            'message': f"{len(expiring)} items expiring soon"
        },
        priority='high'
    )

    print("Message from Pantry to Executive Chef:")
    print(f"  From: {message['from']}")
    print(f"  To: {message['to']}")
    print(f"  Action: {message['action']}")
    print(f"  Priority: {message['priority']}")
    print(f"  Data keys: {list(message['data'].keys())}")

    test_message_created = (
        message['from'] == 'pantry_agent' and
        message['to'] == 'executive_chef' and
        message['priority'] == 'high'
    )
    print_test("Message created correctly", test_message_created)

    # Test 2: Pantry generates proactive alerts
    alerts = pantry.generate_expiration_alerts()
    print(f"\nProactive alerts generated: {len(alerts)}")

    if alerts:
        alert = alerts[0]
        print(f"  Alert to: {alert['to']}")
        print(f"  Priority: {alert['priority']}")
        print(f"  Critical items: {len(alert['data']['critical_items'])}")
        print(f"  High priority items: {len(alert['data']['high_priority_items'])}")

    test_alerts = len(alerts) > 0
    print_test("Proactive alerts generated", test_alerts)

    # Test 3: Pantry handles request from another agent
    request = {
        'from': 'executive_chef',
        'action': 'check_expiring',
        'data': {'days_threshold': 3}
    }

    response = pantry.handle_request_from_agent(request)

    print(f"\nRequest-Response cycle:")
    print(f"  Request action: {request['action']}")
    print(f"  Response success: {response['success']}")
    print(f"  Response data keys: {list(response['data'].keys())}")

    test_request_handling = response['success']
    print_test("Request handled successfully", test_request_handling)

    # Test 4: Executive Chef delegation
    delegation = exec_chef.delegate_to_pantry(
        action='check_inventory',
        parameters={'include_expiring': True}
    )

    print(f"\nExecutive Chef delegation:")
    print(f"  Agent: {delegation['agent']}")
    print(f"  Action: {delegation['action']}")
    print(f"  Delegated by: {delegation['delegated_by']}")

    test_delegation = delegation['agent'] == 'pantry'
    print_test("Delegation packet created", test_delegation)

    success = test_message_created and test_alerts and test_request_handling and test_delegation
    print(f"\n{'✅' if success else '❌'} Inter-agent communication {'passed' if success else 'failed'}")
    return success


# =============================================================================
# TEST 7: EXECUTIVE CHEF - DECISION MAKING
# =============================================================================

def test_executive_chef_decisions():
    """Test Executive Chef's decision-making capabilities."""
    print_section("TEST 7: Executive Chef - Decision Making")

    exec_chef = ExecutiveChefAgent(name="Executive Chef")

    # Test 1: Query type decision (ingredient-first)
    prefs1 = {
        'diet': 'omnivore',
        'allergies': [],
        'restrictions': [],
        'cuisines': [],
        'skill': 'home cook'
    }

    query_type1 = exec_chef.decide_query_type(prefs1)
    print(f"Scenario 1 (Simple preferences):")
    print(f"  Preferences: {prefs1}")
    print(f"  Query type: {query_type1}")

    test_ingredient_first = query_type1 == "ingredient"
    print_test("Ingredient-first strategy selected", test_ingredient_first)

    # Test 2: Query type decision (recipe-first)
    prefs2 = {
        'diet': 'vegan',
        'allergies': ['nuts', 'soy'],
        'restrictions': ['gluten-free', 'low-carb'],
        'cuisines': ['Italian', 'Thai'],
        'skill': 'expert'
    }

    query_type2 = exec_chef.decide_query_type(prefs2)
    print(f"\nScenario 2 (Complex constraints):")
    print(f"  Preferences: {prefs2}")
    print(f"  Query type: {query_type2}")

    test_recipe_first = query_type2 == "recipe"
    print_test("Recipe-first strategy selected for complex constraints", test_recipe_first)

    # Test 3: Complexity analysis
    print(f"\nComplexity Analysis:")
    analysis = exec_chef.analyze_request_complexity(
        llm,
        prefs2,
        "I want a healthy dinner for tonight"
    )

    print(f"  Complexity: {analysis['complexity']}")
    print(f"  Strategy: {analysis['strategy']}")
    print(f"  Required agents: {analysis['required_agents']}")
    print(f"  Estimated steps: {analysis['estimated_steps']}")

    test_analysis = 'complexity' in analysis and 'strategy' in analysis
    print_test("Complexity analysis completed", test_analysis)

    success = test_ingredient_first and test_recipe_first and test_analysis
    print(f"\n{'✅' if success else '❌'} Executive Chef decisions {'passed' if success else 'failed'}")
    return success


# =============================================================================
# TEST 8: EXECUTIVE CHEF - SYNTHESIS & QUALITY CHECK
# =============================================================================

def test_executive_chef_synthesis():
    """Test Executive Chef's synthesis and quality check capabilities."""
    print_section("TEST 8: Executive Chef - Synthesis & Quality Check")

    exec_chef = ExecutiveChefAgent(name="Executive Chef")
    pantry = PantryAgent(name="Pantry Manager")

    # Setup
    mock_inventory = get_mock_inventory()
    for item in mock_inventory:
        pantry.inventory_cache[item['ingredient_name']] = item

    user_prefs = get_mock_user_preferences()

    # Prepare agent responses
    agent_responses = {
        'user_preferences': user_prefs,
        'pantry_inventory': pantry.get_inventory(),
        'expiring_items': pantry.get_expiring_soon(days_threshold=3),
        'pantry_summary': pantry.get_pantry_summary()
    }

    print(f"User preferences:")
    for key, value in user_prefs.items():
        print(f"  {key}: {value}")

    print(f"\nPantry status:")
    print(f"  Total ingredients: {agent_responses['pantry_summary']['total_ingredients']}")
    print(f"  Expiring items: {len(agent_responses['expiring_items'])}")

    # Test synthesis
    print(f"\nGenerating recommendation...")
    recommendation = exec_chef.synthesize_recommendations(
        llm,
        agent_responses,
        user_prefs
    )

    print(f"\n--- RECOMMENDATION ---")
    print(recommendation[:500] + "..." if len(recommendation) > 500 else recommendation)
    print(f"--- END RECOMMENDATION ---")

    test_synthesis = len(recommendation) > 0
    print_test("Recommendation generated", test_synthesis)

    # Test quality check
    print(f"\nPerforming quality check...")
    passed, issues = exec_chef.perform_quality_check(
        llm,
        recommendation,
        user_prefs
    )

    print(f"  Quality check passed: {passed}")
    if issues:
        print(f"  Issues found: {len(issues)}")
        for issue in issues:
            print(f"    • {issue}")
    else:
        print(f"  No issues found")

    test_quality = isinstance(passed, bool) and isinstance(issues, list)
    print_test("Quality check executed", test_quality)

    success = test_synthesis and test_quality
    print(f"\n{'✅' if success else '❌'} Synthesis and quality check {'passed' if success else 'failed'}")
    return success


# =============================================================================
# TEST 9: END-TO-END WORKFLOW SIMULATION
# =============================================================================

def test_end_to_end_workflow():
    """Test the complete agent workflow without LangGraph."""
    print_section("TEST 9: End-to-End Workflow Simulation")

    # Initialize agents
    waiter = WaiterAgent(name="Maison d'Être")
    exec_chef = ExecutiveChefAgent(name="Executive Chef")
    pantry = PantryAgent(name="Pantry Manager")

    # Setup pantry
    mock_inventory = get_mock_inventory()
    for item in mock_inventory:
        pantry.inventory_cache[item['ingredient_name']] = item

    print("Step 1: Waiter collects user preferences")
    user_input = "I'm vegetarian, allergic to nuts, and I love Italian food. I'm a beginner cook."
    user_prefs = waiter.extract_preferences(llm, user_input)
    print(f"  User: '{user_input}'")
    print(f"  Extracted: {user_prefs}")

    test_step1 = user_prefs.get('diet') is not None
    print_test("Step 1: Preferences collected", test_step1)

    print("\nStep 2: Pantry checks inventory and expiring items")
    inventory = pantry.get_inventory()
    expiring = pantry.get_expiring_soon(days_threshold=3)
    summary = pantry.get_pantry_summary()
    print(f"  Inventory: {len(inventory)} items")
    print(f"  Expiring: {len(expiring)} items")

    test_step2 = len(inventory) > 0
    print_test("Step 2: Inventory checked", test_step2)

    print("\nStep 3: Pantry generates alerts for Executive Chef")
    alerts = pantry.generate_expiration_alerts()
    print(f"  Alerts generated: {len(alerts)}")
    if alerts:
        print(f"  Alert priority: {alerts[0]['priority']}")

    test_step3 = isinstance(alerts, list)
    print_test("Step 3: Alerts generated", test_step3)

    print("\nStep 4: Executive Chef analyzes complexity")
    query_type = exec_chef.decide_query_type(user_prefs)
    print(f"  Query type: {query_type}")

    test_step4 = query_type in ["ingredient", "recipe"]
    print_test("Step 4: Query type determined", test_step4)

    print("\nStep 5: Executive Chef synthesizes recommendation")
    agent_responses = {
        'user_preferences': user_prefs,
        'pantry_inventory': inventory,
        'expiring_items': expiring,
        'pantry_summary': summary
    }

    recommendation = exec_chef.synthesize_recommendations(
        llm,
        agent_responses,
        user_prefs
    )
    print(f"  Recommendation length: {len(recommendation)} characters")

    test_step5 = len(recommendation) > 100
    print_test("Step 5: Recommendation synthesized", test_step5)

    print("\nStep 6: Executive Chef performs quality check")
    passed, issues = exec_chef.perform_quality_check(
        llm,
        recommendation,
        user_prefs
    )
    print(f"  Quality passed: {passed}")
    print(f"  Issues: {len(issues)}")

    test_step6 = isinstance(passed, bool)
    print_test("Step 6: Quality check performed", test_step6)

    print("\nStep 7: Verify allergen compliance")
    # Check if recommendation mentions nuts (which user is allergic to)
    contains_allergen = any(allergen.lower() in recommendation.lower()
                           for allergen in user_prefs['allergies'])

    test_step7 = not contains_allergen
    print_test("Step 7: No allergens in recommendation", test_step7)

    success = all([test_step1, test_step2, test_step3, test_step4,
                   test_step5, test_step6, test_step7])

    print(f"\n{'✅' if success else '❌'} End-to-end workflow {'passed' if success else 'failed'}")
    return success


# =============================================================================
# TEST 10: OPERATION LOGGING & AUDIT TRAIL
# =============================================================================

def test_operation_logging():
    """Test that agents properly log their operations."""
    print_section("TEST 10: Operation Logging & Audit Trail")

    pantry = PantryAgent(name="Pantry Manager")
    exec_chef = ExecutiveChefAgent(name="Executive Chef")

    # Setup
    mock_inventory = get_mock_inventory()
    for item in mock_inventory:
        pantry.inventory_cache[item['ingredient_name']] = item

    # Perform various operations
    pantry.get_inventory()
    pantry.get_expiring_soon()
    pantry.generate_expiration_alerts()

    # Check pantry logs
    pantry_logs = pantry.get_operation_log()
    print(f"Pantry Agent operations logged: {len(pantry_logs)}")

    for log in pantry_logs[:3]:
        print(f"  • {log['operation']} at {log['timestamp']}")

    test_pantry_logs = len(pantry_logs) > 0
    print_test("Pantry operations logged", test_pantry_logs)

    # Perform Executive Chef operations
    exec_chef.delegate_to_pantry('check_inventory', {})
    exec_chef.delegate_to_pantry('check_expiring', {'days': 3})

    # Check Executive Chef logs
    delegation_logs = exec_chef.get_delegation_log()
    print(f"\nExecutive Chef delegations logged: {len(delegation_logs)}")

    for log in delegation_logs:
        print(f"  • {log['action']} to {log['agent']} at {log['timestamp']}")

    test_exec_logs = len(delegation_logs) > 0
    print_test("Executive Chef delegations logged", test_exec_logs)

    success = test_pantry_logs and test_exec_logs
    print(f"\n{'✅' if success else '❌'} Operation logging {'passed' if success else 'failed'}")
    return success


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("  LEFTOVR MULTI-AGENT SYSTEM - INTEGRATION TEST SUITE")
    print("="*80)

    results = []

    # Run all tests
    results.append(("Agent Initialization", test_agent_initialization()))
    results.append(("Waiter Preference Extraction", test_waiter_preference_extraction()))
    results.append(("Pantry Inventory Management", test_pantry_inventory_management()))
    results.append(("Pantry Recipe Feasibility", test_pantry_recipe_feasibility()))
    results.append(("Pantry Inventory Updates", test_pantry_inventory_updates()))
    results.append(("Inter-Agent Communication", test_inter_agent_communication()))
    results.append(("Executive Chef Decisions", test_executive_chef_decisions()))
    results.append(("Executive Chef Synthesis", test_executive_chef_synthesis()))
    results.append(("End-to-End Workflow", test_end_to_end_workflow()))
    results.append(("Operation Logging", test_operation_logging()))

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{'='*80}")
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*80}\n")

    if passed == total:
        print("🎉 ALL TESTS PASSED! The multi-agent system is working correctly.")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please review the output above.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

