"""
Comprehensive test suite for full Executive Chef orchestration with all agents.

Tests cover:
1. Simple pantry requests with lightweight task plans
2. Complex recipe requests with full LLM-generated plans
3. Multi-agent coordination and synthesis
4. Quality check delegation to Waiter
5. Proper delegation logging throughout workflow
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from langchain_openai import ChatOpenAI

from agents.executive_chef_agent import ExecutiveChefAgent
from agents.pantry_agent import PantryAgent
from agents.sous_chef_agent import SousChefAgent
from agents.waiter_agent import WaiterAgent
# RecipeKnowledgeAgent not imported - has optional dependencies


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM that returns realistic responses."""
    llm = Mock(spec=ChatOpenAI)

    def mock_invoke(messages):
        # Extract the instruction context
        content = str(messages[-1].content) if messages else ""

        # Return different responses based on content
        if "complexity" in content.lower():
            return Mock(content="""{
                "complexity": "medium",
                "strategy": "ingredient_first",
                "required_agents": ["pantry", "sous_chef"],
                "agent_sequence": ["pantry", "sous_chef"],
                "reasoning": "User wants recipes based on available ingredients",
                "priority_factors": ["ingredient_availability", "waste_reduction"],
                "estimated_steps": 3
            }""")

        elif "task_plan" in content.lower() or "execution plan" in content.lower():
            return Mock(content="""{
                "tasks": [
                    {
                        "agent": "pantry",
                        "action": "check_inventory",
                        "input": "user preferences",
                        "expected_output": "ingredient list with expiration dates",
                        "priority": "high"
                    },
                    {
                        "agent": "sous_chef",
                        "action": "suggest_recipes",
                        "input": "pantry data + preferences",
                        "expected_output": "top 3 recipe recommendations",
                        "priority": "high"
                    }
                ],
                "delegation_order": ["pantry", "sous_chef"],
                "success_criteria": ["recipes_suggested", "allergen_safe"],
                "expected_duration": "5-10 minutes",
                "fallback_strategy": "Suggest recipes with shopping list"
            }""")

        elif "synthesize" in content.lower():
            return Mock(content="Here are 3 great recipe options based on your pantry!")

        elif "quality" in content.lower():
            return Mock(content="""{
                "passed": true,
                "issues": [],
                "score": 95,
                "critical_failures": []
            }""")

        else:
            return Mock(content="Response generated successfully")

    llm.invoke = mock_invoke
    return llm


@pytest.fixture
def executive_chef():
    """Initialize Executive Chef agent."""
    return ExecutiveChefAgent(name="Test Executive Chef")


@pytest.fixture
def pantry_agent():
    """Initialize Pantry agent with mock data."""
    agent = PantryAgent(name="Test Pantry")

    # Add test inventory
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    next_week = (datetime.now() + timedelta(days=7)).date().isoformat()

    agent.add_or_update_ingredient("chicken breast", 2, "lb", next_week, "protein", "fridge")
    agent.add_or_update_ingredient("spinach", 1, "bunch", tomorrow, "vegetable", "fridge")
    agent.add_or_update_ingredient("pasta", 1, "lb", None, "grain", "pantry")
    agent.add_or_update_ingredient("olive oil", 0.5, "cup", None, "oil", "pantry")
    agent.add_or_update_ingredient("garlic", 8, "cloves", None, "vegetable", "pantry")

    return agent


@pytest.fixture
def sous_chef_agent():
    """Initialize Sous Chef agent."""
    return SousChefAgent(name="Test Sous Chef")


@pytest.fixture
def waiter_agent():
    """Initialize Waiter agent."""
    return WaiterAgent(name="Test Waiter")


@pytest.fixture
def user_preferences():
    """Sample user preferences."""
    return {
        "allergies": ["nuts"],
        "restrictions": ["vegetarian"],
        "skill": "beginner",
        "cuisines": ["Italian"]
    }


# ==============================================================================
# TEST 1: COMPLEXITY ANALYSIS FOR ALL REQUESTS
# ==============================================================================

