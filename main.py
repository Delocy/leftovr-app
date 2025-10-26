import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Literal, Annotated
import json
import operator
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState
from langgraph.types import Command

from langgraph.cache.memory import InMemoryCache
import asyncio
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")

# Initialize OpenAI client
llm = ChatOpenAI(
    model="gpt-5-nano",
    temperature=0.7,
    api_key=OPENAI_API_KEY
)

from agents.waiter_agent import WaiterAgent
from agents.recipe_knowledge_agent import RecipeKnowledgeAgent
from agents.executive_chef_agent import ExecutiveChefAgent
from agents.pantry_agent import PantryAgent
from agents.sous_chef_agent import SousChefAgent


# Modern collaborative state
class ModernCollaborativeState(MessagesState):
    user_preferences: Dict[str, Any]
    waiter_satisfied: bool
    handoff_packet: Dict[str, Any]
    query_type: Optional[Literal["ingredient", "recipe"]]
    latest_user_message: Optional[str]
    user_ingredients: List[str]  # pantry ingredients from user
    recipe_results: List[Dict[str, Any]]  # retrieved recipes
    final_recommendation: Optional[str]
    quality_passed: bool
    quality_issues: List[str]
    # Use Annotated with operator.add to allow multiple updates per step
    coordination_log: Annotated[List[str], operator.add]

    # Pantry-related fields
    pantry_inventory: List[Dict[str, Any]]
    expiring_items: List[Dict[str, Any]]
    pantry_summary: Dict[str, Any]
    recipe_feasibility: Optional[Dict[str, Any]]
    
    # Sous chef states
    sous_chef_recommendations: List[Dict[str, Any]]
    user_recipe_selection: Optional[int]  # User's choice (1, 2, or 3)
    selected_recipe_data: Optional[Dict[str, Any]]  # Full selected recipe
    adapted_recipe: Optional[Dict[str, Any]]  # Adapted recipe
    formatted_recipe: Optional[str]  # Final formatted recipe for user

