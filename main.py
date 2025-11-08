import os
import json
import asyncio
import threading
import tempfile
import traceback
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal, Annotated
import operator
from queue import Queue
from contextlib import contextmanager

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, add_messages
from langgraph.graph.message import AnyMessage
from langgraph.types import Command
from langgraph.cache.memory import InMemoryCache

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

# Initialize OpenAI client
llm = ChatOpenAI(
    model="gpt-5-nano",
    temperature=0.7,
    api_key=OPENAI_API_KEY
)

from agents.recipe_knowledge_agent import RecipeKnowledgeAgent
from agents.executive_chef_agent import ExecutiveChefAgent
from agents.pantry_agent import PantryAgent
from agents.sous_chef_agent import SousChefAgent
from utils.output_validator import ResultValidator


# ============================================
# WORKFLOW TRACING UTILITY
# ============================================

class WorkflowTracer:
    """Structured tracing and timing utility for LangGraph workflow nodes"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.trace_log = []

    @contextmanager
    def trace_node(self, node_name: str, stage: str = "", metadata: Dict[str, Any] = None):
        """
        Context manager for tracing node execution with timing.

        Usage:
            with tracer.trace_node("waiter_node", stage="presenting_options"):
                # node logic here
                pass
        """
        if not self.enabled:
            yield
            return

        start_time = time.time()
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Entry log
        entry_msg = f"[{timestamp}] ➡️  ENTER: {node_name}"
        if stage:
            entry_msg += f" (stage: {stage})"
        if metadata:
            entry_msg += f" | {metadata}"
        print(entry_msg)
        self.trace_log.append({
            "timestamp": timestamp,
            "event": "enter",
            "node": node_name,
            "stage": stage,
            "metadata": metadata
        })

        try:
            yield
        finally:
            # Exit log with timing
            elapsed = (time.time() - start_time) * 1000  # milliseconds
            exit_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            exit_msg = f"[{exit_timestamp}] ⬅️  EXIT:  {node_name} ({elapsed:.2f}ms)"
            print(exit_msg)
            self.trace_log.append({
                "timestamp": exit_timestamp,
                "event": "exit",
                "node": node_name,
                "stage": stage,
                "elapsed_ms": elapsed
            })

    def log_transition(self, from_node: str, to_node: str, reason: str = ""):
        """Log state transition between nodes"""
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = f"[{timestamp}] 🔄 TRANSITION: {from_node} → {to_node}"
        if reason:
            msg += f" | Reason: {reason}"
        print(msg)
        self.trace_log.append({
            "timestamp": timestamp,
            "event": "transition",
            "from": from_node,
            "to": to_node,
            "reason": reason
        })

    def log_state_change(self, node: str, key: str, value: Any):
        """Log important state changes"""
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        # Truncate value if too long
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:97] + "..."
        msg = f"[{timestamp}] 📝 STATE UPDATE [{node}]: {key} = {value_str}"
        print(msg)
        self.trace_log.append({
            "timestamp": timestamp,
            "event": "state_update",
            "node": node,
            "key": key,
            "value": value_str
        })

    def get_trace_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the workflow execution"""
        if not self.trace_log:
            return {}

        nodes_visited = set()
        total_time = 0
        node_timings = {}

        for entry in self.trace_log:
            if entry["event"] == "enter":
                nodes_visited.add(entry["node"])
            elif entry["event"] == "exit":
                elapsed = entry.get("elapsed_ms", 0)
                total_time += elapsed
                node = entry["node"]
                if node not in node_timings:
                    node_timings[node] = []
                node_timings[node].append(elapsed)

        return {
            "total_nodes_visited": len(nodes_visited),
            "total_time_ms": total_time,
            "node_timings": {node: sum(times) for node, times in node_timings.items()},
            "trace_entries": len(self.trace_log)
        }

    def export_trace(self, filepath: str):
        """Export trace log to JSON file"""
        with open(filepath, 'w') as f:
            json.dump({
                "trace_log": self.trace_log,
                "summary": self.get_trace_summary()
            }, f, indent=2)
        print(f"📊 Trace exported to: {filepath}")


# Global tracer instance
_global_tracer = WorkflowTracer(enabled=True)


# Modern collaborative state
class ModernCollaborativeState(MessagesState):
    user_preferences: Dict[str, Any]
    query_type: Optional[Literal["ingredient", "recipe", "pantry", "general"]]
    latest_user_message: Optional[str]

    # Workflow stage tracking
    current_workflow_stage: str  # "initial", "collecting", "orchestrating", "executing", "presenting_options", "adapting", "final_qa", "idle"

    # Executive Chef orchestration
    executive_chef_task_plan: Optional[Dict[str, Any]]  # EC's orchestration plan
    agent_delegation_results: Dict[str, Any]  # Results from delegated agents

    # Pantry-related fields
    pantry_inventory: List[Dict[str, Any]]
    expiring_items: List[Dict[str, Any]]
    pantry_summary: Dict[str, Any]
    recipe_feasibility: Optional[Dict[str, Any]]

    # Recipe and recommendation fields
    user_ingredients: List[str]  # pantry ingredients from user
    recipe_results: List[Dict[str, Any]]  # retrieved recipes
    sous_chef_recommendations: List[Dict[str, Any]]
    user_recipe_selection: Optional[int]  # User's choice (1, 2, or 3)
    selected_recipe_data: Optional[Dict[str, Any]]  # Full selected recipe
    adapted_recipe: Optional[Dict[str, Any]]  # Adapted recipe
    formatted_recipe: Optional[str]  # Final formatted recipe for user

    # Quality control (moved to Waiter)
    final_recommendation: Optional[str]
    waiter_quality_passed: bool
    waiter_quality_issues: List[str]

    # Use Annotated with operator.add to allow multiple updates per step
    coordination_log: Annotated[List[str], operator.add]

