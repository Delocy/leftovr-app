#!/usr/bin/env python3
"""
Complete Test Suite for Leftovr App
Tests: Backend API, Agent Workflow, and Integration
"""

import os
import sys
import json
import requests
from datetime import datetime

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def print_header(msg):
    print(f"\n{'='*70}")
    print(f"{BLUE}{msg}{RESET}")
    print(f"{'='*70}\n")


# =============================================================================
# TEST 1: Environment Variables
# =============================================================================

def test_environment():
    """Check if required environment variables are set"""
    print_header("TEST 1: Environment Variables")
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API for LLM',
        'PINECONE_API_KEY': 'Pinecone for recipe search',
    }
    
    optional_vars = {
        'PINECONE_INDEX_NAME': 'Pinecone index name',
        'LANGCHAIN_API_KEY': 'LangSmith tracing',
    }
    
    all_good = True
    
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            print_success(f"{var} set ({description})")
        else:
            print_error(f"{var} NOT SET ({description})")
            all_good = False
    
    print()
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            print_info(f"{var} set ({description})")
        else:
            print_warning(f"{var} not set ({description})")
    
    return all_good


# =============================================================================
# TEST 2: Backend Health Check
# =============================================================================

def test_backend_health(base_url='http://localhost:8000'):
    """Test if backend server is running"""
    print_header("TEST 2: Backend Health Check")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Backend server is running")
            print(f"   Status: {data.get('status')}")
            print(f"   Timestamp: {data.get('timestamp')}")
            
            agents = data.get('agents', {})
            print(f"\n   Agent Status:")
            for agent, status in agents.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {agent}: {status}")
            
            return True
        else:
            print_error(f"Backend returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Is it running?")
        print_info("Start backend with: python api/server.py")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


# =============================================================================
# TEST 3: Pantry Operations
# =============================================================================