class ModernCollaborativeSystem:
    """collaborative system with enhanced orchestration"""

    def __init__(self):
        self.graph = self._create_modern_collaborative_graph()
        self.waiter = WaiterAgent(name="Maison d'Être")
        
        # Initialize Recipe Knowledge Agent
        self.recipe_agent = RecipeKnowledgeAgent(data_dir='data')
        try:
            self.recipe_agent.load_metadata()
            self.recipe_agent.load_ingredient_index()
            self.recipe_agent.setup_qdrant()  # Optional: for semantic search
            print("✅ Recipe Knowledge Agent initialized successfully")
        except FileNotFoundError as e:
            print(f"⚠️  Warning: {e}")
            print("   Run the ingestion script first: python scripts/ingest_recipes_qdrant.py")
            self.recipe_agent = None
        self.exec_chef = ExecutiveChefAgent(name="Executive Chef")
        self.pantry = PantryAgent(name="Pantry Manager")
        self.sous_chef = SousChefAgent(name="Sous Chef", recipe_knowledge_agent=self.recipe_agent)

    def _create_modern_collaborative_graph(self) -> StateGraph:
        """Create collaborative workflow with Command API"""
        workflow = StateGraph(ModernCollaborativeState)

        def waiter_agent_collect(state) -> Command[Literal["waiter_collect_info", "pantry_check", "return_to_user"]]:
            """
            Waiter agent logic:
            - Classify every new user message
            - Maintain full messages history for context-aware classification
            - Only require full preferences for 'recipe' queries
            - 'pantry' and 'general' skip preference requirements
            """
            log = state.get("coordination_log", [])
            current_prefs = state.get("user_preferences", {}) or {}
            messages = state.get("messages", [])  # full chat history

            # Helper: check if preferences contain any meaningful info
            def _is_prefs_empty(prefs: dict) -> bool:
                return not any(prefs.get(k) for k in ["allergies", "restrictions"])

            latest = state.get("latest_user_message")

            # --- Update messages history ---
            if latest:
                messages.append({"role": "user", "content": latest})
            else:
                # No latest message, trigger initial greeting
                intro = self.waiter.run(llm, context="query_type")
                print(f"\nWaiter: {intro}")
                messages.append({"role": "assistant", "content": intro})
                return Command(
                    update={
                        "coordination_log": log,
                        "user_preferences": current_prefs,
                        "waiter_satisfied": False,
                        "latest_user_message": None,
                        "query_type": None,
                        "messages": messages,
                    },
                    goto="return_to_user"
                )

            # --- Classify query using full chat history ---
            # classification = self.waiter.classify_query(llm, messages)
            # query_type = classification.get("query_type")
            # state["query_type"] = query_type
            prev_query_type = state.get("query_type")
            if prev_query_type == "recipe" and _is_prefs_empty(current_prefs):
                query_type = "recipe"
            else:
                classification = self.waiter.classify_query(llm, messages)
                query_type = classification.get("query_type", "general")
            # --- BEHAVIOR BRANCHES ---

            # 1) Pantry or general queries
            if query_type in {"pantry", "general"}:
                if query_type == "pantry":
                    suff_info = self.waiter.pantry_info_sufficient(llm, messages).get("sufficient_info")
                    if suff_info:
                        return Command(
                            update={
                                "coordination_log": log,
                                "user_preferences": current_prefs,
                                "waiter_satisfied": True,
                                "query_type": query_type,
                                "messages": messages,
                            },
                            goto="pantry_check"
                        )
                    else:
                        prompt = (
                            "Could you clarify what pantry action you'd like to take? "
                            "For example, add, update, remove, or view items."
                        )
                        print(f"\nWaiter: {prompt}")
                        messages.append({"role": "assistant", "content": prompt})
                        return Command(
                            update={
                                "coordination_log": log,
                                "user_preferences": current_prefs,
                                "waiter_satisfied": False,
                                "query_type": query_type,
                                "messages": messages,
                            },
                            goto="return_to_user"
                        )
                else:  # general
                    user_text = latest  # latest user message string
                    res = self.waiter.respond(llm, user_text)
                    print(res)
                    messages.append({"role": "assistant", "content": res})
                    return Command(
                        update={
                            "coordination_log": log,
                            "user_preferences": current_prefs,
                            "waiter_satisfied": False,
                            "query_type": query_type,
                            "messages": messages,
                        },
                        goto="return_to_user"
                    )

            # 2) Recipe queries
            if query_type == "recipe":
                extracted = self.waiter.extract_preferences(llm, messages)
                # Merge extracted preferences
                def merge_list(key):
                    existing = list(current_prefs.get(key, []) or [])
                    incoming = list(extracted.get(key, []) or [])
                    return existing + [x for x in incoming if x not in existing]

                current_prefs = {
                    "allergies": merge_list("allergies"),
                    "restrictions": merge_list("restrictions"),
                }

                if _is_prefs_empty(current_prefs):
                    missing_fields = [k for k in ["allergies", "restrictions"] if not current_prefs.get(k)]

                    missing_prompt = (
                        "I need some more information to suggest recipes.\n"
                        f"Please provide your {', '.join(missing_fields)}."
                    )
                    print(f"\nWaiter: {missing_prompt}")
                    
                    messages.append({"role": "assistant", "content": missing_prompt})
                    return Command(
                        update={
                            "coordination_log": log,
                            "user_preferences": current_prefs,
                            "waiter_satisfied": False,
                            "latest_user_message": latest,
                            "query_type": query_type,
                            "messages": messages,
                        },
                        goto="return_to_user"
                    )

                # Check for missing essential fields
                required = ["allergies", "restrictions"]
                missing = [k for k in required if not current_prefs.get(k)]
                if missing:
                    insufficient_prompt = f"Waiter: missing fields for recipe query -> {', '.join(missing)}"
                    print(f"\nWaiter: {missing_prompt}")
                    messages.append({"role": "assistant", "content": insufficient_prompt})
                    return Command(
                        update={
                            "coordination_log": log,
                            "user_preferences": current_prefs,
                            "waiter_satisfied": False,
                            "latest_user_message": latest,
                            "query_type": query_type,
                            "messages": messages,
                        },
                        goto="return_to_user"
                    )

                # All required recipe preferences present -> handoff
                log.append("Waiter: recipe preferences complete; handing off")

            prefs = current_prefs
            required_scalar = ["diet", "skill"]
            optional_lists = ["allergies", "restrictions", "cuisines"]
            satisfied = all(bool(prefs.get(k)) for k in required_scalar)

            for field in optional_lists:
                if prefs.get(field) is None:
                    prefs[field] = []

            if satisfied:
                log.append("Waiter: preferences complete, checking pantry inventory")
                print("Waiter: preferences complete, checking pantry inventory")
                return Command(
                    update={
                        "coordination_log": log,
                        "user_preferences": current_prefs,
                        "waiter_satisfied": True,
                        "handoff_packet": {
                            "user_preferences": current_prefs,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "notes": "Collected by waiter; ready for pantry check."
                        },
                        "query_type": query_type,
                        "messages": messages,
                    },
                    goto="pantry_check"
                )

            # Safety fallback
            return Command(
                update={
                    "coordination_log": log,
                    "user_preferences": current_prefs,
                    "waiter_satisfied": True,
                    "query_type": query_type,
                    "messages": messages,
                },
                goto="return_to_user"
            )

        def pantry_check(state) -> Command[Literal["executive_chef_review"]]:
            """Pantry Agent checks inventory and communicates with Executive Chef."""
            log = state.get("coordination_log", [])

            log.append("Pantry Agent: Checking inventory status")
            print("\n🗄️  Pantry Agent: Checking inventory...")

            # Get pantry data
            summary = self.pantry.get_pantry_summary()
            expiring = self.pantry.get_expiring_soon(days_threshold=3)
            inventory = self.pantry.get_inventory()

            print(f"   📊 {summary['total_ingredients']} ingredients in stock")
            print(f"   ⚠️  {len(expiring)} items expiring soon")

            # Alert about critical items
            if expiring:
                critical = [x for x in expiring if x.get('priority') == 'CRITICAL']
                high = [x for x in expiring if x.get('priority') == 'HIGH']

                if critical:
                    print(f"   🚨 {len(critical)} CRITICAL items (use immediately):")
                    for item in critical[:3]:
                        print(f"      • {item['ingredient_name']}: {item['quantity']} {item['unit']} "
                              f"(expires in {item['days_until_expiry']} day(s))")

                if high:
                    print(f"   ⚠️  {len(high)} HIGH priority items (use soon):")
                    for item in high[:3]:
                        print(f"      • {item['ingredient_name']}: {item['quantity']} {item['unit']} "
                              f"(expires in {item['days_until_expiry']} day(s))")

            # Generate proactive alerts for Executive Chef
            alerts = self.pantry.generate_expiration_alerts()
            if alerts:
                log.append(f"Pantry Agent: Generated {len(alerts)} expiration alerts for Executive Chef")
                print(f"   📢 Sent {len(alerts)} alert(s) to Executive Chef")

            log.append(f"Pantry Agent: Inventory check complete - {summary['total_ingredients']} items, {len(expiring)} expiring")

            return Command(
                update={
                    "coordination_log": log,
                    "pantry_inventory": inventory,
                    "expiring_items": expiring,
                    "pantry_summary": summary
                },
                goto="executive_chef_review"
            )

        def exec_chef_review(state) -> Command[Literal["recipe_knowledge_retrieve"]]:
            """Executive Chef reviews preferences and pantry data, coordinates with Pantry Agent."""
            log = state.get("coordination_log", [])
            handoff = state.get("handoff_packet", {})
            user_prefs = handoff.get("user_preferences", {})

            # Get pantry data
            expiring = state.get("expiring_items", [])
            pantry_summary = state.get("pantry_summary", {})

            if handoff:
                log.append("Executive Chef: Analyzing request with pantry data")
                print(f"\n👨‍🍳 Executive Chef: Orchestrating recipe plan...")
                print(f"   User preferences received: {user_prefs.get('diet', 'omnivore')}, "
                      f"{len(user_prefs.get('allergies', []))} allergies")

                # Acknowledge pantry status
                if pantry_summary:
                    print(f"   Pantry status: {pantry_summary.get('total_ingredients', 0)} ingredients available")

                # Prioritize expiring ingredients
                if expiring:
                    priority_items = [x['ingredient_name'] for x in expiring[:5]]
                    log.append(f"Executive Chef: Prioritizing expiring items: {', '.join(priority_items)}")
                    print(f"   🎯 Prioritizing: {', '.join(priority_items[:3])}")

                # Analyze complexity and determine query type
                query_type = self.exec_chef.decide_query_type(user_prefs)
                log.append(f"Executive Chef: Query type determined as '{query_type}'")
                print(f"   Strategy: {query_type}")

                # Message to Pantry Agent about strategy (communication)
                pantry_request = self.pantry.create_message_to_agent(
                    target_agent='executive_chef',
                    action='strategy_acknowledgment',
                    data={
                        'query_type': query_type,
                        'prioritize_expiring': len(expiring) > 0,
                        'expiring_count': len(expiring)
                    },
                    priority='medium'
                )
                log.append(f"Executive Chef: Communicated strategy to Pantry Agent")

                return Command(
                    update={
                        "coordination_log": log,
                        "query_type": query_type
                    },
                    goto="recipe_knowledge_retrieve"
                )
            else:
                log.append("Executive Chef: no handoff packet found; proceeding cautiously")
                return Command(
                    update={
                        "coordination_log": log,
                        "query_type": "ingredient"  # default
                    },
                    goto="recipe_knowledge_retrieve"
                )

        def sous_chef_recommend(state) -> Command[Literal["wait_for_user_selection"]]:
            """
            Sous Chef generates top 3 recipe recommendations.
            
            Flow:
            1. Receive recipe results from Recipe Knowledge Agent
            2. Analyze based on pantry, preferences, expiring items
            3. Generate top 3 recommendations
            4. Present to user
            5. Always go to wait_for_user_selection (which handles auto-select or user input)
            """
            log = state.get("coordination_log", [])
            
            log.append("Sous Chef: Analyzing recipes and generating recommendations")
            print("\n👨‍🍳 Sous Chef: Generating top 3 recommendations...\n")
            
            # Get required data from state
            recipe_results = state.get("recipe_results", [])
            pantry_summary = state.get("pantry_summary", {})
            user_prefs = state.get("user_preferences", {})
            expiring_items = state.get("expiring_items", [])
            
            if not recipe_results:
                log.append("Sous Chef: ERROR - No recipe results available")
                print("❌ No recipe results to analyze")
                return Command(update={
                    "coordination_log": log,
                    "sous_chef_recommendations": []
                })
            
            # Generate recommendations
            recommendations = self.sous_chef.generate_recommendations(
                llm=llm,
                pantry_summary=pantry_summary,
                user_preferences=user_prefs,
                expiring_items=expiring_items,
                recipe_results=recipe_results
            )
            
            if not recommendations:
                log.append("Sous Chef: ERROR - Failed to generate recommendations")
                print("❌ Failed to generate recommendations")
                return Command(update={
                    "coordination_log": log,
                    "sous_chef_recommendations": []
                })
            
            # Present to user
            presentation = self.sous_chef.present_recommendations(llm, recommendations)
            
            print("\n" + "="*80)
            print("🍽️  SOUS CHEF RECOMMENDATIONS")
            print("="*80 + "\n")
            print(presentation)
            print("\n" + "="*80 + "\n")
            
            log.append(f"Sous Chef: Generated {len(recommendations)} recommendations")
            
            # Always go to wait_for_user_selection (it handles auto-select logic)
            return Command(
                update={
                    "coordination_log": log,
                    "sous_chef_recommendations": recommendations
                },
                goto="wait_for_user_selection"
            )

        def wait_for_user_selection(state) -> Command[Literal["sous_chef_adapt"]]:
            """
            Wait for user to select a recipe (1, 2, or 3).
            
            This node interrupts execution (via interrupt_before) to get user input,
            OR can auto-select if configured.
            """
            log = state.get("coordination_log", [])
            
            # Check if auto-select is enabled
            auto_select = state.get("auto_select_recipe", False)
            
            if auto_select:
                # Auto-select first recipe (for demo/testing)
                log.append("Auto-selecting recipe #1 (demo mode)")
                print(f"\n[Demo Mode] Auto-selecting recipe #1\n")
                return Command(
                    update={
                        "coordination_log": log,
                        "user_recipe_selection": 1
                    },
                    goto="sous_chef_adapt"
                )
            
            # Check if user has made a selection
            selection = state.get("user_recipe_selection")
            
            if selection:
                log.append(f"User selected recipe #{selection}")
                print(f"\n✅ User selected recipe #{selection}\n")
                return Command(
                    update={"coordination_log": log},
                    goto="sous_chef_adapt"
                )
            else:
                # Need user input - the interrupt_before will pause execution here
                # Just indicate we're waiting and continue (interrupt will happen)
                log.append("Waiting for user recipe selection...")
                print("\n⏳ Waiting for your selection (1, 2, or 3)...\n")
                return Command(
                    update={"coordination_log": log},
                    goto="wait_for_user_selection"
                )

        # def sous_chef_adapt(state) -> Command[Literal["executive_chef_quality_check"]]:
        #     """
        #     Sous Chef adapts the selected recipe to user's dietary requirements.
            
        #     Flow:
        #     1. Get user's recipe selection
        #     2. Find full recipe data
        #     3. Adapt based on dietary restrictions and allergies
        #     4. Format for user presentation
        #     5. Pass to Executive Chef for quality check
        #     """
        #     log = state.get("coordination_log", [])
            
        #     log.append("Sous Chef: Adapting selected recipe")
        #     print("\n🔧 Sous Chef: Adapting recipe to your dietary needs...\n")
            
        #     # Get selection and recipe data
        #     selection = state.get("user_recipe_selection")
        #     recipe_results = state.get("recipe_results", [])
        #     user_prefs = state.get("user_preferences", {})
        #     pantry_inventory = state.get("pantry_inventory", [])

        #     if not selection:
        #         log.append("Sous Chef: ERROR - No recipe selection found")
        #         print("❌ No recipe selection found")
        #         return Command(update={"coordination_log": log})

        #     # Ensure Sous Chef remembers the latest recommendations
        #     if not self.sous_chef.current_recommendations:
        #         cached_recs = state.get("sous_chef_recommendations", [])
        #         if cached_recs:
        #             self.sous_chef.current_recommendations = cached_recs

        #     # Handle selection
        #     selected_recipe = self.sous_chef.handle_user_selection(selection, recipe_results)
            
        #     if not selected_recipe:
        #         log.append(f"Sous Chef: ERROR - Invalid selection: {selection}")
        #         print(f"❌ Invalid selection: {selection}")
        #         return Command(update={"coordination_log": log})
            
        #     log.append(f"Sous Chef: Selected recipe: {selected_recipe.get('title', 'Unknown')}")
            
        #     # Adapt recipe
        #     adapted_recipe = self.sous_chef.adapt_recipe(
        #         llm=llm,
        #         recipe=selected_recipe,
        #         user_preferences=user_prefs,
        #         pantry_inventory=pantry_inventory
        #     )
            
        #     if "error" in adapted_recipe:
        #         log.append(f"Sous Chef: ERROR - Adaptation failed: {adapted_recipe['error']}")
        #         print(f"❌ Adaptation failed: {adapted_recipe.get('error')}")
        #         fallback_text = self.sous_chef.build_fallback_recipe_summary(selected_recipe, user_prefs)
        #         return Command(
        #             update={
        #                 "coordination_log": log,
        #                 "selected_recipe_data": selected_recipe,
        #                 "adapted_recipe": adapted_recipe,
        #                 "formatted_recipe": fallback_text,
        #                 "final_recommendation": fallback_text
        #             },
        #             goto="executive_chef_quality_check"
        #         )
            
        #     # Format for presentation
        #     formatted_recipe = self.sous_chef.format_adapted_recipe(llm, adapted_recipe)
            
        #     log.append("Sous Chef: Recipe adapted successfully")
        #     print("✅ Recipe adaptation complete\n")
            
        #     # Show preview (optional)
        #     if state.get("show_adapted_preview", True):
        #         print("="*80)
        #         print("🍳 ADAPTED RECIPE PREVIEW")
        #         print("="*80 + "\n")
        #         print(formatted_recipe[:500] + "..." if len(formatted_recipe) > 500 else formatted_recipe)
        #         print("\n" + "="*80 + "\n")
            
        #     return Command(
        #         update={
        #             "coordination_log": log,
        #             "selected_recipe_data": selected_recipe,
        #             "adapted_recipe": adapted_recipe,
        #             "formatted_recipe": formatted_recipe,
        #             "final_recommendation": formatted_recipe  # For Executive Chef quality check
        #         },
        #         goto="executive_chef_quality_check"
        #     )

        def sous_chef_adapt(state) -> Command[Literal["executive_chef_quality_check"]]:
            """
            Sous Chef adapts the selected recipe to user's dietary requirements.

            Flow:
            1. Get user's recipe selection
            2. Resolve full recipe data from cached recommendations / prior results
            3. Adapt based on dietary restrictions and allergies
            4. Format for user presentation
            5. Pass to Executive Chef for quality check
            """
            log = state.get("coordination_log", [])
            log.append("Sous Chef: Adapting selected recipe")
            print("\n🔧 Sous Chef: Adapting recipe to your dietary needs...\n")

            # --- gather prior state (NO NEW SEARCH HERE) ---
            selection = state.get("user_recipe_selection")
            recipe_results = state.get("recipe_results", [])  # from RECIPE_SEARCH node
            user_prefs = state.get("user_preferences", {})
            pantry_inventory = state.get("pantry_inventory", [])

            if not selection:
                log.append("Sous Chef: ERROR - No recipe selection found")
                print("❌ No recipe selection found")
                return Command(update={"coordination_log": log})

            # seed in-memory recs from state if needed
            if not self.sous_chef.current_recommendations:
                cached_recs = state.get("sous_chef_recommendations", [])
                if cached_recs:
                    self.sous_chef.current_recommendations = cached_recs

            # resolve the user's chosen recipe solely from cached results
            selected_recipe = self.sous_chef.handle_user_selection(selection, recipe_results)
            if not selected_recipe:
                log.append(f"Sous Chef: ERROR - Invalid selection: {selection}")
                print(f"❌ Invalid selection: {selection}")
                return Command(update={"coordination_log": log})

            log.append(f"Sous Chef: Selected recipe: {selected_recipe.get('title', 'Unknown')}")

            # --- adapt the chosen recipe only (NO RECOMMEND / NO SEARCH) ---
            adapted_recipe = self.sous_chef.adapt_recipe(
                llm=llm,
                recipe=selected_recipe,
                user_preferences=user_prefs,
                pantry_inventory=pantry_inventory
            )

            if "error" in adapted_recipe:
                log.append(f"Sous Chef: ERROR - Adaptation failed: {adapted_recipe['error']}")
                print(f"❌ Adaptation failed: {adapted_recipe.get('error')}")
                fallback_text = self.sous_chef.build_fallback_recipe_summary(selected_recipe, user_prefs)
                return Command(
                    update={
                        "coordination_log": log,
                        "selected_recipe_data": selected_recipe,
                        "adapted_recipe": None,
                        "formatted_recipe": fallback_text
                    },
                    goto="executive_chef_quality_check"
                )

            formatted_recipe = self.sous_chef.format_recipe_for_user(adapted_recipe, user_prefs)

            # optional preview
            if state.get("show_adapted_preview", True):
                print("="*80)
                print("🍳 ADAPTED RECIPE PREVIEW")
                print("="*80 + "\n")
                print(formatted_recipe[:500] + "..." if len(formatted_recipe) > 500 else formatted_recipe)
                print("\n" + "="*80 + "\n")

            return Command(
                update={
                    "coordination_log": log,
                    "selected_recipe_data": selected_recipe,
                    "adapted_recipe": adapted_recipe,
                    "formatted_recipe": formatted_recipe,
                },
                goto="executive_chef_quality_check"
            )


        def recipe_knowledge_agent(state):
            """Retrieve recipes based on user preferences and ingredients"""
            log = state.get("coordination_log", [])
            
            if not self.recipe_agent:
                log.append("Recipe Knowledge Agent: Not initialized. Run ingestion script first.")
                print("⚠️  Recipe Knowledge Agent not available")
                return Command(update={
                    "coordination_log": log,
                    "recipe_results": []
                })
            
            # Get user ingredients and preferences
            user_ingredients = state.get("user_ingredients", [])
            user_prefs = state.get("user_preferences", {})
            
            if not user_ingredients:
                log.append("Recipe Knowledge Agent: No ingredients provided")
                print("Recipe Agent: No ingredients to search with")
                return Command(update={
                    "coordination_log": log,
                    "recipe_results": []
                })
            
            # Build query text from preferences
            query_parts = []
            if user_prefs.get("cuisines"):
                query_parts.append(", ".join(user_prefs["cuisines"]))
            if user_prefs.get("diet"):
                query_parts.append(user_prefs["diet"])
            if user_prefs.get("skill"):
                skill_map = {"beginner": "easy", "intermediate": "moderate", "advanced": "complex"}
                query_parts.append(skill_map.get(user_prefs["skill"], ""))
            
            query_text = " ".join(query_parts) if query_parts else "dinner recipe"
            
            log.append(f"Recipe Knowledge Agent: Searching with ingredients={user_ingredients}, query='{query_text}'")
            print(f"\n🔍 Recipe Agent: Searching for recipes...")
            print(f"   Ingredients: {', '.join(user_ingredients)}")
            print(f"   Preferences: {query_text}")
            
            # Perform LEFTOVR hybrid search
            try:
                results = self.recipe_agent.hybrid_query(
                    pantry_items=user_ingredients,
                    query_text=query_text,
                    allow_missing=2,  # Willing to buy up to 2 items
                    top_k=10,
                    use_semantic=True
                )
                
                # Format results - NEW FORMAT: (metadata, score, num_used, missing)
                recipe_results = []
                for metadata, score, num_used, missing in results:
                    recipe_results.append({
                        "id": metadata.get("id"),
                        "title": metadata.get("title"),
                        "ingredients": metadata.get("ner", []),
                        "link": metadata.get("link"),
                        "source": metadata.get("source"),
                        "score": float(score),
                        "pantry_items_used": num_used,
                        "missing_ingredients": missing
                    })
                
                log.append(f"Recipe Knowledge Agent: Found {len(recipe_results)} recipes")
                print(f"✅ Found {len(recipe_results)} matching recipes")
                
                # Display top 3 recipes
                for i, recipe in enumerate(recipe_results[:3], 1):
                    print(f"\n{i}. {recipe['title']} (score: {recipe['score']:.0f})")
                    print(f"   Uses {recipe['pantry_items_used']}/{len(user_ingredients)} of your leftovers")
                    if recipe['missing_ingredients']:
                        print(f"   Need to buy: {', '.join(recipe['missing_ingredients'])}")
                    else:
                        print(f"   ✅ Can make NOW!")
                    print(f"   Source: {recipe['source']}")
                
                return Command(
                    update={
                        "coordination_log": log,
                        "recipe_results": recipe_results
                    },
                    goto="sous_chef_recommend"
                )
                
            except Exception as e:
                log.append(f"Recipe Knowledge Agent: Error during search - {str(e)}")
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                return Command(
                    update={
                        "coordination_log": log,
                        "recipe_results": []
                    },
                    goto="sous_chef_recommend"
                )

        def exec_chef_check(state):
            log = state.get("coordination_log", [])

            log.append("Executive Chef: Performing final quality check")
            print("Executive Chef: Quality control in progress...")

            # Get all the data collected so far
            user_prefs = state.get("user_preferences", {})
            pantry_inventory = state.get("pantry_inventory", [])
            expiring_items = state.get("expiring_items", [])
            pantry_summary = state.get("pantry_summary", {})

            # Use Executive Chef to orchestrate and synthesize
            print("Executive Chef: Synthesizing final recommendation...")

            # Prepare agent responses for synthesis (including pantry data)
            agent_responses = {
                "user_preferences": user_prefs,
                "pantry_inventory": pantry_inventory,
                "expiring_items": expiring_items,
                "pantry_summary": pantry_summary
            }

            # Generate recommendation
            recommendation = self.exec_chef.synthesize_recommendations(
                llm,
                agent_responses,
                user_prefs
            )

            # Perform quality check
            passed, issues = self.exec_chef.perform_quality_check(
                llm,
                recommendation,
                user_prefs
            )

            if passed:
                log.append("Executive Chef: ✅ Quality check passed - recommendation approved")
                print("Executive Chef: ✅ All quality checks passed")
            else:
                log.append(f"Executive Chef: ⚠️ Quality issues detected: {', '.join(issues)}")
                print(f"Executive Chef: ⚠️ Issues found: {', '.join(issues)}")

            return Command(
                update={
                    "coordination_log": log,
                    "final_recommendation": recommendation,
                    "quality_passed": passed,
                    "quality_issues": issues
                }
            )

        def waiter_return(state):
            log = state.get("coordination_log", [])
            recommendation = state.get("final_recommendation", "")
            quality_passed = state.get("quality_passed", False)

            log.append("Waiter: Preparing to present recommendation to user")
            print("\n" + "="*80)
            print("🍽️  MAISON D'ÊTRE - Your Culinary Recommendation")
            print("="*80)

            if recommendation:
                print(recommendation)
            else:
                print("I apologize, but I wasn't able to generate a recommendation at this time.")

            if not quality_passed:
                print("\n⚠️  Note: Some quality issues were detected. Please review carefully.")

            print("="*80 + "\n")

            return Command(update={"coordination_log": log})

        workflow.add_node("waiter_collect_info", waiter_agent_collect)
        workflow.add_node("pantry_check", pantry_check)
        workflow.add_node("executive_chef_review", exec_chef_review)
        workflow.add_node("recipe_knowledge_retrieve", recipe_knowledge_agent)
        workflow.add_node("sous_chef_recommend", sous_chef_recommend)
        workflow.add_node("wait_for_user_selection", wait_for_user_selection)
        workflow.add_node("sous_chef_adapt", sous_chef_adapt)
        workflow.add_node("executive_chef_quality_check", exec_chef_check)
        workflow.add_node("return_to_user", waiter_return)


        # 2. Define edges - Fixed workflow logic
        # Flow: waiter → pantry → exec_chef_review → recipe_knowledge → sous_chef_recommend → 
        #       wait_for_selection → sous_chef_adapt → exec_chef_quality_check → return_to_user
        
        workflow.add_edge("pantry_check", "executive_chef_review")
        
        workflow.add_edge("executive_chef_review", "recipe_knowledge_retrieve")
        
        # Recipe Knowledge Agent retrieves recipes, then Sous Chef recommends
        workflow.add_edge("recipe_knowledge_retrieve", "sous_chef_recommend")
        workflow.add_edge("sous_chef_recommend", "wait_for_user_selection")
        
        # Sous Chef recommends, then waits for user selection (routing handled by Command.goto)
        # Note: wait_for_user_selection routes via Command.goto to either return_to_user or sous_chef_adapt
        workflow.add_edge("wait_for_user_selection", "sous_chef_adapt")

        # After user selects and recipe is adapted, quality check happens
        workflow.add_edge("sous_chef_adapt", "executive_chef_quality_check")
        
        # Finally, return to user
        workflow.add_edge("executive_chef_quality_check", "return_to_user")

        # 3. Set entry and end nodes
        workflow.set_entry_point("waiter_collect_info")
        workflow.set_finish_point("return_to_user")

        # Modern compilation with advanced features
        return workflow.compile(
            cache=InMemoryCache(),
            interrupt_before=["return_to_user", "wait_for_user_selection"],
            interrupt_after=[],
        )

    async def run_hybrid(self, initial_user_message: Optional[str] = None):
        state = {
            "user_preferences": {},
            "waiter_satisfied": False,
            "handoff_packet": {},
            "query_type": None,
            "latest_user_message": initial_user_message,
            "final_recommendation": None,
            "quality_passed": False,
            "quality_issues": [],
            "agent_assignments": {},
            "messages": [],
            "coordination_log": [],

            # Pantry-related state
            "pantry_inventory": [],
            "expiring_items": [],
            "pantry_summary": {},
            "recipe_feasibility": None,
            
            # Sous chef state
            "sous_chef_recommendations": [],
            "user_recipe_selection": None,
            "selected_recipe_data": None,
            "adapted_recipe": None,
            "formatted_recipe": None,
            "auto_select_recipe": False,  # Set to True for demo mode
            "show_adapted_preview": True
        }

        state = await self.graph.ainvoke(state)

        while True:
            # If the graph stopped for user input (interrupt_before="return_to_user")
            if state.get("_interrupt") == "return_to_user" or not state["waiter_satisfied"]:
                user_text = input("You: ")
                if user_text.strip().lower() in {"exit", "quit"}:
                    print("👋 Exiting the conversation...")
                    break

                # Inject user input and resume from where we paused
                state["latest_user_message"] = user_text
                state = await self.graph.ainvoke(state, config={"resume": True})
                
            elif state.get("_interrupt") == "wait_for_user_selection":
                # Get user's recipe selection
                recommendations = state.get("sous_chef_recommendations", [])
                if recommendations:
                    print("\nWhich recipe would you like to make?")
                    selection = input("Enter 1, 2, or 3 (or 'quit' to exit): ").strip()
                    
                    if selection.lower() in {"exit", "quit"}:
                        break
                    
                    try:
                        selection_int = int(selection)
                        if 1 <= selection_int <= 3:
                            state["user_recipe_selection"] = selection_int
                            state = await self.graph.ainvoke(state, config={"resume": True})
                        else:
                            print("❌ Please enter 1, 2, or 3")
                            continue
                    except ValueError:
                        print("❌ Please enter a number (1, 2, or 3)")
                        continue
                else:
                    print("❌ No recommendations available")
                    break
            else:
                # Workflow has reached finish point
                print("\n✅ Workflow complete!")
                break

        print("\n=== Final State ===")
        print(json.dumps(state, indent=2, default=str))

if __name__ == "__main__":
    system = ModernCollaborativeSystem()
    asyncio.run(system.run_hybrid())
