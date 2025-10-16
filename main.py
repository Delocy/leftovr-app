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
    """collaborative state extending MessagesState"""
    # Conversation/control fields used by nodes
    user_preferences: Dict[str, Any]  # expects keys: diet, allergies, restrictions, cuisines, skill
    waiter_satisfied: bool
    handoff_packet: Dict[str, Any]
    # Query routing hint for pantry/recipe branch
    query_type: Optional[Literal["ingredient", "recipe"]]
    # Chat integration fields
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
                log.append("Waiter: merged extracted preferences from latest_user_message")

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
                print("Missing fields")
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

        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-waiter", action="store_true", help="Interactive CLI chat with the waiter agent")
    parser.add_argument("--run-once", action="store_true", help="Invoke the graph once and print resulting state")
    parser.add_argument("--prefs-json", type=str, default="", help="Seed state.user_preferences as JSON")
    parser.add_argument("--latest-message", type=str, default="", help="Seed state.latest_user_message text")
    parser.add_argument("--draw-graph", action="store_true", help="Print mermaid diagram of the workflow")
    args = parser.parse_args()

    if args.draw_graph:
        system = ModernCollaborativeSystem()
        g = system.graph.get_graph(xray=True)
        print(g.draw_mermaid())
    elif args.chat_waiter:
        waiter = WaiterAgent(name="Maison d'Être")
        prefs = {"diet": None, "allergies": [], "restrictions": [], "cuisines": [], "skill": None}

        def merge_list(existing, incoming):
            return (existing or []) + [x for x in (incoming or []) if x not in (existing or [])]

        def satisfied(p):
            return all([
                bool(p.get("diet")),
                bool(p.get("allergies")),
                bool(p.get("restrictions")),
                bool(p.get("cuisines")),
                bool(p.get("skill")),
            ])

        print("You are now chatting with the waiter. Type 'exit' to quit.\n")
        print(f"Waiter: {waiter.run(llm)}")
        while True:
            try:
                user_text = input("You: ")
            except EOFError:
                break
            if not user_text or user_text.strip().lower() in {"exit", "quit"}:
                break

            reply = waiter.respond(llm, user_text)
            print(f"Waiter: {reply}")

            extracted = waiter.extract_preferences(llm, user_text)
            prefs = {
                "diet": prefs.get("diet") or extracted.get("diet"),
                "skill": prefs.get("skill") or extracted.get("skill"),
                "allergies": merge_list(prefs.get("allergies"), extracted.get("allergies")),
                "restrictions": merge_list(prefs.get("restrictions"), extracted.get("restrictions")),
                "cuisines": merge_list(prefs.get("cuisines"), extracted.get("cuisines")),
            }

            print("\n[Summary so far]")
            print(f"- diet: {prefs['diet']}")
            print(f"- allergies: {prefs['allergies']}")
            print(f"- restrictions: {prefs['restrictions']}")
            print(f"- cuisines: {prefs['cuisines']}")
            print(f"- skill: {prefs['skill']}\n")

            if satisfied(prefs):
                handoff_packet = {
                    "user_preferences": prefs,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "notes": "Collected by waiter; ready for executive chef."
                }
                print("Waiter: Thanks! I have everything I need. Handing off to the executive chef.")
                print("\n[Handoff Packet]")
                print(handoff_packet)
                break
    elif args.run_once:
        system = ModernCollaborativeSystem()
        try:
            prefs = json.loads(args.prefs_json) if args.prefs_json else {}
        except json.JSONDecodeError:
            print("Invalid --prefs-json; using empty preferences.")
            prefs = {}

        initial_state = {
            "user_preferences": prefs,
            "waiter_satisfied": False,
            "handoff_packet": {},
            "query_type": None,
            "latest_user_message": args.latest_message or None,
            "waiter_prompt_sent": False,
            # required scaffolding keys
            "tasks": [],
            "completed_tasks": [],
            "failed_tasks": [],
            "in_progress_tasks": [],
            "agent_assignments": {},
            "messages": [],
            "coordination_log": [],
        }

        final_state = system.graph.invoke(initial_state)
        print("\n=== Final State Snapshot ===")
        for k in [
            "user_preferences",
            "waiter_satisfied",
            "handoff_packet",
            "latest_user_message",
            "waiter_prompt_sent",
        ]:
            if k in final_state:
                print(f"{k}: {final_state[k]}")
        print("\n--- coordination_log ---")
        for line in final_state.get("coordination_log", []):
            print(f"- {line}")
    else:
        ModernCollaborativeSystem()