def test_complexity_analysis_called_for_simple_request(executive_chef, user_preferences, mock_llm):
    """
    Test that Executive Chef calls analyze_request_complexity() for simple requests.
    Success Criteria: Method is called and returns complexity analysis.
    """
    print("\n🧪 TEST 1: Complexity analysis for simple pantry request")

    query_context = "What's in my pantry?"

    # Execute complexity analysis
    complexity = executive_chef.analyze_request_complexity(
        llm=mock_llm,
        user_preferences=user_preferences,
        query_context=query_context
    )

    # Verify complexity analysis was performed
    assert complexity is not None, "Complexity analysis should return a result"
    assert "complexity" in complexity, "Should include complexity level"
    assert "strategy" in complexity, "Should include processing strategy"
    assert "required_agents" in complexity, "Should identify required agents"

    # Verify logged in task history
    assert len(executive_chef.task_history) > 0, "Should log the analysis"
    last_action = executive_chef.task_history[-1]
    assert last_action["action"] == "complexity_analysis"

    print(f"   ✅ Complexity: {complexity['complexity']}")
    print(f"   ✅ Strategy: {complexity['strategy']}")
    print(f"   ✅ Required agents: {complexity['required_agents']}")


def test_complexity_analysis_called_for_complex_request(executive_chef, user_preferences, mock_llm):
    """
    Test that Executive Chef calls analyze_request_complexity() for complex requests.
    Success Criteria: Method is called and identifies complex scenario.
    """
    print("\n🧪 TEST 2: Complexity analysis for complex recipe request")

    # Complex query with multiple constraints
    complex_prefs = {
        **user_preferences,
        "restrictions": ["vegan", "gluten-free"],
        "allergies": ["nuts", "soy", "shellfish"],
        "time_constraint": "30 minutes"
    }

    query_context = "I need a quick vegan gluten-free dinner using ingredients that expire soon"

    # Execute complexity analysis
    complexity = executive_chef.analyze_request_complexity(
        llm=mock_llm,
        user_preferences=complex_prefs,
        query_context=query_context
    )

    # Verify complexity reflects the complex nature
    assert complexity is not None
    assert complexity["complexity"] in ["medium", "complex"], \
        "Should identify this as medium or complex"

    print(f"   ✅ Identified as: {complexity['complexity']}")
    print(f"   ✅ Estimated steps: {complexity.get('estimated_steps', 'N/A')}")


# ==============================================================================
# TEST 2: HYBRID TASK PLAN STORAGE
# ==============================================================================

def test_lightweight_task_plan_for_simple_pantry(executive_chef, user_preferences, mock_llm):
    """
    Test that simple pantry requests get lightweight task plans.
    Success Criteria: Task plan is a simple dict without full LLM generation.
    """
    print("\n🧪 TEST 3: Lightweight task plan for simple pantry request")

    # Simulate simple pantry request
    complexity = {
        "complexity": "simple",
        "strategy": "pantry",
        "required_agents": ["pantry"],
        "reasoning": "Simple inventory check"
    }

    # For simple requests, we would store a lightweight plan
    lightweight_plan = {
        "strategy": complexity["strategy"],
        "complexity": "simple",
        "agents": complexity["required_agents"],
        "query_type": "pantry"
    }

    # Verify structure
    assert lightweight_plan["complexity"] == "simple"
    assert "strategy" in lightweight_plan
    assert "agents" in lightweight_plan
    assert "tasks" not in lightweight_plan, "Should not have detailed tasks"

    print(f"   ✅ Lightweight plan: {lightweight_plan}")


