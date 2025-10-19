import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
import json
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph.cache.memory import InMemoryCache
import asyncio
from datetime import datetime, timezone
import argparse

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


# Modern collaborative state
class ModernCollaborativeState(MessagesState):
    user_preferences: Dict[str, Any]
    waiter_satisfied: bool
    handoff_packet: Dict[str, Any]
    query_type: Optional[Literal["ingredient", "recipe"]]
    latest_user_message: Optional[str]
    user_ingredients: List[str]  # pantry ingredients from user
    recipe_results: List[Dict[str, Any]]  # retrieved recipes



    
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
            self.recipe_agent.try_load_faiss()  # Optional: loads embeddings if available
            print("✅ Recipe Knowledge Agent initialized successfully")
        except FileNotFoundError as e:
            print(f"⚠️  Warning: {e}")
            print("   Run the ingestion script first: python scripts/ingest_recipes.py --input assets/full_dataset.csv --outdir data")
            self.recipe_agent = None

    def _create_modern_collaborative_graph(self) -> StateGraph:
        """Create collaborative workflow with Command API"""
        workflow = StateGraph(ModernCollaborativeState)
        
            # --- STUB FUNCTIONS ---
        def waiter_agent_collect(state) -> Command[Literal["waiter_collect_info", "executive_chef_review", "return_to_user"]]:
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
                log.append("Waiter: preferences complete, handing off to executive chef")
                print("Waiter: preferences complete, handing off to executive chef")
                return Command(
                    update={
                        "waiter_satisfied": True,
                        "handoff_packet": {
                            "user_preferences": prefs,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "notes": "Collected by waiter; ready for executive chef."
                        },
                        "coordination_log": log,
                        "user_preferences": prefs, 
                        "latest_user_message": None
                    },
                    goto="executive_chef_review"
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

        def exec_chef_review(state) -> Command[Literal["pantry_query"]]:
            log = state.get("coordination_log", [])
            if state.get("handoff_packet"):
                log.append("Executive Chef: handoff packet received; proceeding to pantry query")
            else:
                log.append("Executive Chef: no handoff packet found; proceeding cautiously")
            return Command(update={"coordination_log": log}, goto="pantry_query")

        def pantry_agent_query(state):
            return Command(update={})

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
            
            # Perform hybrid search
            try:
                results = self.recipe_agent.hybrid_query(
                    pantry_items=user_ingredients,
                    query_text=query_text,
                    top_k=10
                )
                
                # Format results
                recipe_results = []
                for metadata, score in results:
                    recipe_results.append({
                        "id": metadata.get("id"),
                        "title": metadata.get("title"),
                        "ingredients": metadata.get("ner", []),
                        "link": metadata.get("link"),
                        "source": metadata.get("source"),
                        "score": float(score)
                    })
                
                log.append(f"Recipe Knowledge Agent: Found {len(recipe_results)} recipes")
                print(f" Found {len(recipe_results)} matching recipes")
                
                # Display top 3 recipes
                for i, recipe in enumerate(recipe_results[:3], 1):
                    print(f"\n{i}. {recipe['title']} (score: {recipe['score']:.2f})")
                    print(f"   Ingredients: {', '.join(recipe['ingredients'][:5])}{'...' if len(recipe['ingredients']) > 5 else ''}")
                    print(f"   Source: {recipe['source']}")
                
                return Command(update={
                    "coordination_log": log,
                    "recipe_results": recipe_results
                })
                
            except Exception as e:
                log.append(f"Recipe Knowledge Agent: Error during search - {str(e)}")
                print(f"❌ Error: {e}")
                return Command(update={
                    "coordination_log": log,
                    "recipe_results": []
                })

        def exec_chef_check(state):
            return Command(update={})

        def waiter_return(state):
            return Command(update={})

        workflow.add_node("waiter_collect_info", waiter_agent_collect)
        workflow.add_node("executive_chef_review", exec_chef_review)
        workflow.add_node("pantry_query", pantry_agent_query)
        workflow.add_node("sous_chef_prepare_recipe", sous_chef_handle)
        workflow.add_node("recipe_knowledge_retrieve", recipe_knowledge_agent)
        workflow.add_node("executive_chef_quality_check", exec_chef_check)
        workflow.add_node("return_to_user", waiter_return)

                
        # 2. Define edges
        # Routing from waiter_collect_info is controlled at runtime via Command.goto
        workflow.add_edge("executive_chef_review", "pantry_query")

        workflow.add_conditional_edges(
            "pantry_query",
            lambda state: "ingredient" if state["query_type"] == "ingredient" else "recipe",
            {
                "ingredient": "executive_chef_quality_check",
                "recipe": "sous_chef_prepare_recipe"
            }
        )

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
            "agent_assignments": {},
            "messages": [],
            "coordination_log": [],
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
