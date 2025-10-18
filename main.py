import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Literal
import json
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command

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
from agents.executive_chef_agent import ExecutiveChefAgent


# Modern collaborative state
class ModernCollaborativeState(MessagesState):
    user_preferences: Dict[str, Any]
    waiter_satisfied: bool
    handoff_packet: Dict[str, Any]
    query_type: Optional[Literal["ingredient", "recipe"]]
    latest_user_message: Optional[str]
    final_recommendation: Optional[str]
    quality_passed: bool
    quality_issues: List[str]
    coordination_log: List[str]

class ModernCollaborativeSystem:
    """collaborative system with enhanced orchestration"""

    def __init__(self):
        self.graph = self._create_modern_collaborative_graph()
        self.waiter = WaiterAgent(name="Maison d'Être")
        self.exec_chef = ExecutiveChefAgent(name="Executive Chef")

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

        def exec_chef_review(state) -> Command[Literal["executive_chef_quality_check"]]:
            log = state.get("coordination_log", [])
            handoff = state.get("handoff_packet", {})
            user_prefs = handoff.get("user_preferences", {})

            if handoff:
                log.append("Executive Chef: handoff packet received; analyzing request")
                print(f"Executive Chef: Received preferences - {user_prefs}")

                # Analyze complexity and determine query type
                query_type = self.exec_chef.decide_query_type(user_prefs)
                log.append(f"Executive Chef: Query type determined as '{query_type}'")
                print(f"Executive Chef: Query type → {query_type}")

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
            return Command(update={})

        def exec_chef_check(state):
            log = state.get("coordination_log", [])

            log.append("Executive Chef: Performing final quality check")
            print("Executive Chef: Quality control in progress...")

            # Get all the data collected so far
            user_prefs = state.get("user_preferences", {})

            # Use Executive Chef to orchestrate and synthesize
            print("Executive Chef: Synthesizing final recommendation...")

            # Prepare agent responses for synthesis
            agent_responses = {
                "user_preferences": user_prefs
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
        workflow.add_node("executive_chef_review", exec_chef_review)
        workflow.add_node("sous_chef_prepare_recipe", sous_chef_handle)
        workflow.add_node("recipe_knowledge_retrieve", recipe_knowledge_agent)
        workflow.add_node("executive_chef_quality_check", exec_chef_check)
        workflow.add_node("return_to_user", waiter_return)


        # 2. Define edges
        # Routing from waiter_collect_info is controlled at runtime via Command.goto
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