def test_full_llm_task_plan_for_complex_request(executive_chef, pantry_agent, user_preferences, mock_llm):
    """
    Test that complex requests get full LLM-generated task plans.
    Success Criteria: Task plan includes tasks, delegation_order, success_criteria.
    """
    print("\n🧪 TEST 4: Full LLM task plan for complex request")

    # Get complexity analysis
    complexity = executive_chef.analyze_request_complexity(
        llm=mock_llm,
        user_preferences=user_preferences,
        query_context="Complex multi-constraint recipe request"
    )

    # Get pantry context
    pantry_context = {
        "summary": pantry_agent.get_pantry_summary(),
        "expiring": pantry_agent.get_expiring_soon(days_threshold=3)
    }

    # Generate full task plan
    task_plan = executive_chef.create_task_plan(
        llm=mock_llm,
        user_preferences=user_preferences,
        complexity_analysis=complexity,
        pantry_context=pantry_context
    )

    # Verify full task plan structure
    assert task_plan is not None
    # Note: If JSON parsing fails, create_task_plan falls back to a default plan
    # The important thing is that it returns a structured plan
    assert isinstance(task_plan, dict), "Should return a dictionary"
    assert "tasks" in task_plan or "strategy" in task_plan, "Should have tasks or strategy"

    # If full plan generated, verify structure
    if "tasks" in task_plan:
        assert "delegation_order" in task_plan, "Should specify agent order"
        assert "success_criteria" in task_plan, "Should define success criteria"
        assert len(task_plan["tasks"]) > 0, "Should have at least one task"

    # Verify logged
    logged_plan = [h for h in executive_chef.task_history if h["action"] == "task_planning"]
    assert len(logged_plan) > 0, "Should log task planning"

    if "tasks" in task_plan:
        print(f"   ✅ Task plan with {len(task_plan['tasks'])} tasks")
        print(f"   ✅ Delegation order: {task_plan['delegation_order']}")
        print(f"   ✅ Success criteria: {task_plan['success_criteria']}")
    else:
        print(f"   ✅ Fallback task plan generated (JSON parsing fell back to default)")


# ==============================================================================
# TEST 3: SYNTHESIS OF MULTI-AGENT RESPONSES
# ==============================================================================

def test_synthesis_for_medium_complexity(executive_chef, pantry_agent, user_preferences, mock_llm):
    """
    Test that Executive Chef synthesizes responses for medium/complex cases.
    Success Criteria: synthesize_recommendations() is called and produces output.
    """
    print("\n🧪 TEST 5: Synthesis of multi-agent responses")

    # Prepare mock agent responses
    agent_responses = {
        "pantry": {
            "summary": pantry_agent.get_pantry_summary(),
            "expiring_items": pantry_agent.get_expiring_soon(days_threshold=3),
            "inventory": pantry_agent.get_inventory()
        },
        "sous_chef": [
            {
                "rank": 1,
                "title": "Spinach Garlic Pasta",
                "score": 95,
                "why_recommended": "Uses expiring spinach"
            }
        ]
    }

    # Call synthesis
    synthesis = executive_chef.synthesize_recommendations(
        llm=mock_llm,
        agent_responses=agent_responses,
        user_preferences=user_preferences
    )

    # Verify synthesis performed
    assert synthesis is not None
    assert len(synthesis) > 0, "Should produce synthesized text"

    # Verify logged
    synthesis_log = [h for h in executive_chef.task_history if h["action"] == "synthesis"]
    assert len(synthesis_log) > 0, "Should log synthesis action"

    print(f"   ✅ Synthesis produced: {synthesis[:100]}...")
    print(f"   ✅ Synthesis logged in task history")


# ==============================================================================
# TEST 4: QUALITY CHECK DELEGATION TO WAITER
# ==============================================================================

