"""
Leftovr - Refactored LangGraph Workflow
Clean separation: Streamlit = Frontend | LangGraph = Backend Logic
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal, Annotated
import operator

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, add_messages, END
from langgraph.types import Command

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LangSmith tracing configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "leftovr-app")

# Enable LangSmith tracing if configured
if LANGCHAIN_TRACING_V2.lower() == "true" and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    print(f"✅ LangSmith tracing enabled for project: {LANGCHAIN_PROJECT}")
else:
    print("ℹ️  LangSmith tracing disabled (set LANGCHAIN_TRACING_V2=true to enable)")

# Initialize OpenAI client with GPT-4o for optimal performance
# NOTE: JSON mode only used for llm_classifier (structured data extraction)
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,  # Default for general use
    api_key=OPENAI_API_KEY
)

# Specialized LLM instances for different tasks
llm_classifier = ChatOpenAI(
    model="gpt-4o",
    temperature=0.0,  # Deterministic for classification
    api_key=OPENAI_API_KEY,
    model_kwargs={"response_format": {"type": "json_object"}}  # JSON mode for structured outputs
)

llm_creative = ChatOpenAI(
    model="gpt-4o",
    temperature=0.8,  # Higher creativity for recommendations
    api_key=OPENAI_API_KEY
    # NO JSON mode - creative outputs should be natural text
)

from agents.recipe_knowledge_agent import RecipeKnowledgeAgent
from agents.executive_chef_agent import ExecutiveChefAgent
from agents.pantry_agent import PantryAgent
from agents.sous_chef_agent import SousChefAgent


# ============================================
# SIMPLIFIED STATE SCHEMA
# ============================================

class RecipeWorkflowState(MessagesState):
    """
    Simplified state for recipe workflow.
    Only essential fields - no duplicate logic.
    """
    # User context
    user_message: str  # Current user input
    user_preferences: Dict[str, Any]  # {allergies, diet, cuisines, skill_level}

    # Workflow control
    query_type: Optional[Literal["pantry", "recipe", "general"]]  # What type of request
    current_stage: str  # Track workflow stage

    # Pantry data
    pantry_inventory: List[Dict[str, Any]]  # Available ingredients
    expiring_items: List[Dict[str, Any]]  # Ingredients expiring soon

    # Recipe search results
    recipe_results: List[Dict[str, Any]]  # Top-k recipes from search (e.g., 10)
    top_3_recommendations: List[Dict[str, Any]]  # Sous Chef's top 3 picks

    # User selection & final recipe
    user_recipe_selection: Optional[int]  # 1, 2, or 3
    selected_recipe_data: Optional[Dict[str, Any]]  # Full recipe details
    customized_recipe: Optional[Dict[str, Any]]  # Final adapted recipe

    # Response
    response: Optional[str]  # Text response for general queries

    # Coordination log
    coordination_log: Annotated[List[str], operator.add]  # Workflow tracking


# ============================================
# LANGGRAPH WORKFLOW - SIMPLIFIED
# ============================================

class LeftovrWorkflow:
    """
    Clean LangGraph workflow with specialized nodes.
    Streamlit handles UI, this handles all logic.
    """

    def __init__(self):
        # Initialize agents
        self.exec_chef = ExecutiveChefAgent(name="Maison D'Être")
        self.pantry = PantryAgent(name="Pantry Manager")

        # Initialize Recipe Knowledge Agent
        self.recipe_agent = RecipeKnowledgeAgent(data_dir='data')
        try:
            self.recipe_agent.load_metadata()
            self.recipe_agent.load_ingredient_index()
            self.recipe_agent.setup_qdrant()
            print("✅ Recipe Knowledge Agent initialized with hybrid search")
        except FileNotFoundError as e:
            print(f"⚠️  Warning: {e}")
            print("   Run the ingestion script first: python scripts/ingest_recipes_qdrant.py")
            self.recipe_agent = None

        # Wire pantry to recipe agent
        if self.recipe_agent:
            self.recipe_agent.set_pantry_agent(self.pantry)

        self.sous_chef = SousChefAgent(name="Sous Chef", recipe_knowledge_agent=self.recipe_agent)

        # Build workflow graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the simplified LangGraph workflow"""
        workflow = StateGraph(RecipeWorkflowState)

        # Add nodes
        workflow.add_node("orchestrator", self._orchestrator_node)
        workflow.add_node("pantry", self._pantry_node)
        workflow.add_node("recipe_search", self._recipe_search_node)
        workflow.add_node("recommendation", self._recommendation_node)
        workflow.add_node("customization", self._customization_node)
        workflow.add_node("general_response", self._general_response_node)

        # Set entry point
        workflow.set_entry_point("orchestrator")

        # Conditional routing from orchestrator
        workflow.add_conditional_edges(
            "orchestrator",
            self._route_from_orchestrator,
            {
                "pantry": "pantry",
                "recipe": "recipe_search",
                "general": "general_response",
                "selection": "customization"  # User selected a recipe
            }
        )

        # Simple edges
        workflow.add_edge("pantry", END)
        workflow.add_edge("recipe_search", "recommendation")
        workflow.add_edge("recommendation", END)
        workflow.add_edge("customization", END)
        workflow.add_edge("general_response", END)

        return workflow.compile()

    # ============================================
    # NODE 1: ORCHESTRATOR (Executive Chef)
    # ============================================

    def _orchestrator_node(self, state: RecipeWorkflowState) -> Dict[str, Any]:
        """
        Single entry point - classify query and decide routing.
        This is the Executive Chef making decisions.
        """
        print("\n🎯 [ORCHESTRATOR] Analyzing user request...")

        user_msg = state.get("user_message", "")
        messages = state.get("messages", [])

        # Build message list for classification
        if user_msg:
            messages = messages + [{"role": "user", "content": user_msg}]

        # Classify query type using classifier LLM (temperature=0 for deterministic results)
        query_classification = self.exec_chef.classify_query(llm_classifier, messages)
        query_type = query_classification.get("query_type", "general")

        # Extract user preferences for recipe and general queries (but NOT pantry)
        # For pantry queries, the LLM tends to misclassify ingredients as allergies
        current_prefs = state.get("user_preferences", {})
        if query_type in ["recipe", "general"]:
            # Extract preferences from conversation using classifier LLM
            preferences = self.exec_chef.extract_preferences(llm_classifier, messages)

            # Only merge if actual preferences were found (not empty)
            has_prefs = any([
                preferences.get("allergies"),
                preferences.get("restrictions"),
                preferences.get("cuisines"),
                preferences.get("diet"),
                preferences.get("skill")
            ])

            if has_prefs:
                # Merge lists (allergies, restrictions, cuisines)
                updated_prefs = {**current_prefs}
                for key in ["allergies", "restrictions", "cuisines"]:
                    existing = list(current_prefs.get(key, []))
                    new_items = list(preferences.get(key, []))
                    if new_items:
                        existing.extend(new_items)
                        updated_prefs[key] = list(set(existing))  # Remove duplicates

                # Override single values (diet, skill)
                if preferences.get("diet"):
                    updated_prefs["diet"] = preferences["diet"]
                if preferences.get("skill"):
                    updated_prefs["skill"] = preferences["skill"]
            else:
                # No preferences found, keep existing
                updated_prefs = current_prefs
        else:
            # For pantry queries, keep existing preferences unchanged
            updated_prefs = current_prefs

        # Check if user is selecting a recipe (1, 2, or 3)
        selection_keywords = ["i'll try", "i'll take", "give me recipe", "option", "choice"]
        if any(keyword in user_msg.lower() for keyword in selection_keywords):
            # Try to extract recipe number
            for i in [1, 2, 3]:
                if str(i) in user_msg or ["one", "two", "three"][i-1] in user_msg.lower():
                    print(f"✅ [ORCHESTRATOR] User selected recipe {i}")
                    return {
                        "query_type": "recipe",
                        "user_preferences": updated_prefs,
                        "user_recipe_selection": i,
                        "current_stage": "customization",
                        "coordination_log": [f"User selected recipe #{i}"]
                    }

        print(f"📋 [ORCHESTRATOR] Query type: {query_type}")
        print(f"👤 [ORCHESTRATOR] Preferences: {updated_prefs}")

        return {
            "query_type": query_type,
            "user_preferences": updated_prefs,
            "current_stage": f"routing_to_{query_type}",
            "coordination_log": [f"Orchestrator classified as: {query_type}"]
        }

    def _route_from_orchestrator(self, state: RecipeWorkflowState) -> str:
        """Decide which node to route to based on query type"""
        query_type = state.get("query_type", "general")

        # If user selected a recipe, go to customization
        if state.get("user_recipe_selection"):
            return "selection"

        # Route based on query type
        routing = {
            "pantry": "pantry",
            "ingredient": "pantry",
            "recipe": "recipe",
            "general": "general"
        }

        return routing.get(query_type, "general")

    # ============================================
    # NODE 2: PANTRY (Pantry Agent)
    # ============================================

    def _pantry_node(self, state: RecipeWorkflowState) -> Dict[str, Any]:
        """
        Handle pantry operations: add/update/remove ingredients.
        """
        print("\n🥬 [PANTRY] Processing inventory operation...")

        user_msg = state.get("user_message", "")

        # Use Executive Chef to extract ingredients using classifier LLM
        extracted = self.exec_chef.extract_ingredients(llm_classifier, user_msg)
        ingredients = extracted.get("ingredients", [])

        # Add each ingredient to pantry using Pantry Agent
        added_items = []
        for ing in ingredients:
            name = ing.get("name", "")
            quantity = ing.get("quantity", 1)
            unit = ing.get("unit", "pieces")

            if name:
                self.pantry.add_or_update_ingredient(
                    ingredient_name=name,
                    quantity=quantity,
                    unit=unit
                )
                added_items.append(f"{quantity} {unit} {name}")

        # Get updated inventory
        inventory = self.pantry.get_inventory()
        expiring = self.pantry.get_expiring_soon(days_threshold=3)

        # Create response
        response = self._format_pantry_response(added_items, inventory, expiring)

        print(f"✅ [PANTRY] Updated inventory: {len(inventory)} items")

        return {
            "pantry_inventory": inventory,
            "expiring_items": expiring,
            "response": response,
            "current_stage": "pantry_complete",
            "coordination_log": [f"Pantry updated: added {len(added_items)} items"]
        }

    def _format_pantry_response(self, added_items: List[str], inventory: List, expiring: List) -> str:
        """Format pantry operation result for user"""
        response = ""

        if added_items:
            response = f"✅ I've added {', '.join(added_items)} to your pantry.\n\n"
        else:
            response = "✅ I've updated your pantry.\n\n"

        response += f"📦 **Your pantry now has {len(inventory)} items.**"

        if expiring:
            response += f"\n⚠️  {len(expiring)} items expiring soon: "
            response += ", ".join([item.get("ingredient_name", item.get("name", "")) for item in expiring[:3]])

        return response

    # ============================================
    # NODE 3: RECIPE SEARCH (Recipe Knowledge Agent)
    # ============================================

    def _recipe_search_node(self, state: RecipeWorkflowState) -> Dict[str, Any]:
        """
        Search for recipes using hybrid search.
        Returns top-k results (e.g., 10 recipes).
        """
        print("\n🔍 [RECIPE SEARCH] Searching for recipes...")

        if not self.recipe_agent:
            return {
                "response": "⚠️  Recipe search is not available. Please run the ingestion script first.",
                "current_stage": "error",
                "coordination_log": ["Recipe search unavailable - no data loaded"]
            }

        user_msg = state.get("user_message", "")
        preferences = state.get("user_preferences", {})
        inventory = state.get("pantry_inventory", [])

        # Extract pantry items as ingredient names
        pantry_items = [item.get("ingredient_name", item.get("name", "")) for item in inventory] if inventory else None

        # Perform hybrid query (keyword + semantic)
        try:
            # hybrid_query returns list of (recipe_metadata, score, num_used, missing)
            results = self.recipe_agent.hybrid_query(
                pantry_items=pantry_items,
                query_text=user_msg,
                top_k=10,
                allow_missing=2,
                use_semantic=True
            )

            # Extract recipe metadata from results
            recipe_results = [recipe_meta for recipe_meta, score, num_used, missing in results]

            print(f"✅ [RECIPE SEARCH] Found {len(recipe_results)} recipes")

            return {
                "recipe_results": recipe_results,
                "current_stage": "recipe_search_complete",
                "coordination_log": [f"Found {len(recipe_results)} recipes via hybrid search"]
            }

        except Exception as e:
            print(f"❌ [RECIPE SEARCH] Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": f"❌ Sorry, I encountered an error searching recipes: {str(e)}",
                "current_stage": "error",
                "coordination_log": [f"Recipe search error: {str(e)}"]
            }

    # ============================================
    # NODE 4: RECOMMENDATION (Sous Chef - Rank)
    # ============================================

    def _recommendation_node(self, state: RecipeWorkflowState) -> Dict[str, Any]:
        """
        Sous Chef analyzes top-k recipes and selects best 3.
        Considers: ingredient match, expiring items, user skill level.
        """
        print("\n👨‍🍳 [RECOMMENDATION] Sous Chef selecting top 3...")

        recipe_results = state.get("recipe_results", [])
        preferences = state.get("user_preferences", {})
        inventory = state.get("pantry_inventory", [])
        expiring = state.get("expiring_items", [])

        if not recipe_results:
            return {
                "response": "😕 I couldn't find any recipes matching your criteria.",
                "current_stage": "no_results",
                "coordination_log": ["No recipes found to recommend"]
            }

        # Use Sous Chef's existing generate_recommendations method with creative LLM
        pantry_summary = {
            "inventory": inventory,
            "total_ingredients": len(inventory)
        }

        top_3 = self.sous_chef.generate_recommendations(
            llm=llm_creative,  # Use creative LLM for recommendations
            pantry_summary=pantry_summary,
            user_preferences=preferences,
            expiring_items=expiring,
            recipe_results=recipe_results  # Pass the search results
        )

        # Format response
        response = self._format_recommendations(top_3, expiring)

        print(f"✅ [RECOMMENDATION] Selected top 3 recipes")

        return {
            "top_3_recommendations": top_3,
            "response": response,
            "current_stage": "presenting_options",
            "coordination_log": [f"Sous Chef recommended {len(top_3)} recipes"]
        }

    def _format_recommendations(self, top_3: List[Dict], expiring: List) -> str:
        """Format top 3 recommendations for user"""
        response = "🍽️ **Here are my top 3 recipe recommendations:**\n\n"

        for i, recipe in enumerate(top_3, 1):
            response += f"**{i}. {recipe.get('title', 'Unknown Recipe')}**\n"

            # Show ingredient count
            ingredients = recipe.get('ner', []) or recipe.get('ingredients', [])
            if ingredients:
                response += f"   🥘 {len(ingredients)} ingredients\n"

            # Show timing and servings
            ready_time = recipe.get('readyInMinutes', 'N/A')
            servings = recipe.get('servings', 'N/A')
            if ready_time != 'N/A' or servings != 'N/A':
                response += f"   ⏱️ {ready_time} min | 👥 {servings} servings\n"

            # Show match percentage if available
            match_pct = recipe.get("match_percentage", recipe.get("score", 0))
            if match_pct:
                response += f"   🎯 {match_pct}% ingredient match\n"

            # Show recipe link
            link = recipe.get('link', '')
            if link:
                # Make sure link has protocol
                if not link.startswith('http'):
                    link = f"https://{link}"
                response += f"   🔗 [View Recipe]({link})\n"

            # Show why recommended
            reason = recipe.get("recommendation_reason", recipe.get("reasoning", "Great recipe!"))
            response += f"   💡 {reason}\n\n"

        if expiring:
            expiring_names = [item.get('ingredient_name') or item.get('name', '') for item in expiring[:3]]
            response += f"\n⚠️  Using expiring items: {', '.join(expiring_names)}"

        response += "\n\n✨ **Which recipe would you like to try?** (Reply with 1, 2, or 3)"

        return response

    # ============================================
    # NODE 6: GENERAL RESPONSE (Executive Chef)
    # ============================================

    def _customization_node(self, state: RecipeWorkflowState) -> Dict[str, Any]:
        """
        Sous Chef adapts selected recipe to user's pantry and preferences.
        Handles substitutions, adjustments, and formatting.
        """
        print("\n🎨 [CUSTOMIZATION] Adapting recipe...")

        selection = state.get("user_recipe_selection")
        top_3 = state.get("top_3_recommendations", [])
        inventory = state.get("pantry_inventory", [])
        preferences = state.get("user_preferences", {})

        if not selection or not top_3:
            return {
                "response": "😕 I need you to select a recipe first (1, 2, or 3).",
                "current_stage": "awaiting_selection",
                "coordination_log": ["No recipe selection provided"]
            }

        # Validate selection
        if selection < 1 or selection > len(top_3):
            return {
                "response": f"Please select a valid option (1-{len(top_3)}).",
                "current_stage": "awaiting_selection",
                "coordination_log": ["Invalid recipe selection"]
            }

        # Get selected recipe
        selected = top_3[selection - 1]

        # Use Sous Chef's existing adapt_recipe method with creative LLM
        customized = self.sous_chef.adapt_recipe(
            llm=llm_creative,  # Use creative LLM for recipe adaptation
            recipe=selected,
            user_preferences=preferences,
            pantry_inventory=inventory
        )

        # Format final recipe using existing method
        formatted = self.sous_chef.format_recipe_for_user(customized, preferences)

        print(f"✅ [CUSTOMIZATION] Recipe customized: {selected.get('title', 'Unknown')}")

        return {
            "selected_recipe_data": selected,
            "customized_recipe": customized,
            "response": formatted,
            "current_stage": "final_recipe",
            "coordination_log": [f"Customized recipe #{selection}: {selected.get('title', 'Unknown')}"]
        }

    # ============================================
    # NODE 6: GENERAL RESPONSE (Executive Chef)
    # ============================================

    def _general_response_node(self, state: RecipeWorkflowState) -> Dict[str, Any]:
        """
        Handle general conversation - cooking questions, greetings, etc.
        No agent calls needed.
        """
        print("\n💬 [GENERAL] Handling general query...")

        user_msg = state.get("user_message", "")

        # Use Executive Chef for general responses
        response = self.exec_chef.respond_as_waiter(llm, user_msg)

        print(f"✅ [GENERAL] Responded to general query")

        return {
            "response": response,
            "current_stage": "general_complete",
            "coordination_log": ["Handled general query"]
        }

    # ============================================
    # PUBLIC INTERFACE
    # ============================================

    async def ainvoke(self, input_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async invoke the workflow.
        Called by Streamlit frontend.
        """
        # Ensure required fields
        if "user_message" not in input_state:
            raise ValueError("user_message is required")

        # Initialize state if needed
        if "coordination_log" not in input_state:
            input_state["coordination_log"] = []
        if "current_stage" not in input_state:
            input_state["current_stage"] = "initial"

        # Run workflow
        result = await self.graph.ainvoke(input_state)

        return result

    def invoke(self, input_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync invoke the workflow.
        """
        # Ensure required fields
        if "user_message" not in input_state:
            raise ValueError("user_message is required")

        # Initialize state if needed
        if "coordination_log" not in input_state:
            input_state["coordination_log"] = []
        if "current_stage" not in input_state:
            input_state["current_stage"] = "initial"

        # Run workflow
        result = self.graph.invoke(input_state)

        return result


# ============================================
# INITIALIZATION
# ============================================

def create_workflow() -> LeftovrWorkflow:
    """Create and return the workflow instance"""
    return LeftovrWorkflow()


# For testing
if __name__ == "__main__":
    print("🚀 Initializing Leftovr Workflow...")
    workflow = create_workflow()

    # Test 1: Pantry addition
    print("\n" + "="*60)
    print("TEST 1: Add pantry items")
    print("="*60)
    result1 = workflow.invoke({
        "user_message": "I have 2 chicken breasts, tomatoes, and pasta",
        "user_preferences": {},
        "pantry_inventory": []
    })
    print(f"\n📤 Response:\n{result1.get('response', 'No response')}")

    # Test 2: Recipe search
    print("\n" + "="*60)
    print("TEST 2: Search recipes")
    print("="*60)
    result2 = workflow.invoke({
        "user_message": "What can I make? I'm vegetarian",
        "user_preferences": {"dietary_restrictions": ["vegetarian"]},
        "pantry_inventory": result1.get("pantry_inventory", [])
    })
    print(f"\n📤 Response:\n{result2.get('response', 'No response')}")