def test_pantry_operations(base_url='http://localhost:8000'):
    """Test pantry CRUD operations"""
    print_header("TEST 3: Pantry Operations (CRUD)")
    
    # Test 1: Get inventory
    print_info("Getting pantry inventory...")
    try:
        response = requests.get(f"{base_url}/pantry/inventory", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved inventory: {data.get('total_items', 0)} items")
            inventory = data.get('inventory', [])
            if inventory:
                print(f"   Sample items: {[item.get('ingredient_name', item.get('name')) for item in inventory[:3]]}")
        else:
            print_error(f"Failed to get inventory: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error getting inventory: {e}")
        return False
    
    # Test 2: Add item
    print_info("Adding test item to pantry...")
    test_item = {
        "ingredient_name": "test_chicken",
        "quantity": 2.0,
        "unit": "lbs",
        "expiration_date": "2025-12-20"
    }
    
    try:
        response = requests.post(f"{base_url}/pantry/add", json=test_item, timeout=5)
        if response.status_code == 200:
            print_success("Successfully added test item")
        else:
            print_error(f"Failed to add item: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error adding item: {e}")
        return False
    
    # Test 3: Delete item (cleanup)
    print_info("Cleaning up test item...")
    try:
        response = requests.delete(f"{base_url}/pantry/delete/test_chicken", timeout=5)
        if response.status_code == 200:
            print_success("Successfully deleted test item")
        else:
            print_warning(f"Could not delete test item: {response.status_code}")
    except Exception as e:
        print_warning(f"Error deleting item: {e}")
    
    return True


# =============================================================================
# TEST 4: Chat Endpoint (Agent Workflow)
# =============================================================================

def test_chat_workflow(base_url='http://localhost:8000'):
    """Test the chat endpoint with agent workflow"""
    print_header("TEST 4: Chat Endpoint (Agent Workflow)")
    
    test_cases = [
        {
            "name": "General greeting",
            "message": "Hello! What can you help me with?",
            "expected_type": "general"
        },
        {
            "name": "Pantry query",
            "message": "I have chicken and rice in my pantry",
            "expected_type": "pantry"
        },
        {
            "name": "Recipe request",
            "message": "Show me some pasta recipes",
            "expected_type": "recipe"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print_info(f"Test {i}: {test['name']}")
        print(f"   Message: \"{test['message']}\"")
        
        payload = {
            "user_message": test['message'],
            "user_preferences": {},
            "pantry_inventory": []
        }
        
        try:
            response = requests.post(f"{base_url}/chat", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                current_stage = data.get('current_stage', 'unknown')
                
                print_success(f"Got response (stage: {current_stage})")
                print(f"   Response preview: {response_text[:150]}...")
                
                # Check for recommendations
                if data.get('top_3_recommendations'):
                    recipes = data['top_3_recommendations']
                    print(f"   📋 Recommendations: {len(recipes)} recipes")
                    for idx, recipe in enumerate(recipes[:2], 1):
                        print(f"      {idx}. {recipe.get('title', 'Unknown')}")
                
                # Check for pantry updates
                if data.get('pantry_inventory'):
                    items = data['pantry_inventory']
                    print(f"   🥬 Pantry: {len(items)} items")
                
                print()
            else:
                print_error(f"Chat request failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            print_error("Request timed out (agent workflow taking too long)")
            return False
        except Exception as e:
            print_error(f"Error: {e}")
            return False
    
    return True


# =============================================================================
# TEST 5: Recipe Search
# =============================================================================

def test_recipe_search(base_url='http://localhost:8000'):
    """Test recipe search endpoint"""
    print_header("TEST 5: Recipe Search (Pinecone)")
    
    print_info("Searching for 'chicken pasta' recipes...")
    
    payload = {
        "query": "chicken pasta recipes",
        "preferences": {},
        "top_k": 5
    }
    
    try:
        response = requests.post(f"{base_url}/recipes/search", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            recipes = data.get('recipes', [])
            total = data.get('total_results', 0)
            
            print_success(f"Found {total} recipes")
            
            if recipes:
                print(f"\n   Top Results:")
                for idx, recipe in enumerate(recipes[:3], 1):
                    title = recipe.get('title', 'Unknown')
                    match_pct = recipe.get('match_percentage', 0)
                    print(f"   {idx}. {title} (Match: {match_pct}%)")
                
                return True
            else:
                print_warning("No recipes found - Pinecone index might be empty")
                print_info("Run: python scripts/ingest_recipes_pinecone.py --input assets/full_dataset.csv --outdir data")
                return False
        else:
            print_error(f"Recipe search failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False


# =============================================================================
# TEST 6: Agent Workflow Direct Test
# =============================================================================

def test_agent_workflow_direct():
    """Test the LangGraph workflow directly (without API)"""
    print_header("TEST 6: Agent Workflow (Direct)")
    
    print_info("Loading workflow...")
    try:
        # Add parent directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from main import LeftovrWorkflow
        
        print_success("Workflow loaded successfully")
        
        print_info("Initializing workflow...")
        workflow = LeftovrWorkflow()
        print_success("Workflow initialized")
        
        print_info("Testing simple query...")
        result = workflow.invoke({
            "user_message": "Hello, what can you help me with?",
            "user_preferences": {},
            "pantry_inventory": []
        })
        
        response = result.get('response', '')
        if response:
            print_success("Workflow executed successfully")
            print(f"   Response: {response[:150]}...")
            return True
        else:
            print_error("No response from workflow")
            return False
            
    except ImportError as e:
        print_error(f"Cannot import workflow: {e}")
        print_info("This test requires the backend to be properly set up")
        return False
    except Exception as e:
        print_error(f"Error testing workflow: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def main():
    """Run all tests"""
    print(f"\n{'='*70}")
    print(f"{BLUE}🧪 LEFTOVR APP - COMPLETE TEST SUITE{RESET}")
    print(f"{'='*70}\n")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Test 1: Environment
    results['environment'] = test_environment()
    
    # Test 2: Backend Health
    results['backend_health'] = test_backend_health()
    
    if not results['backend_health']:
        print_warning("\nBackend not running. Remaining tests require backend.")
        print_info("Start backend: python api/server.py")
        print_info("Start MCP server: python mcp/server.py")
    else:
        # Test 3: Pantry
        results['pantry'] = test_pantry_operations()
        
        # Test 4: Chat
        results['chat'] = test_chat_workflow()
        
        # Test 5: Recipe Search
        results['recipe_search'] = test_recipe_search()
    
    # Test 6: Direct workflow (optional)
    if input("\n\nRun direct workflow test? (y/N): ").strip().lower() == 'y':
        results['workflow_direct'] = test_agent_workflow_direct()
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = f"{GREEN}✅ PASSED{RESET}" if passed_test else f"{RED}❌ FAILED{RESET}"
        print(f"{test_name:20s} : {status}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 All tests passed! Your system is working correctly.{RESET}\n")
        return 0
    else:
        print(f"\n{YELLOW}⚠️  Some tests failed. Check the output above for details.{RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