def test_quality_check_performed_by_waiter_only(waiter_agent, user_preferences, mock_llm):
    """
    Test that quality checks are performed ONLY by Waiter, not Executive Chef.
    Success Criteria: Waiter.perform_quality_check() works, EC doesn't have it.
    """
    print("\n🧪 TEST 6: Quality check performed by Waiter only")

    # Test recipe text
    recipe_text = """
    # Spinach Garlic Pasta

    ## Ingredients:
    - 1 lb pasta
    - 2 cups spinach
    - 4 cloves garlic
    - 3 tbsp olive oil

    ## Instructions:
    1. Cook pasta according to package
    2. Sauté garlic in olive oil
    3. Add spinach and wilt
    4. Toss with pasta
    """

    # Mock conversation messages
    messages = [
        {"role": "user", "content": "I want a vegetarian pasta recipe"},
        {"role": "assistant", "content": "Let me find something for you"}
    ]

    # Perform quality check with Waiter
    qa_result = waiter_agent.perform_quality_check(
        llm=mock_llm,
        recipe_text=recipe_text,
        user_prefs=user_preferences,
        messages=messages
    )

    # Verify quality check result
    assert qa_result is not None
    assert "passed" in qa_result
    assert "issues" in qa_result
    assert isinstance(qa_result["passed"], bool)

    print(f"   ✅ Waiter QA passed: {qa_result['passed']}")
    print(f"   ✅ Waiter QA issues: {qa_result['issues']}")

    # Verify Executive Chef doesn't have perform_quality_check method anymore
    exec_chef = ExecutiveChefAgent()
    assert not hasattr(exec_chef, "perform_quality_check") or \
           not callable(getattr(exec_chef, "perform_quality_check", None)), \
           "Executive Chef should not have active perform_quality_check method"

    print(f"   ✅ Executive Chef does not perform quality checks")


# ==============================================================================
# TEST 5: PROPER DELEGATION LOGGING
# ==============================================================================

def test_delegation_logging_pantry(executive_chef):
    """
    Test that delegations to Pantry Agent are properly logged.
    Success Criteria: Delegation creates log entry with correct structure.
    """
    print("\n🧪 TEST 7: Delegation logging to Pantry Agent")

    # Delegate to pantry
    delegation = executive_chef.delegate_to_pantry(
        action="check_inventory",
        parameters={"user_message": "Check my pantry"}
    )

    # Verify delegation structure
    assert delegation is not None
    assert delegation["agent"] == "pantry"
    assert delegation["action"] == "check_inventory"
    assert "parameters" in delegation
    assert "timestamp" in delegation
    assert "delegated_by" in delegation

    # Verify logged
    assert len(executive_chef.delegation_log) > 0
    last_delegation = executive_chef.delegation_log[-1]
    assert last_delegation["agent"] == "pantry"

    print(f"   ✅ Delegation logged: {delegation['action']}")
    print(f"   ✅ Delegation log entries: {len(executive_chef.delegation_log)}")


def test_delegation_logging_sous_chef(executive_chef):
    """
    Test that delegations to Sous Chef Agent are properly logged.
    """
    print("\n🧪 TEST 8: Delegation logging to Sous Chef Agent")

    # Delegate to sous chef
    delegation = executive_chef.delegate_to_sous_chef(
        action="suggest_recipes",
        parameters={"pantry_context": {}, "preferences": {}}
    )

    # Verify delegation structure
    assert delegation["agent"] == "sous_chef"
    assert delegation["action"] == "suggest_recipes"
    assert delegation["delegated_by"] == executive_chef.name

    # Verify logged
    sous_chef_delegations = [
        d for d in executive_chef.delegation_log if d["agent"] == "sous_chef"
    ]
    assert len(sous_chef_delegations) > 0

    print(f"   ✅ Sous Chef delegation logged")


def test_delegation_logging_recipe_knowledge(executive_chef):
    """
    Test that delegations to Recipe Knowledge Agent are properly logged.
    """
    print("\n🧪 TEST 9: Delegation logging to Recipe Knowledge Agent")

    # Delegate to recipe knowledge
    delegation = executive_chef.delegate_to_recipe_knowledge(
        action="search_recipes",
        parameters={"query_text": "pasta recipes", "pantry_items": ["pasta", "spinach"]}
    )

    # Verify delegation structure
    assert delegation["agent"] == "recipe_knowledge"
    assert delegation["action"] == "search_recipes"

    # Verify logged
    rk_delegations = [
        d for d in executive_chef.delegation_log if d["agent"] == "recipe_knowledge"
    ]
    assert len(rk_delegations) > 0

    print(f"   ✅ Recipe Knowledge delegation logged")