class ModernCollaborativeSystem:
    """collaborative system with enhanced orchestration"""

    def __init__(self, enable_tracing: bool = True):
        # Initialize tracer
        self.tracer = WorkflowTracer(enabled=enable_tracing)

        self.graph = self._create_modern_collaborative_graph()

        # Initialize Validator
        self.validator = ResultValidator()

        # Initialize Agents (ExecutiveChefAgent handles both orchestration and user interface)
        self.exec_chef = ExecutiveChefAgent(name="Maison D'Être")
        self.pantry = PantryAgent(name="Pantry Manager")

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

        # Wire pantry to recipe agent
        if self.recipe_agent:
            self.recipe_agent.set_pantry_agent(self.pantry)

        self.sous_chef = SousChefAgent(name="Sous Chef", recipe_knowledge_agent=self.recipe_agent)

    def _create_modern_collaborative_graph(self) -> StateGraph:
        """Create collaborative workflow with Command API"""
        workflow = StateGraph(ModernCollaborativeState)

        def waiter_node(state) -> Command[Literal["waiter_node", "executive_chef_orchestrate", "waiter_finalize", "sous_chat"]]:
            """
            User interaction node (powered by ExecutiveChefAgent's user interface methods).
            Handles conversation based on workflow stage:
            - Stage: initial/collecting - Greet, classify query, extract preferences
            - Stage: presenting_options - Display recipe recommendations
            - Stage: awaiting_selection - Collect user choice or questions
            """
            with self.tracer.trace_node("waiter_node", stage=state.get("current_workflow_stage", "initial"), 
                                       metadata={"query_type": state.get("query_type")}):
                log = state.get("coordination_log", [])
                stage = state.get("current_workflow_stage", "initial")
                messages = state.get("messages", [])
                current_prefs = state.get("user_preferences", {}) or {}
                latest = state.get("latest_user_message")

                # --- Stage: Initial Greeting ---
                if stage == "initial" and not latest:
                    intro = self.exec_chef.run_waiter(llm, context="general")
                    print(f"\n🎭 Maison D'Être: {intro}")
                    messages.append({"role": "assistant", "content": intro})
                    self.tracer.log_transition("waiter_node", "waiter_node", "Initial greeting complete")
                    return Command(
                        update={
                            "coordination_log": log,
                            "user_preferences": current_prefs,
                            "messages": messages,
                            "current_workflow_stage": "collecting"
                        },
                        goto="waiter_node"
                    )

                # --- Stage: Presenting Recommendations ---
                if stage == "presenting_options":
                    recommendations = state.get("sous_chef_recommendations", [])
                    if not recommendations:
                        print("\n❌ Waiter: No recommendations available")
                        self.tracer.log_transition("waiter_node", "waiter_finalize", "No recommendations available")
                        return Command(
                            update={
                                "coordination_log": log,
                                "current_workflow_stage": "idle"
                            },
                            goto="waiter_finalize"
                        )

                    # Validate recommendations before presenting
                    self.tracer.log_state_change("waiter_node", "validating", f"{len(recommendations)} recommendations")
                    validation = self.validator.validate_recommendations(recommendations, current_prefs)

                    if not validation["passed"]:
                        error_msg = "I apologize, I couldn't find safe recipes matching your requirements."
                        if validation["issues"]:
                            error_msg += f"\n\nIssues: {'; '.join(validation['issues'][:3])}"
                        print(f"\n⚠️ Waiter: {error_msg}")
                        messages.append({"role": "assistant", "content": error_msg})
                        self.tracer.log_transition("waiter_node", "waiter_finalize", "Validation failed")
                        return Command(
                            update={
                                "coordination_log": log,
                                "messages": messages,
                                "current_workflow_stage": "idle"
                            },
                            goto="waiter_finalize"
                        )

                    # Present validated recommendations
                    filtered_recs = validation["filtered_recommendations"]
                    self.tracer.log_state_change("waiter_node", "filtered_recommendations", len(filtered_recs))
                    presentation = self.sous_chef.present_recommendations(llm, filtered_recs)
                    print("\n" + "="*80)
                    print("🍽️  RECIPE RECOMMENDATIONS")
                    print("="*80 + "\n")
                    print(presentation)
                    print("\n" + "="*80)
                    print("\n💬 You can also ask questions about the recipes before choosing!")
                    print("   (e.g., 'What's the difference between 1 and 2?', 'Can I substitute ingredients?')\n")

                    messages.append({"role": "assistant", "content": presentation})
                    log.append("Waiter: Presented validated recipe recommendations to user")

                    # Wait for user selection or questions
                    self.tracer.log_transition("waiter_node", "waiter_node", "Awaiting user selection")
                    return Command(
                        update={
                            "coordination_log": log,
                            "messages": messages,
                            "sous_chef_recommendations": filtered_recs,  # Store filtered
                            "current_workflow_stage": "awaiting_selection"
                        },
                        goto="waiter_node"
                    )

                # --- Stage: User Selection Received ---
                if stage == "awaiting_selection" and latest:
                    messages.append({"role": "user", "content": latest})

                    # Check if it's a direct selection (1, 2, or 3)
                    try:
                        selection = int(latest.strip())
                        if 1 <= selection <= 3:
                            log.append(f"Waiter: User selected recipe #{selection}")
                            print(f"\n✅ Waiter: User selected recipe #{selection}")
                            self.tracer.log_state_change("waiter_node", "user_recipe_selection", selection)
                            self.tracer.log_transition("waiter_node", "executive_chef_orchestrate", f"Recipe #{selection} selected")
                            return Command(
                                update={
                                    "coordination_log": log,
                                    "user_recipe_selection": selection,
                                    "messages": messages,
                                    "current_workflow_stage": "adapting_recipe"
                                },
                                goto="executive_chef_orchestrate"
                            )
                        else:
                            error_msg = "Please enter 1, 2, or 3, or ask me a question about the recipes!"
                            print(f"\nWaiter: {error_msg}")
                            messages.append({"role": "assistant", "content": error_msg})
                            self.tracer.log_transition("waiter_node", "waiter_node", "Invalid selection")
                            return Command(
                                update={
                                    "coordination_log": log,
                                    "messages": messages
                                },
                                goto="waiter_node"
                            )
                    except ValueError:
                        # Not a number - could be a question, route to Sous Chef
                        log.append("Waiter: User has a question, routing to Sous Chef")
                        print(f"\n💬 Waiter: Connecting you with Sous Chef...")
                        self.tracer.log_transition("waiter_node", "sous_chat", "User has a question")
                        return Command(
                            update={
                                "coordination_log": log,
                                "messages": messages,
                                "current_workflow_stage": "sous_dialogue"
                            },
                            goto="sous_chat"
                        )

                # --- Update messages history for collecting stage ---
                if latest and stage in ["collecting", "initial"]:
                    messages.append({"role": "user", "content": latest})

                # --- Classify query using full chat history ---
                classification = self.exec_chef.classify_query(llm, messages)
                query_type = classification.get("query_type", "general")
                self.tracer.log_state_change("waiter_node", "query_type", query_type)
                log.append(f"Waiter: Classified query as '{query_type}'")

                # --- BEHAVIOR BRANCHES ---

                # 1) General queries - handle directly
                if query_type == "general":
                    res = self.exec_chef.respond_as_waiter(llm, latest)
                    print(f"\nWaiter: {res}")
                    messages.append({"role": "assistant", "content": res})
                    self.tracer.log_transition("waiter_node", "waiter_node", "Handled general query")
                    return Command(
                        update={
                            "coordination_log": log,
                            "user_preferences": current_prefs,
                            "query_type": query_type,
                            "messages": messages,
                            "current_workflow_stage": "idle"
                        },
                        goto="waiter_node"
                    )

                # 2) Pantry queries - delegate to Executive Chef
                if query_type == "pantry":
                    log.append("Waiter: Delegating pantry request to Executive Chef")
                    print("\nWaiter: Processing pantry request...")
                    self.tracer.log_transition("waiter_node", "executive_chef_orchestrate", "Delegating pantry query")
                    return Command(
                        update={
                            "coordination_log": log,
                            "query_type": query_type,
                            "messages": messages,
                            "current_workflow_stage": "orchestrating"
                        },
                        goto="executive_chef_orchestrate"
                    )

                # 3) Recipe queries - collect preferences
                if query_type == "recipe":
                    extracted = self.exec_chef.extract_preferences(llm, messages)
                    self.tracer.log_state_change("waiter_node", "extracted_preferences", extracted)

                    # Merge extracted preferences
                    def merge_list(key):
                        existing = list(current_prefs.get(key, []) or [])
                        incoming = list(extracted.get(key, []) or [])
                        return existing + [x for x in incoming if x not in existing]

                    current_prefs = {
                        "allergies": merge_list("allergies"),
                        "restrictions": merge_list("restrictions"),
                    }

                    # Check if minimum preferences collected
                    def _is_prefs_empty(prefs: dict) -> bool:
                        return not any(prefs.get(k) for k in ["allergies", "restrictions"])

                    if _is_prefs_empty(current_prefs):
                        missing_prompt = (
                            "I need some information to suggest safe recipes for you.\n"
                            "Could you please share any allergies or dietary restrictions you have?"
                        )
                        print(f"\nWaiter: {missing_prompt}")
                        messages.append({"role": "assistant", "content": missing_prompt})
                        self.tracer.log_transition("waiter_node", "waiter_node", "Collecting more preferences")
                        return Command(
                            update={
                                "coordination_log": log,
                                "user_preferences": current_prefs,
                                "query_type": query_type,
                                "messages": messages,
                                "current_workflow_stage": "collecting"
                            },
                            goto="waiter_node"
                        )

                    # Preferences complete - delegate to Executive Chef
                    log.append("Waiter: Recipe preferences collected, delegating to Executive Chef")
                    print("Waiter: Preferences collected! Finding recipes for you...")
                    self.tracer.log_state_change("waiter_node", "user_preferences", current_prefs)
                    self.tracer.log_transition("waiter_node", "executive_chef_orchestrate", "Preferences collected, delegating")
                    return Command(
                        update={
                            "coordination_log": log,
                            "user_preferences": current_prefs,
                            "query_type": query_type,
                            "messages": messages,
                            "current_workflow_stage": "orchestrating"
                        },
                        goto="executive_chef_orchestrate"
                    )

                # Safety fallback - go back to waiter
                self.tracer.log_transition("waiter_node", "waiter_node", "Fallback - unknown query type")
                return Command(
                    update={
                        "coordination_log": log,
                        "user_preferences": current_prefs,
                        "query_type": query_type,
                        "messages": messages,
                        "current_workflow_stage": "idle"
                    },
                    goto="waiter_node"
                )

        def executive_chef_orchestrate(state) -> Command[Literal["agent_execute", "waiter_node", "waiter_finalize"]]:
            """
            Orchestration node (powered by ExecutiveChefAgent's orchestration methods).
            Analyzes request complexity, creates task plans, delegates to agents, and synthesizes results.
            """
            with self.tracer.trace_node("executive_chef_orchestrate", 
                                       stage=state.get("current_workflow_stage"), 
                                       metadata={"query_type": state.get("query_type")}):
                log = state.get("coordination_log", [])
                stage = state.get("current_workflow_stage")
                query_type = state.get("query_type")
                user_prefs = state.get("user_preferences", {})
                latest_message = state.get("latest_user_message", "")

                log.append(f"Executive Chef: Orchestrating request - stage '{stage}', query '{query_type}'")
                print(f"\n👨‍🍳 Executive Chef: Orchestrating workflow...")

                # Stage 1: Initial orchestration - analyze complexity and create task plan
                if stage == "orchestrating":
                    print("   Analyzing request complexity...")

                    # FULL ORCHESTRATION: Analyze complexity for ALL requests
                    complexity = self.exec_chef.analyze_request_complexity(
                        llm, user_prefs, query_context=latest_message
                    )

                    self.tracer.log_state_change("executive_chef_orchestrate", "complexity", 
                                                complexity.get('complexity', 'unknown'))
                    log.append(f"Executive Chef: Complexity analysis complete - {complexity.get('complexity', 'unknown')}")
                    print(f"   Complexity: {complexity.get('complexity')} | Strategy: {complexity.get('strategy')}")

                    # Get pantry context - needed for both simple and complex cases
                    pantry_summary = self.pantry.get_pantry_summary()
                    pantry_context = {
                        'summary': pantry_summary,
                        'expiring': self.pantry.get_expiring_soon(days_threshold=3)
                    }

                    # Hybrid task plan storage
                    if complexity.get('complexity') == 'simple' and query_type == "pantry":
                        task_plan = {
                            'strategy': complexity.get('strategy', 'pantry'),
                            'complexity': 'simple',
                            'agents': complexity.get('required_agents', ['pantry']),
                            'query_type': query_type
                        }
                        log.append("Executive Chef: Created lightweight task plan for simple pantry operation")
                    else:
                        # Complex requests get full LLM-generated plan
                        print("   Creating detailed execution plan...")
                        task_plan = self.exec_chef.create_task_plan(
                            llm, user_prefs, complexity, pantry_context
                        )
                        self.tracer.log_state_change("executive_chef_orchestrate", "task_plan", 
                                                    f"{len(task_plan.get('tasks', []))} tasks")
                        log.append(f"Executive Chef: Created detailed task plan with {len(task_plan.get('tasks', []))} tasks")
                        print(f"   Plan: {len(task_plan.get('tasks', []))} tasks, {len(task_plan.get('delegation_order', []))} agents")

                    # Use delegation methods for proper tracking
                    if query_type == "pantry":
                        delegation = self.exec_chef.delegate_to_pantry(
                            "check_inventory",
                            {"user_message": latest_message, "preferences": user_prefs}
                        )
                        log.append(f"Executive Chef: Delegated to Pantry Agent - {delegation['action']}")
                        self.tracer.log_transition("executive_chef_orchestrate", "agent_execute", 
                                                  "Delegated to Pantry Agent")
                        return Command(
                            update={
                                "coordination_log": log,
                                "executive_chef_task_plan": task_plan,
                                "current_workflow_stage": "executing_pantry"
                            },
                            goto="agent_execute"
                        )

                    elif query_type == "recipe":
                        delegation = self.exec_chef.delegate_to_sous_chef(
                            "suggest_recipes",
                            {"pantry_context": pantry_context, "preferences": user_prefs}
                        )
                        log.append(f"Executive Chef: Delegated to Sous Chef - {delegation['action']}")
                        print("   Delegating to recipe search workflow...")
                        self.tracer.log_transition("executive_chef_orchestrate", "agent_execute", 
                                                  "Delegated to Sous Chef for recipe search")
                        return Command(
                            update={
                                "coordination_log": log,
                                "executive_chef_task_plan": task_plan,
                                "current_workflow_stage": "executing_recipe_search"
                            },
                            goto="agent_execute"
                        )

                # Stage 2: Synthesis of recipe recommendations
                elif stage == "synthesizing_recommendations":
                    log.append("Executive Chef: Synthesizing agent responses")
                    print("   Synthesizing multi-agent responses...")

                    agent_responses = state.get("agent_delegation_results", {})
                    task_plan = state.get("executive_chef_task_plan", {})
                    complexity = task_plan.get("complexity", "medium")

                    # Call synthesize_recommendations for medium/complex cases
                    if complexity in ["medium", "complex"]:
                        synthesis = self.exec_chef.synthesize_recommendations(
                            llm, agent_responses, user_prefs
                        )
                        self.tracer.log_state_change("executive_chef_orchestrate", "synthesis", "complete")
                        log.append("Executive Chef: Generated synthesis of agent recommendations")
                        print(f"   Synthesis complete - presenting to user")
                    else:
                        # Simple cases can skip synthesis
                        log.append("Executive Chef: Skipping synthesis for simple request")

                    self.tracer.log_transition("executive_chef_orchestrate", "waiter_node", 
                                              "Synthesis complete, presenting options")
                    return Command(
                        update={
                            "coordination_log": log,
                            "current_workflow_stage": "presenting_options"
                        },
                        goto="waiter_node"
                    )

                # Stage 3: After recipe search complete
                elif stage == "recipe_search_complete":
                    log.append("Executive Chef: Recipe search complete, routing to Waiter for presentation")
                    self.tracer.log_transition("executive_chef_orchestrate", "waiter_node", 
                                              "Recipe search complete")
                    return Command(
                        update={
                            "coordination_log": log,
                            "current_workflow_stage": "presenting_options"
                        },
                        goto="waiter_node"
                    )

                # Stage 4: User selected recipe, coordinate adaptation
                elif stage == "adapting_recipe":
                    delegation = self.exec_chef.delegate_to_sous_chef(
                        "adapt_recipe",
                        {"selection": state.get("user_recipe_selection"), "preferences": user_prefs}
                    )
                    log.append(f"Executive Chef: Delegated recipe adaptation - {delegation['action']}")
                    print("   Coordinating recipe adaptation...")
                    self.tracer.log_transition("executive_chef_orchestrate", "agent_execute", 
                                              f"Delegated recipe adaptation for #{state.get('user_recipe_selection')}")
                    return Command(
                        update={
                            "coordination_log": log,
                            "current_workflow_stage": "executing_adaptation"
                        },
                        goto="agent_execute"
                    )

                # Stage 5: Adaptation complete, final QA by Waiter
                elif stage == "adaptation_complete":
                    log.append("Executive Chef: Adaptation complete, routing to Waiter for final QA")
                    print("   Recipe adaptation complete - sending to Waiter for quality check")
                    self.tracer.log_transition("executive_chef_orchestrate", "waiter_finalize", 
                                              "Adaptation complete, final QA")
                    return Command(
                        update={
                            "coordination_log": log,
                            "current_workflow_stage": "final_qa"
                        },
                        goto="waiter_finalize"
                    )

                # Default: continue to agent_execute
                self.tracer.log_transition("executive_chef_orchestrate", "agent_execute", "Default fallback")
                return Command(
                    update={
                        "coordination_log": log
                    },
                    goto="agent_execute"
                )

        def agent_execute(state) -> Command[Literal["executive_chef_orchestrate", "waiter_finalize"]]:
            """
            Generic execution node that routes to appropriate agent based on workflow stage.
            """
            with self.tracer.trace_node("agent_execute", stage=state.get("current_workflow_stage")):
                log = state.get("coordination_log", [])
                stage = state.get("current_workflow_stage")
                user_prefs = state.get("user_preferences", {})
                messages = state.get("messages", [])

                # Execute pantry CRUD operation
                if stage == "executing_pantry":
                    log.append("Agent Execute: Pantry Agent handling request")
                    print("\n🗄️  Pantry Agent: Processing request...")

                    # For now, just acknowledge (TODO: implement actual pantry CRUD)
                    result_msg = "Pantry operation processed."
                    print(f"   {result_msg}")
                    self.tracer.log_state_change("agent_execute", "pantry_result", result_msg)
                    self.tracer.log_transition("agent_execute", "waiter_finalize", "Pantry operation complete")
                    return Command(
                        update={
                            "coordination_log": log,
                            "agent_delegation_results": {"pantry": {"message": result_msg}},
                            "current_workflow_stage": "pantry_complete"
                        },
                        goto="waiter_finalize"
                    )

                # Execute recipe search workflow
                elif stage == "executing_recipe_search":
                    log.append("Agent Execute: Pantry check + Sous Chef recommendations")
                    print("\n📊 Checking pantry...")

                    # Step 1: Pantry check
                    pantry_summary = self.pantry.get_pantry_summary()
                    expiring = self.pantry.get_expiring_soon(days_threshold=3)
                    inventory = self.pantry.get_inventory()
                    self.tracer.log_state_change("agent_execute", "pantry_inventory", 
                                                f"{pantry_summary['total_ingredients']} ingredients")
                    print(f"   {pantry_summary['total_ingredients']} ingredients, {len(expiring)} expiring soon")

                    # Step 2: Sous Chef generates recommendations (calls Recipe Knowledge Agent internally)
                    print("\n👨‍🍳 Sous Chef: Generating recommendations...")
                    recommendations = self.sous_chef.generate_recommendations(
                        llm=llm,
                        pantry_summary={"inventory": inventory, **pantry_summary},
                        user_preferences=user_prefs,
                        expiring_items=expiring,
                        recipe_results=None  # Sous Chef will fetch internally
                    )

                    if not recommendations:
                        log.append("Agent Execute: No recommendations generated")
                        print("❌ Unable to generate recommendations")
                        self.tracer.log_transition("agent_execute", "waiter_finalize", 
                                                  "No recommendations generated")
                        return Command(
                            update={
                                "coordination_log": log,
                                "current_workflow_stage": "idle"
                            },
                            goto="waiter_finalize"
                        )

                    self.tracer.log_state_change("agent_execute", "recommendations", 
                                                f"{len(recommendations)} generated")
                    log.append(f"Agent Execute: Generated {len(recommendations)} recommendations")

                    # Return to Executive Chef for synthesis instead of going directly to Waiter
                    self.tracer.log_transition("agent_execute", "executive_chef_orchestrate", 
                                              "Recipe search complete, sending for synthesis")
                    return Command(
                        update={
                            "coordination_log": log,
                            "pantry_inventory": inventory,
                            "expiring_items": expiring,
                            "pantry_summary": pantry_summary,
                            "sous_chef_recommendations": recommendations,
                            "recipe_results": [],  # Store for later if needed
                            "agent_delegation_results": {
                                "pantry": pantry_summary,
                                "sous_chef": recommendations,
                                "expiring_items": expiring
                            },
                            "current_workflow_stage": "synthesizing_recommendations"
                        },
                        goto="executive_chef_orchestrate"
                    )

                # Execute recipe adaptation
                elif stage == "executing_adaptation":
                    log.append("Agent Execute: Sous Chef adapting selected recipe")
                    print("\n🔧 Sous Chef: Adapting recipe...")

                    selection = state.get("user_recipe_selection")
                    recipe_results = state.get("recipe_results", [])
                    pantry_inventory = state.get("pantry_inventory", [])

                    if not selection:
                        log.append("Agent Execute: No selection found")
                        self.tracer.log_transition("agent_execute", "waiter_finalize", "No selection found")
                        return Command(
                            update={"coordination_log": log, "current_workflow_stage": "idle"},
                            goto="waiter_finalize"
                        )

                    # Cache recommendations if needed
                    if not self.sous_chef.current_recommendations:
                        cached = state.get("sous_chef_recommendations", [])
                        if cached:
                            self.sous_chef.current_recommendations = cached

                    # Handle selection and adapt
                    selected_recipe = self.sous_chef.handle_user_selection(selection, recipe_results)
                    if not selected_recipe:
                        log.append("Agent Execute: Invalid selection")
                        self.tracer.log_transition("agent_execute", "waiter_finalize", "Invalid selection")
                        return Command(
                            update={"coordination_log": log, "current_workflow_stage": "idle"},
                            goto="waiter_finalize"
                        )

                    self.tracer.log_state_change("agent_execute", "selected_recipe", 
                                                selected_recipe.get('title', 'Unknown'))
                    adapted_recipe = self.sous_chef.adapt_recipe(
                        llm=llm,
                        recipe=selected_recipe,
                        user_preferences=user_prefs,
                        pantry_inventory=pantry_inventory
                    )

                    formatted = self.sous_chef.format_recipe_for_user(adapted_recipe, user_prefs)
                    self.tracer.log_state_change("agent_execute", "adapted_recipe", "complete")
                    log.append("Agent Execute: Recipe adapted successfully")

                    self.tracer.log_transition("agent_execute", "executive_chef_orchestrate", 
                                              "Recipe adaptation complete")
                    return Command(
                        update={
                            "coordination_log": log,
                            "selected_recipe_data": selected_recipe,
                            "adapted_recipe": adapted_recipe,
                            "formatted_recipe": formatted,
                            "agent_delegation_results": {"adapted_recipe": adapted_recipe},
                            "current_workflow_stage": "adaptation_complete"
                        },
                        goto="executive_chef_orchestrate"
                    )

                # Default fallback
                self.tracer.log_transition("agent_execute", "waiter_finalize", "Default fallback - unknown stage")
                return Command(
                    update={
                        "coordination_log": log,
                        "current_workflow_stage": "idle"
                    },
                    goto="waiter_finalize"
                )

        def sous_chat(state) -> Command[Literal["waiter_node", "executive_chef_orchestrate"]]:
            """
            Sous Chef dialogue node - handles Q&A about recommendations.
            User can ask questions, compare recipes, request substitutions.
            """
            with self.tracer.trace_node("sous_chat", stage=state.get("current_workflow_stage")):
                log = state.get("coordination_log", [])
                stage = state.get("current_workflow_stage")
                latest = state.get("latest_user_message")
                messages = state.get("messages", [])
                recommendations = state.get("sous_chef_recommendations", [])
                user_prefs = state.get("user_preferences", {})

                if stage != "sous_dialogue":
                    # Safety fallback
                    self.tracer.log_transition("sous_chat", "waiter_node", "Safety fallback - wrong stage")
                    return Command(
                        update={"coordination_log": log, "current_workflow_stage": "awaiting_selection"},
                        goto="waiter_node"
                    )

                if not latest:
                    # No user message, go back to waiter
                    self.tracer.log_transition("sous_chat", "waiter_node", "No user message")
                    return Command(
                        update={"coordination_log": log, "current_workflow_stage": "awaiting_selection"},
                        goto="waiter_node"
                    )

                # Call Sous Chef conversation handler
                print(f"\n👨‍🍳 Sous Chef: Processing your question...")
                conversation_result = self.sous_chef.converse_about_recommendations(
                    llm=llm,
                    recommendations=recommendations,
                    user_message=latest,
                    user_preferences=user_prefs
                )

                reply = conversation_result["reply"]
                selection = conversation_result["selection"]

                # Display Sous Chef's response
                print(f"\n👨‍🍳 Sous Chef: {reply}\n")
                messages.append({"role": "assistant", "content": reply})
                log.append(f"Sous Chef: Responded to user question")

                # Check if user made a selection
                if selection:
                    log.append(f"Sous Chef: User selected recipe #{selection}")
                    print(f"✅ Selection confirmed: Recipe #{selection}")
                    self.tracer.log_state_change("sous_chat", "user_recipe_selection", selection)
                    self.tracer.log_transition("sous_chat", "executive_chef_orchestrate", 
                                              f"Recipe #{selection} selected via dialogue")
                    return Command(
                        update={
                            "coordination_log": log,
                            "messages": messages,
                            "user_recipe_selection": selection,
                            "current_workflow_stage": "adapting_recipe"
                        },
                        goto="executive_chef_orchestrate"
                    )
                else:
                    # Continue dialogue
                    log.append("Sous Chef: Awaiting user selection or further questions")
                    self.tracer.log_transition("sous_chat", "waiter_node", "Continuing dialogue")
                    return Command(
                        update={
                            "coordination_log": log,
                            "messages": messages,
                            "current_workflow_stage": "sous_dialogue"
                        },
                        goto="waiter_node"  # Return to waiter to get next input
                    )

        def waiter_finalize(state) -> Command:
            """
            Final presentation node (powered by ExecutiveChefAgent + Validator).
            Performs quality validation and presents final results to user.
            """
            with self.tracer.trace_node("waiter_finalize", stage=state.get("current_workflow_stage")):
                log = state.get("coordination_log", [])
                stage = state.get("current_workflow_stage")
                messages = state.get("messages", [])

                # Pantry operation complete
                if stage == "pantry_complete":
                    result = state.get("agent_delegation_results", {}).get("pantry", {})
                    response = f"✅ Pantry updated: {result.get('message', 'Operation complete')}"
                    print(f"\nWaiter: {response}")
                    messages.append({"role": "assistant", "content": response})
                    log.append("Waiter: Pantry operation presented to user")
                    self.tracer.log_state_change("waiter_finalize", "workflow_complete", "pantry_operation")
                    return Command(
                        update={
                            "coordination_log": log,
                            "messages": messages,
                            "current_workflow_stage": "idle"
                        }
                    )

                # Final QA and presentation using Validator
                elif stage == "final_qa":
                    formatted_recipe = state.get("formatted_recipe", "")
                    user_prefs = state.get("user_preferences", {})

                    if not formatted_recipe:
                        error_msg = "I apologize, I wasn't able to generate a recipe."
                        print(f"\nWaiter: {error_msg}")
                        messages.append({"role": "assistant", "content": error_msg})
                        log.append("Waiter: No recipe available")
                        self.tracer.log_state_change("waiter_finalize", "error", "no_recipe_available")
                        return Command(
                            update={
                                "coordination_log": log,
                                "messages": messages,
                                "current_workflow_stage": "idle"
                            }
                        )

                    # Use Validator for safety checks
                    self.tracer.log_state_change("waiter_finalize", "validating", "recipe_safety_check")
                    validation = self.validator.validate_adapted_recipe(
                        formatted_recipe, user_prefs, messages
                    )

                    log.append(f"Validator: Recipe validation - {'passed' if validation['passed'] else 'FAILED'}")
                    self.tracer.log_state_change("waiter_finalize", "validation_result", 
                                                "passed" if validation["passed"] else "failed")

                    validated_content = validation["content"]

                    # Display validated recipe
                    print("\n" + "="*80)
                    if validation["passed"]:
                        print("🍽️  MAISON D'ÊTRE - Your Recipe")
                    else:
                        print("🚨 MAISON D'ÊTRE - Recipe Safety Alert")
                    print("="*80 + "\n")
                    print(validated_content)
                    print("\n" + "="*80 + "\n")

                    messages.append({"role": "assistant", "content": validated_content})

                    return Command(
                        update={
                            "coordination_log": log,
                            "messages": messages,
                            "waiter_quality_passed": validation["passed"],
                            "waiter_quality_issues": validation.get("issues", []),
                            "current_workflow_stage": "idle"
                        }
                    )

                # Default case
                log.append("Waiter: Presenting status to user")
                print("\nWaiter: Request processed.")
                self.tracer.log_state_change("waiter_finalize", "workflow_complete", "default")
                return Command(
                    update={
                        "coordination_log": log,
                        "messages": messages,
                        "current_workflow_stage": "idle"
                    }
                )

        # Add nodes to workflow
        workflow.add_node("waiter_node", waiter_node)
        workflow.add_node("executive_chef_orchestrate", executive_chef_orchestrate)
        workflow.add_node("agent_execute", agent_execute)
        workflow.add_node("sous_chat", sous_chat)
        workflow.add_node("waiter_finalize", waiter_finalize)

        # Set entry and finish points
        workflow.set_entry_point("waiter_node")
        workflow.set_finish_point("waiter_finalize")

        # Compile workflow
        return workflow.compile(
            cache=InMemoryCache(),
            interrupt_before=["waiter_node"]  # Pause for user input
        )

    def seed_sample_pantry(self):
        """Add sample ingredients to pantry for testing."""
        from datetime import datetime, timedelta

        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        week_later = today + timedelta(days=7)

        sample_items = [
            {"name": "chicken breast", "quantity": 2, "unit": "lbs", "expiration": tomorrow.date().isoformat(), "category": "protein"},
            {"name": "spinach", "quantity": 1, "unit": "bunch", "expiration": tomorrow.date().isoformat(), "category": "vegetable"},
            {"name": "tomatoes", "quantity": 5, "unit": "pieces", "expiration": (today + timedelta(days=3)).date().isoformat(), "category": "vegetable"},
            {"name": "pasta", "quantity": 1, "unit": "lb", "expiration": week_later.date().isoformat(), "category": "grain"},
            {"name": "olive oil", "quantity": 16, "unit": "oz", "expiration": None, "category": "pantry"},
            {"name": "garlic", "quantity": 1, "unit": "bulb", "expiration": week_later.date().isoformat(), "category": "vegetable"},
            {"name": "onion", "quantity": 2, "unit": "pieces", "expiration": week_later.date().isoformat(), "category": "vegetable"},
            {"name": "parmesan cheese", "quantity": 8, "unit": "oz", "expiration": (today + timedelta(days=14)).date().isoformat(), "category": "dairy"},
            {"name": "eggs", "quantity": 12, "unit": "pieces", "expiration": (today + timedelta(days=10)).date().isoformat(), "category": "protein"},
            {"name": "milk", "quantity": 1, "unit": "quart", "expiration": (today + timedelta(days=4)).date().isoformat(), "category": "dairy"},
        ]

        for item in sample_items:
            self.pantry.add_or_update_ingredient(
                ingredient_name=item["name"],
                quantity=item["quantity"],
                unit=item["unit"],
                expiration_date=item["expiration"],
                category=item["category"]
            )

        print(f"✅ Seeded pantry with {len(sample_items)} sample ingredients")
        print(f"   {len(self.pantry.get_expiring_soon())} items expiring soon")

    async def run_hybrid(self, initial_user_message: Optional[str] = None):
        state = {
            "user_preferences": {},
            "query_type": None,
            "latest_user_message": initial_user_message,
            "messages": [],
            "current_workflow_stage": "initial",
            "executive_chef_task_plan": None,
            "agent_delegation_results": {},
            "coordination_log": [],

            # Pantry fields
            "pantry_inventory": [],
            "expiring_items": [],
            "pantry_summary": {},
            "recipe_feasibility": None,

            # Recipe fields
            "user_ingredients": [],
            "recipe_results": [],
            "sous_chef_recommendations": [],
            "user_recipe_selection": None,
            "selected_recipe_data": None,
            "adapted_recipe": None,
            "formatted_recipe": None,

            # Quality fields
            "final_recommendation": None,
            "waiter_quality_passed": False,
            "waiter_quality_issues": []
        }

        while True:
            state = await self.graph.ainvoke(state)

            # Check workflow stage
            stage = state.get("current_workflow_stage", "")

            if stage == "idle":
                # Get user input for next request
                user_text = input("\nYou: ")
                if user_text.strip().lower() in {"exit", "quit"}:
                    print("👋 Goodbye!")
                    break

                state["latest_user_message"] = user_text
                state["current_workflow_stage"] = "collecting"
            else:
                # Workflow still in progress, continue
                continue

    def process_chat_message(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        user_pantry: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
        recipe_recommendations: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response + state updates.
        This method handles all chat logic using the agents.

        Args:
            user_message: The user's message
            conversation_history: List of {role, content} messages
            user_pantry: Current pantry items
            user_preferences: Current user preferences
            recipe_recommendations: Current recipe recommendations (if any)

        Returns:
            Dictionary with:
            - bot_response: str - What the bot should say
            - should_trigger_workflow: bool - Whether to trigger a workflow
            - workflow_type: Optional[str] - Type of workflow to trigger
            - updated_pantry: List[Dict] - Updated pantry items
            - updated_preferences: Dict - Updated preferences
        """
        import re
        from langchain_core.messages import HumanMessage

        # Build messages for classification
        messages = conversation_history + [{"role": "user", "content": user_message}]

        # Classify the query using Executive Chef
        classification = self.exec_chef.classify_query(llm, messages)
        query_type = classification.get("query_type", "general")

        print(f"[ChatProcessor] Query type: {query_type}")

        # Handle general queries
        if query_type == "general":
            response = self.exec_chef.respond_as_waiter(llm, user_message)
            return {
                "bot_response": response,
                "should_trigger_workflow": False,
                "workflow_type": None,
                "updated_pantry": user_pantry,
                "updated_preferences": user_preferences
            }

        # Handle pantry operations
        if query_type == "pantry":
            # Extract ingredients using Executive Chef
            ingredients_data = self.exec_chef.extract_ingredients(llm, user_message)
            ingredients = ingredients_data.get("ingredients", [])

            if not ingredients:
                response = self.exec_chef.respond_as_waiter(llm, user_message, context="pantry")
                return {
                    "bot_response": response,
                    "should_trigger_workflow": False,
                    "workflow_type": None,
                    "updated_pantry": user_pantry,
                    "updated_preferences": user_preferences
                }

            # Add ingredients to pantry
            added_items = []
            updated_pantry = user_pantry.copy() if user_pantry else []

            for ing in ingredients:
                item_name = ing.get("name", "")
                raw_quantity = ing.get("quantity", 1)
                unit = ing.get("unit") or "pieces"

                if item_name:
                    name_clean = item_name.strip()
                    if not name_clean:
                        continue

                    try:
                        pantry_quantity = float(raw_quantity)
                        display_quantity = int(pantry_quantity) if pantry_quantity.is_integer() else round(pantry_quantity, 2)
                    except (TypeError, ValueError):
                        pantry_quantity = raw_quantity
                        display_quantity = raw_quantity

                    if isinstance(display_quantity, float):
                        display_quantity_str = f"{display_quantity:.2f}".rstrip("0").rstrip(".")
                    else:
                        display_quantity_str = str(display_quantity)

                    # Update or insert into pantry (case-insensitive)
                    updated = False
                    for stored_item in updated_pantry:
                        if stored_item["name"].strip().lower() == name_clean.lower():
                            stored_item["quantity"] = pantry_quantity
                            stored_item["unit"] = unit
                            updated = True
                            break

                    if not updated:
                        updated_pantry.append({
                            "name": name_clean,
                            "quantity": pantry_quantity,
                            "unit": unit
                        })

                    # Update pantry agent
                    self.pantry.add_or_update_ingredient(
                        ingredient_name=name_clean,
                        quantity=pantry_quantity,
                        unit=unit
                    )

                    added_items.append(f"{display_quantity_str} {unit} of {name_clean}")

            if added_items:
                items_text = ", ".join(added_items)
                response = f"Great! I've added {items_text} to your pantry. 🗄️\n\nWhat else would you like to add, or would you like to see what recipes you can make?"
            else:
                response = "I couldn't add those items. Could you try again?"

            return {
                "bot_response": response,
                "should_trigger_workflow": False,
                "workflow_type": None,
                "updated_pantry": updated_pantry,
                "updated_preferences": user_preferences
            }

        # Handle recipe queries
        if query_type == "recipe":
            # Extract preferences
            extracted = self.exec_chef.extract_preferences(llm, messages)

            # Merge preferences
            updated_prefs = user_preferences.copy()
            if extracted.get("allergies"):
                existing = list(updated_prefs.get("allergies", []))
                existing.extend(extracted["allergies"])
                updated_prefs["allergies"] = list(set(existing))
            if extracted.get("restrictions"):
                existing = list(updated_prefs.get("restrictions", []))
                existing.extend(extracted["restrictions"])
                updated_prefs["restrictions"] = list(set(existing))
            if extracted.get("cuisines"):
                existing = list(updated_prefs.get("cuisines", []))
                existing.extend(extracted["cuisines"])
                updated_prefs["cuisines"] = list(set(existing))
            if extracted.get("diet"):
                updated_prefs["diet"] = extracted["diet"]
            if extracted.get("skill"):
                updated_prefs["skill"] = extracted["skill"]

            # Check for recipe selection
            recipe_recommendations = recipe_recommendations or []
            if recipe_recommendations:
                # Check if user is selecting a recipe
                selection_match = re.search(r"(?:recipe|option|#)\s*(\d+)", user_message, re.IGNORECASE)
                if not selection_match:
                    if re.search(r"\b(make|take|choose|pick|go with|cook)\b", user_message, re.IGNORECASE):
                        selection_match = re.search(r"\b(\d{1,2})\b", user_message)

                if selection_match:
                    try:
                        recipe_num = int(selection_match.group(1))
                        if 1 <= recipe_num <= len(recipe_recommendations):
                            return {
                                "bot_response": f"Excellent choice! Let me prepare recipe #{recipe_num} for you... 👨‍🍳",
                                "should_trigger_workflow": True,
                                "workflow_type": "recipe_adapt",
                                "updated_pantry": user_pantry,
                                "updated_preferences": updated_prefs,
                                "user_recipe_selection": recipe_num
                            }
                        else:
                            return {
                                "bot_response": f"Please select a recipe number between 1 and {len(recipe_recommendations)}.",
                                "should_trigger_workflow": False,
                                "workflow_type": None,
                                "updated_pantry": user_pantry,
                                "updated_preferences": updated_prefs
                            }
                    except (TypeError, ValueError):
                        pass

            # Check if we should trigger recipe search
            has_basic_prefs = any([
                updated_prefs.get("allergies"),
                updated_prefs.get("restrictions"),
                updated_prefs.get("diet"),
                updated_prefs.get("cuisines")
            ])

            if not user_pantry:
                return {
                    "bot_response": "I don't see any ingredients in your pantry yet. Tell me what you have! For example: 'I got 3 apples and some chicken'",
                    "should_trigger_workflow": False,
                    "workflow_type": None,
                    "updated_pantry": user_pantry,
                    "updated_preferences": updated_prefs
                }

            if not has_basic_prefs:
                response = self.exec_chef.respond_as_waiter(llm, user_message)
                return {
                    "bot_response": response,
                    "should_trigger_workflow": False,
                    "workflow_type": None,
                    "updated_pantry": user_pantry,
                    "updated_preferences": updated_prefs
                }

            # Ready to search for recipes
            return {
                "bot_response": f"Perfect! Let me search for recipes using your {len(user_pantry)} pantry items... 🔍",
                "should_trigger_workflow": True,
                "workflow_type": "recipe_search",
                "updated_pantry": user_pantry,
                "updated_preferences": updated_prefs
            }

        # Fallback
        response = self.exec_chef.respond_as_waiter(llm, user_message)
        return {
            "bot_response": response,
            "should_trigger_workflow": False,
            "workflow_type": None,
            "updated_pantry": user_pantry,
            "updated_preferences": user_preferences
        }

    async def run_workflow(
        self,
        initial_state: Dict[str, Any],
        workflow_type: str = "recipe_search",
        graph_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Public method to run workflows - can be called from Streamlit or other interfaces.

        Args:
            initial_state: Initial state dictionary with user_preferences, user_ingredients, etc.
            workflow_type: Type of workflow ("recipe_search", "recipe_adapt", etc.)
            graph_config: Optional graph configuration (e.g., interrupt points)

        Returns:
            Result dictionary with recommendations, formatted_recipe, etc.
        """
        try:
            print("\n" + "="*80)
            print(f"STARTING WORKFLOW - {workflow_type.upper()}")
            print("="*80)
            print(f"User preferences: {initial_state.get('user_preferences')}")
            print(f"User ingredients: {initial_state.get('user_ingredients')}")
            print("="*80 + "\n")

            # and go directly to orchestration for programmatic workflows
            if workflow_type == "recipe_search":
                # Set workflow stage to orchestrating (skips waiter greeting)
                initial_state["current_workflow_stage"] = "orchestrating"
                initial_state["query_type"] = "recipe"  # Fixed: was "ingredient", should be "recipe"
                initial_state["latest_user_message"] = "find recipes with my ingredients"
                print("🔧 Configured for direct recipe search workflow")
                
            elif workflow_type == "recipe_adapt":
                initial_state["current_workflow_stage"] = "adapting_recipe"
                initial_state["query_type"] = "recipe"
                print("🔧 Configured for recipe adaptation workflow")
                
            elif workflow_type == "pantry_workflow":
                initial_state["current_workflow_stage"] = "orchestrating"
                initial_state["query_type"] = "pantry"
                initial_state["latest_user_message"] = "check my pantry"
                print("🔧 Configured for pantry workflow")

            # Ensure coordination_log exists
            if "coordination_log" not in initial_state:
                initial_state["coordination_log"] = []

            # For programmatic workflows, create a temporary graph without interrupts
            from langgraph.graph import StateGraph
            temp_workflow = StateGraph(ModernCollaborativeState)
            
            # Get the actual node callables from the compiled graph
            # We need to recreate the nodes since we can't extract them easily
            # Instead, let's just manually execute the workflow logic
            config = dict(graph_config or {})
            
            print(f"📊 Initial stage: {initial_state.get('current_workflow_stage')}")
            print(f"🎯 Query type: {initial_state.get('query_type')}\n")

            # Manual execution loop to bypass interrupts
            state = initial_state
            max_steps = 20
            step = 0
            
            while step < max_steps:
                stage = state.get("current_workflow_stage")
                print(f"  Step {step + 1}: stage='{stage}'")
                
                # Determine which node to execute based on stage
                if stage == "orchestrating":
                    # Call executive_chef_orchestrate logic directly
                    # For now, manually transition to executing_recipe_search
                    from langgraph.types import Command
                    
                    # Simulate what executive_chef would do
                    log = state.get("coordination_log", [])
                    log.append("Manual: Entering orchestration")
                    
                    # Get pantry context
                    pantry_summary = self.pantry.get_pantry_summary()
                    pantry_context = {
                        'summary': pantry_summary,
                        'expiring': self.pantry.get_expiring_soon(days_threshold=3)
                    }
                    
                    state["pantry_summary"] = pantry_summary
                    state["coordination_log"] = log
                    state["current_workflow_stage"] = "executing_recipe_search"
                    step += 1
                    
                elif stage == "executing_recipe_search":
                    # Execute recipe search
                    print("\n📊 Checking pantry...")
                    pantry_summary = self.pantry.get_pantry_summary()
                    expiring = self.pantry.get_expiring_soon(days_threshold=3)
                    inventory = self.pantry.get_inventory()
                    
                    print(f"   {pantry_summary['total_ingredients']} ingredients, {len(expiring)} expiring soon")
                    
                    # Step 2: Sous Chef generates recommendations
                    print("\n👨‍🍳 Sous Chef: Generating recommendations...")
                    recommendations = self.sous_chef.generate_recommendations(
                        llm=llm,
                        pantry_summary={"inventory": inventory, **pantry_summary},
                        user_preferences=state.get("user_preferences", {}),
                        expiring_items=expiring,
                        recipe_results=None
                    )
                    
                    state["sous_chef_recommendations"] = recommendations
                    state["pantry_inventory"] = inventory
                    state["current_workflow_stage"] = "synthesizing_recommendations"
                    step += 1
                    
                elif stage == "synthesizing_recommendations":
                    state["current_workflow_stage"] = "presenting_options"
                    step += 1
                    
                elif stage in ["presenting_options", "idle"]:
                    # Done
                    break
                else:
                    # Unknown stage
                    print(f"  Unknown stage: {stage}, stopping")
                    break
            
            print(f"\n  Completed after {step} steps")

            # Handle interrupts if needed (for user selection during workflow)
            while (
                state.get("_interrupt") == "wait_for_user_selection"
                and state.get("user_recipe_selection")
            ):
                print("Auto-resuming workflow after applying recipe selection")
                resume_config = dict(config)
                resume_config_configurable = dict(resume_config.get("configurable") or {})
                resume_config_configurable["resume"] = True
                resume_config["configurable"] = resume_config_configurable
                state = await self.graph.ainvoke(state, config=resume_config)

            print("\n" + "="*80)
            print("WORKFLOW EXECUTION COMPLETE")
            print("="*80)
            print(f"Recommendations: {len(state.get('sous_chef_recommendations', []))}")
            print(f"Final stage: {state.get('current_workflow_stage')}")
            print("="*80 + "\n")

            # Return results
            return {
                "recommendations": state.get("sous_chef_recommendations", []),
                "recipe_results": state.get("recipe_results", []),
                "formatted_recipe": state.get("formatted_recipe"),
                "final_state": state,
                "complete": True,
                "workflow_type": workflow_type,
                "coordination_log": state.get("coordination_log", [])
            }

        except Exception as e:
            stack_trace = traceback.format_exc()
            print("=" * 80)
            print("WORKFLOW ERROR")
            print("=" * 80)
            print(stack_trace)
            print("=" * 80)
            return {
                "error": str(e),
                "stack_trace": stack_trace,
                "complete": False,
                "workflow_type": workflow_type
            }


# ============================================
# THREAD-SAFE LOGGING FOR STREAMLIT
# ============================================

log_queue = Queue()

def add_log(message: str, agent: str = "System", level: str = "INFO"):
    """Add a log entry with timestamp (thread-safe)"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_entry = {
        "timestamp": timestamp,
        "agent": agent,
        "level": level,
        "message": message
    }
    log_queue.put(log_entry)
    print(f"[{timestamp}] {agent} - {level}: {message}")


def process_queued_log_updates(logs_list: List[Dict]) -> List[Dict]:
    """Process queued log updates from background thread and return updated logs"""
    updated_logs = logs_list.copy() if logs_list else []
    while not log_queue.empty():
        try:
            log_entry = log_queue.get_nowait()
            updated_logs.append(log_entry)
        except:
            break
    return updated_logs


# ============================================
# STREAMLIT WORKFLOW HELPERS
# ============================================

async def run_workflow_async(
    initial_state: Dict[str, Any],
    system_instance: ModernCollaborativeSystem,
    workflow_type: str,
    graph_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run workflow asynchronously - wrapper for Streamlit threading.

    Args:
        initial_state: Initial state dictionary
        system_instance: ModernCollaborativeSystem instance
        workflow_type: Type of workflow to run
        graph_config: Optional graph configuration

    Returns:
        Result dictionary
    """
    try:
        add_log(f"Starting {workflow_type} workflow", "System", "INFO")

        result = await system_instance.run_workflow(initial_state, workflow_type, graph_config)

        # Process coordination log
        coord_log = result.get("coordination_log", [])
        for log_entry in coord_log:
            if ":" in log_entry:
                parts = log_entry.split(":", 1)
                agent = parts[0].strip()
                message = parts[1].strip()
                add_log(message, agent, "INFO")

        if result.get("complete"):
            add_log(f"{workflow_type} workflow completed successfully", "System", "INFO")
        else:
            add_log(f"{workflow_type} workflow failed: {result.get('error')}", "System", "ERROR")

        return result

    except Exception as e:
        add_log(f"Workflow error: {str(e)}", "System", "ERROR")
        stack_trace = traceback.format_exc()
        add_log(f"Full stack trace:\n{stack_trace}", "System", "DEBUG")
        return {"error": str(e), "stack_trace": stack_trace, "complete": False}


def run_workflow_threaded(
    initial_state: Dict[str, Any],
    system_instance: ModernCollaborativeSystem,
    workflow_type: str,
    graph_config: Optional[Dict[str, Any]] = None
):
    """
    Run workflow in a background thread for Streamlit.
    Results are stored in a temp file for retrieval.

    Args:
        initial_state: Initial state dictionary
        system_instance: ModernCollaborativeSystem instance
        workflow_type: Type of workflow to run
        graph_config: Optional graph configuration
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            run_workflow_async(initial_state, system_instance, workflow_type, graph_config)
        )
        # Store result in a temp file
        result_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump({
            "recommendations": result.get("recommendations", []),
            "recipe_results": result.get("recipe_results", []),
            "formatted_recipe": result.get("formatted_recipe"),
            "complete": result.get("complete", False),
            "error": result.get("error"),
            "workflow_type": result.get("workflow_type")
        }, result_file)
        result_file.close()
        # Store path
        with open('/tmp/leftovr_result_path.txt', 'w') as f:
            f.write(result_file.name)
    finally:
        loop.close()


async def test_conversation():
    """
    Test conversation: User adds butter, then asks for recipe recommendations
    """
    print("\n" + "="*80)
    print("TEST CONVERSATION")
    print("="*80 + "\n")
    
    system = ModernCollaborativeSystem(enable_tracing=True)
    
    print("👤 User Message 1: i have 250g butter")
    print("-" * 80)
    
    # Use process_chat_message to handle first message
    result1 = system.process_chat_message(
        user_message="i have 250g butter",
        conversation_history=[],
        user_pantry=[],
        user_preferences={}
    )
    
    print(f"\n🤖 Bot Response: {result1['bot_response']}")
    print(f"📦 Updated pantry: {result1['updated_pantry']}")
    print(f"🔄 Trigger workflow: {result1['should_trigger_workflow']}")
    
    print("\n" + "="*80)
    print("👤 User Message 2: what recipe can i make, i'm vegetarian")
    print("-" * 80)
    
    # Use process_chat_message to handle second message with dietary info
    result2 = system.process_chat_message(
        user_message="what recipe can i make, i'm vegetarian",
        conversation_history=[
            {"role": "user", "content": "i have 250g butter"},
            {"role": "assistant", "content": result1['bot_response']}
        ],
        user_pantry=result1['updated_pantry'],
        user_preferences=result1['updated_preferences']
    )
    
    print(f"\n🤖 Bot Response: {result2['bot_response']}")
    print(f"🔄 Trigger workflow: {result2['should_trigger_workflow']}")
    print(f"📋 Workflow type: {result2.get('workflow_type')}")
    
    # If workflow should be triggered, run it
    if result2['should_trigger_workflow']:
        print("\n" + "="*80)
        print("RUNNING WORKFLOW")
        print("="*80 + "\n")
        
        initial_state = {
            "user_preferences": result2['updated_preferences'],
            "user_ingredients": [item['name'] for item in result2['updated_pantry']],
            "query_type": None,
            "latest_user_message": None,
            "messages": [],
            "current_workflow_stage": "initial",
            "executive_chef_task_plan": None,
            "agent_delegation_results": {},
            "coordination_log": [],
            "pantry_inventory": result2['updated_pantry'],
            "expiring_items": [],
            "pantry_summary": {},
            "recipe_feasibility": None,
            "recipe_results": [],
            "sous_chef_recommendations": [],
            "user_recipe_selection": None,
            "selected_recipe_data": None,
            "adapted_recipe": None,
            "formatted_recipe": None,
            "final_recommendation": None,
            "waiter_quality_passed": False,
            "waiter_quality_issues": []
        }
        
        workflow_result = await system.run_workflow(
            initial_state=initial_state,
            workflow_type=result2['workflow_type']
        )
        
        print("\n" + "="*80)
        print("WORKFLOW RESULTS")
        print("="*80)
        print(f"Complete: {workflow_result['complete']}")
        print(f"Recommendations: {len(workflow_result.get('recommendations', []))}")
        if workflow_result.get('error'):
            print(f"Error: {workflow_result['error']}")
    
    # Print trace summary
    print("\n" + "="*80)
    print("TRACE SUMMARY")
    print("="*80)
    trace_summary = system.tracer.get_trace_summary()
    print(f"Total nodes visited: {trace_summary.get('total_nodes_visited', 0)}")
    print(f"Total time: {trace_summary.get('total_time_ms', 0):.2f}ms")
    print(f"Node timings:")
    for node, timing in trace_summary.get('node_timings', {}).items():
        print(f"  - {node}: {timing:.2f}ms")
    print(f"Trace entries: {len(system.tracer.trace_log)}")
    print("="*80 + "\n")
    
    # Show first few trace entries
    print("First 10 trace entries:")
    for i, entry in enumerate(system.tracer.trace_log[:10]):
        print(f"  {i+1}. [{entry['timestamp']}] {entry['event']}: {entry.get('node', 'N/A')}")
    
    # Export trace
    system.tracer.export_trace("test_conversation_trace.json")


if __name__ == "__main__":
    # Run test conversation
    asyncio.run(test_conversation())
