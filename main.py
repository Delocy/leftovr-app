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

@dataclass
class Task:
    id: str
    description: str
    priority: str  # "high", "medium", "low"
    estimated_time: int  # in minutes
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    result: Optional[str] = None
    assigned_to: Optional[str] = None

# Modern collaborative state
class ModernCollaborativeState(MessagesState):
    user_preferences: Dict[str, Any]
    waiter_satisfied: bool
    handoff_packet: Dict[str, Any]
    query_type: Optional[Literal["ingredient", "recipe"]]
    latest_user_message: Optional[str]
    waiter_prompt_sent: bool



    
class ModernCollaborativeSystem:
    """collaborative system with enhanced orchestration"""

    def __init__(self):
        self.graph = self._create_modern_collaborative_graph()
        self.waiter = WaiterAgent(name="Maison d'Être")

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
                log.append(f"Waiter intro: {intro}")
                return Command(
                    update={
                        "coordination_log": log,
                        "waiter_satisfied": False,
                        "waiter_prompt_sent": True,
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
                log.append(f"Waiter: missing fields -> {', '.join(missing)}")
                print(f"Waiter: missing fields -> {', '.join(missing)}")
                # Ask user to provide the missing fields; return control to user
                return Command(
                    update={
                        "waiter_satisfied": False,
                        "coordination_log": log,
                        "user_preferences": prefs,
                        "waiter_prompt_sent": True,
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
            return Command(update={})

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
            interrupt_before=[],
            interrupt_after=[],
        )
    
    async def run_hybrid(self, initial_user_message: Optional[str] = None):
        state = {
            "user_preferences": {},
            "waiter_satisfied": False,
            "handoff_packet": {},
            "query_type": None,
            "latest_user_message": initial_user_message,
            "waiter_prompt_sent": False,
            "tasks": [],
            "completed_tasks": [],
            "failed_tasks": [],
            "in_progress_tasks": [],
            "agent_assignments": {},
            "messages": [],
            "coordination_log": [],
        }
        
        awaiting_user_input = False

        while True:
            # Invoke the graph
            state = await self.graph.ainvoke(state)

            # If the graph has reached a node that requires user input, pause
            if not state["waiter_satisfied"]:
                awaiting_user_input = True

            # Only prompt user when awaiting input
            print(f"Waiter: {self.waiter.run(llm)}")
            if awaiting_user_input:
                user_text = input("You: ")
                if user_text.strip().lower() in {"exit", "quit"}:
                    print("Exiting...")
                    break
                
                reply = self.waiter.respond(llm, user_text)
                print(f"Waiter: {reply}")
            
                # Update state and reset flag so graph continues
                state["latest_user_message"] = user_text
                awaiting_user_input = False

            # Stop only if graph reached its finish point
            if state.get("_current_node") == END:
                print("Workflow complete.")
                break


        print("\n=== Final State ===")
        print(json.dumps(state, indent=2, default=str))
        
if __name__ == "__main__":
    system = ModernCollaborativeSystem()
    asyncio.run(system.run_hybrid())    