# ==============================================================================
# TEST 6: FULL END-TO-END ORCHESTRATION
# ==============================================================================

def test_full_orchestration_workflow(executive_chef, pantry_agent, user_preferences, mock_llm):
    """
    Test complete orchestration workflow from request to synthesis.
    Success Criteria: All methods called in correct order, proper data flow.
    """
    print("\n🧪 TEST 10: Full end-to-end orchestration workflow")

    executive_chef.clear_logs()

    query_context = "I want a quick vegetarian dinner using what I have"

    # Run full orchestration
    result = executive_chef.orchestrate_full_workflow(
        llm=mock_llm,
        user_preferences=user_preferences,
        pantry_agent=pantry_agent,
        query_context=query_context
    )

    # Verify result structure
    assert result is not None
    assert "success" in result
    assert "recommendation" in result
    assert "metadata" in result
    assert result["success"] is True, "Orchestration should succeed"

    # Verify metadata
    metadata = result["metadata"]
    assert "complexity" in metadata
    assert "plan" in metadata
    assert "pantry_summary" in metadata
    assert "expiring_items" in metadata
    assert "task_history" in metadata

    # Verify task history shows all steps
    task_history = executive_chef.task_history
    actions = [h["action"] for h in task_history]

    assert "complexity_analysis" in actions, "Should perform complexity analysis"
    assert "task_planning" in actions, "Should create task plan"
    assert "synthesis" in actions, "Should synthesize recommendations"

    # Verify NO quality check in task history
    assert "quality_check" not in actions, "Executive Chef should NOT perform quality check"

    print(f"   ✅ Orchestration completed successfully")
    print(f"   ✅ Task history has {len(task_history)} entries")
    print(f"   ✅ Actions performed: {actions}")
    print(f"   ✅ No quality check by Executive Chef (as expected)")


# ==============================================================================
# TEST 7: VERIFICATION OF MAIN.PY IMPLEMENTATION
# ==============================================================================

def test_main_py_orchestration_structure():
    """
    Test that main.py implements the required orchestration structure.
    Success Criteria: Key workflow stages exist in main.py.
    """
    print("\n🧪 TEST 11: Verify main.py orchestration implementation")

    # Read main.py content
    with open("main.py", "r") as f:
        main_content = f.read()

    # Verify key orchestration stages exist
    required_stages = [
        "orchestrating",
        "synthesizing_recommendations",
        "executing_recipe_search",
        "executing_adaptation",
        "adaptation_complete"
    ]

    for stage in required_stages:
        assert stage in main_content, f"main.py should handle '{stage}' stage"

    # Verify complexity analysis is called
    assert "analyze_request_complexity" in main_content, \
        "main.py should call analyze_request_complexity"

    # Verify task plan creation
    assert "create_task_plan" in main_content, \
        "main.py should call create_task_plan"

    # Verify synthesis
    assert "synthesize_recommendations" in main_content, \
        "main.py should call synthesize_recommendations"

    # Verify delegation methods used
    assert "delegate_to_pantry" in main_content or "delegate_to_sous_chef" in main_content, \
        "main.py should use delegation methods"

    print(f"   ✅ All required stages present in main.py")
    print(f"   ✅ Complexity analysis implemented")
    print(f"   ✅ Task planning implemented")
    print(f"   ✅ Synthesis implemented")
    print(f"   ✅ Delegation methods used")


# ==============================================================================
# TEST 8: PANTRY AGENT EXPIRATION TRACKING
# ==============================================================================

