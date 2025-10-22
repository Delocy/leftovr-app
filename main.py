import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Literal
import json
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
    coordination_log: List[str]

    # Pantry-related fields
    pantry_inventory: List[Dict[str, Any]]
    expiring_items: List[Dict[str, Any]]
    pantry_summary: Dict[str, Any]
    recipe_feasibility: Optional[Dict[str, Any]]

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

    def _create_modern_collaborative_graph(self) -> StateGraph:
        """Create collaborative workflow with Command API"""
        workflow = StateGraph(ModernCollaborativeState)

        def waiter_agent_collect(state) -> Command[Literal["waiter_collect_info", "pantry_check", "return_to_user"]]:
            # Ensure log exists
            log = state.get("coordination_log", [])

            # Initialize current preferences dict
            current_prefs = state.get("user_preferences", {}) or {}

            # If there is a latest user message, extract preferences and merge
            latest = state.get("latest_user_message")
            if latest:
                extracted = self.waiter.extract_preferences(llm, latest)
                # Merge strategy: fill missing scalar fields, union list fields
                def merge_list(key):
                    existing = list(current_prefs.get(key, []) or [])
                    incoming = list(extracted.get(key, []) or [])
                    merged = existing + [x for x in incoming if x not in existing]
                    return merged

                merged_prefs = {
                    "diet": current_prefs.get("diet") or extracted.get("diet"),
                    "skill": current_prefs.get("skill") or extracted.get("skill"),
                    "allergies": merge_list("allergies"),
                    "restrictions": merge_list("restrictions"),
                    "cuisines": merge_list("cuisines"),
                }
                current_prefs = merged_prefs

            # If still no preferences, greet and ask, then return control to user
            if not current_prefs:
                intro = self.waiter.run(llm)
                # log.append(f"Waiter intro: {intro}")
                print(f"Waiter: {intro}")
                return Command(
                    update={
                        "coordination_log": log,
                        "waiter_satisfied": False,
                        "latest_user_message": None
                    },
                    goto="return_to_user"
                )

            # Minimal satisfaction heuristic: require all essential fields
            prefs = current_prefs
            required = ["diet", "allergies", "restrictions", "cuisines", "skill"]
            satisfied = all(bool(prefs.get(k)) for k in required)
            if satisfied:
                log.append("Waiter: preferences complete, checking pantry inventory")
                print("Waiter: preferences complete, checking pantry inventory")
                return Command(
                    update={
                        "waiter_satisfied": True,
                        "handoff_packet": {
                            "user_preferences": prefs,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "notes": "Collected by waiter; ready for pantry check."
                        },
                        "coordination_log": log,
                        "user_preferences": prefs,
                        "latest_user_message": None
                    },
                    goto="pantry_check"
                )
            else:
                missing = [k for k in required if not prefs.get(k)]
                # log.append(f"Waiter: missing fields -> {', '.join(missing)}")
                print(f"Waiter: missing fields -> {', '.join(missing)}")
                # Ask user to provide the missing fields; return control to user
                return Command(
                    update={
                        "waiter_satisfied": False,
                        "coordination_log": log,
                        "user_preferences": prefs,
                        "latest_user_message": None
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

        def exec_chef_review(state) -> Command[Literal["executive_chef_quality_check"]]:
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
                    goto="executive_chef_quality_check"
                )
            else:
                log.append("Executive Chef: no handoff packet found; proceeding cautiously")
                return Command(
                    update={
                        "coordination_log": log,
                        "query_type": "ingredient"  # default
                    },
                    goto="executive_chef_quality_check"
                )

        def sous_chef_handle(state):
            return Command(update={})

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
                
                return Command(update={
                    "coordination_log": log,
                    "recipe_results": recipe_results
                })
                
            except Exception as e:
                log.append(f"Recipe Knowledge Agent: Error during search - {str(e)}")
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                return Command(update={
                    "coordination_log": log,
                    "recipe_results": []
                })

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
        workflow.add_node("sous_chef_prepare_recipe", sous_chef_handle)
        workflow.add_node("recipe_knowledge_retrieve", recipe_knowledge_agent)
        workflow.add_node("executive_chef_quality_check", exec_chef_check)
        workflow.add_node("return_to_user", waiter_return)


        # 2. Define edges
        # Routing from waiter_collect_info is controlled at runtime via Command.goto
        workflow.add_edge("pantry_check", "executive_chef_review")
        workflow.add_edge("executive_chef_review", "executive_chef_quality_check")

        workflow.add_edge("sous_chef_prepare_recipe", "recipe_knowledge_retrieve")
        # workflow.add_edge("recipe_knowledge_retrieve", "sous_chef_prepare_recipe")
        # workflow.add_edge("sous_chef_prepare_recipe", "executive_chef_quality_check")
        workflow.add_edge("recipe_knowledge_retrieve", "executive_chef_quality_check")
        workflow.add_edge("executive_chef_quality_check", "return_to_user")

        # 3. Set entry and end nodes
        workflow.set_entry_point("waiter_collect_info")
        workflow.set_finish_point("return_to_user")

        # Modern compilation with advanced features
        return workflow.compile(
            cache=InMemoryCache(),
            interrupt_before=["return_to_user"],
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
            else:
                # Workflow has reached finish point
                print("\n✅ Workflow complete!")
                break

        print("\n=== Final State ===")
        print(json.dumps(state, indent=2, default=str))

if __name__ == "__main__":
    system = ModernCollaborativeSystem()
    asyncio.run(system.run_hybrid())