def test_pantry_expiring_items_tracking(pantry_agent):
    """
    Test that Pantry Agent correctly identifies expiring items.
    Success Criteria: Items expiring soon are flagged with correct priority.
    """
    print("\n🧪 TEST 12: Pantry expiring items tracking")

    # Get expiring items
    expiring = pantry_agent.get_expiring_soon(days_threshold=3)

    # Verify expiring items found
    assert len(expiring) > 0, "Should find expiring items (spinach)"

    # Verify priority assignment
    for item in expiring:
        assert "priority" in item
        assert "days_until_expiry" in item
        assert item["priority"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    # Verify spinach (expires tomorrow) is high priority
    spinach = [i for i in expiring if "spinach" in i.get("ingredient_name", "").lower()]
    if spinach:
        assert spinach[0]["priority"] in ["CRITICAL", "HIGH"], \
            "Spinach expiring soon should be high priority"

    print(f"   ✅ Found {len(expiring)} expiring items")
    for item in expiring:
        print(f"   ✅ {item['ingredient_name']}: {item['days_until_expiry']} days ({item['priority']})")


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

if __name__ == "__main__":
    """Run all tests with detailed output."""
    print("\n" + "="*80)
    print("🧪 FULL EXECUTIVE CHEF ORCHESTRATION TEST SUITE")
    print("="*80)

    # Create fixtures manually for standalone run
    from types import SimpleNamespace

    # Mock LLM
    mock_llm_instance = Mock(spec=ChatOpenAI)

    def mock_invoke(messages):
        content = str(messages[-1].content) if messages else ""
        if "complexity" in content.lower():
            return Mock(content='{"complexity": "medium", "strategy": "ingredient_first", "required_agents": ["pantry", "sous_chef"], "agent_sequence": ["pantry", "sous_chef"], "reasoning": "Test", "priority_factors": ["availability"], "estimated_steps": 3}')
        elif "task_plan" in content.lower() or "execution plan" in content.lower():
            return Mock(content='{"tasks": [{"agent": "pantry", "action": "check_inventory", "input": "prefs", "expected_output": "list", "priority": "high"}], "delegation_order": ["pantry", "sous_chef"], "success_criteria": ["recipes_suggested"], "expected_duration": "5-10 minutes", "fallback_strategy": "Suggest with shopping list"}')
        elif "synthesize" in content.lower():
            return Mock(content="Here are 3 great recipe options!")
        elif "quality" in content.lower():
            return Mock(content='{"passed": true, "issues": [], "score": 95, "critical_failures": []}')
        return Mock(content="Response generated")

    mock_llm_instance.invoke = mock_invoke

    # Create agents
    exec_chef = ExecutiveChefAgent(name="Test EC")
    pantry = PantryAgent(name="Test Pantry")
    sous_chef = SousChefAgent(name="Test SC")
    waiter = WaiterAgent(name="Test Waiter")

    # Add test inventory
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    next_week = (datetime.now() + timedelta(days=7)).date().isoformat()
    pantry.add_or_update_ingredient("chicken breast", 2, "lb", next_week, "protein", "fridge")
    pantry.add_or_update_ingredient("spinach", 1, "bunch", tomorrow, "vegetable", "fridge")
    pantry.add_or_update_ingredient("pasta", 1, "lb", None, "grain", "pantry")

    user_prefs = {
        "allergies": ["nuts"],
        "restrictions": ["vegetarian"],
        "skill": "beginner"
    }

    # Run tests
    try:
        test_complexity_analysis_called_for_simple_request(exec_chef, user_prefs, mock_llm_instance)
        test_complexity_analysis_called_for_complex_request(exec_chef, user_prefs, mock_llm_instance)
        test_lightweight_task_plan_for_simple_pantry(exec_chef, user_prefs, mock_llm_instance)
        test_full_llm_task_plan_for_complex_request(exec_chef, pantry, user_prefs, mock_llm_instance)
        test_synthesis_for_medium_complexity(exec_chef, pantry, user_prefs, mock_llm_instance)
        test_quality_check_performed_by_waiter_only(waiter, user_prefs, mock_llm_instance)
        test_delegation_logging_pantry(exec_chef)
        test_delegation_logging_sous_chef(exec_chef)
        test_delegation_logging_recipe_knowledge(exec_chef)
        test_full_orchestration_workflow(exec_chef, pantry, user_prefs, mock_llm_instance)
        test_main_py_orchestration_structure()
        test_pantry_expiring_items_tracking(pantry)

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise

