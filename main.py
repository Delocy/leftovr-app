import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Literal, Annotated
import json
import operator
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, add_messages
from langgraph.graph.message import AnyMessage
from langgraph.types import Command

from langgraph.cache.memory import InMemoryCache
import asyncio

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")

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

    def __init__(self):
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
                    return Command(
                        update={
                            "coordination_log": log,
                            "current_workflow_stage": "idle"
                        },
                        goto="waiter_finalize"
                    )

                # Validate recommendations before presenting
                validation = self.validator.validate_recommendations(recommendations, current_prefs)

                if not validation["passed"]:
                    error_msg = "I apologize, I couldn't find safe recipes matching your requirements."
                    if validation["issues"]:
                        error_msg += f"\n\nIssues: {'; '.join(validation['issues'][:3])}"
                    print(f"\n⚠️ Waiter: {error_msg}")
                    messages.append({"role": "assistant", "content": error_msg})
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
            log.append(f"Waiter: Classified query as '{query_type}'")

            # --- BEHAVIOR BRANCHES ---

            # 1) General queries - handle directly
            if query_type == "general":
                res = self.exec_chef.respond_as_waiter(llm, latest)
                print(f"\nWaiter: {res}")
                messages.append({"role": "assistant", "content": res})
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

                log.append(f"Executive Chef: Complexity analysis complete - {complexity.get('complexity', 'unknown')}")
                print(f"   Complexity: {complexity.get('complexity')} | Strategy: {complexity.get('strategy')}")

                # Hybrid task plan storage
                if complexity.get('complexity') == 'simple' and query_type == "pantry":
                    # Simple pantry operations get lightweight plan
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
                    pantry_summary = self.pantry.get_pantry_summary()
                    pantry_context = {
                        'summary': pantry_summary,
                        'expiring': self.pantry.get_expiring_soon(days_threshold=3)
                    }

                    task_plan = self.exec_chef.create_task_plan(
                        llm, user_prefs, complexity, pantry_context
                    )
                    log.append(f"Executive Chef: Created detailed task plan with {len(task_plan.get('tasks', []))} tasks")
                    print(f"   Plan: {len(task_plan.get('tasks', []))} tasks, {len(task_plan.get('delegation_order', []))} agents")

                # Use delegation methods for proper tracking
                if query_type == "pantry":
                    delegation = self.exec_chef.delegate_to_pantry(
                        "check_inventory",
                        {"user_message": latest_message, "preferences": user_prefs}
                    )
                    log.append(f"Executive Chef: Delegated to Pantry Agent - {delegation['action']}")

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
                    log.append("Executive Chef: Generated synthesis of agent recommendations")
                    print(f"   Synthesis complete - presenting to user")
                else:
                    # Simple cases can skip synthesis
                    log.append("Executive Chef: Skipping synthesis for simple request")

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

                return Command(
                    update={
                        "coordination_log": log,
                        "current_workflow_stage": "final_qa"
                    },
                    goto="waiter_finalize"
                )

            # Default: continue to agent_execute
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
                    return Command(
                        update={
                            "coordination_log": log,
                            "current_workflow_stage": "idle"
                        },
                        goto="waiter_finalize"
                    )

                log.append(f"Agent Execute: Generated {len(recommendations)} recommendations")

                # Return to Executive Chef for synthesis instead of going directly to Waiter
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
                    return Command(
                        update={"coordination_log": log, "current_workflow_stage": "idle"},
                        goto="waiter_finalize"
                    )

                adapted_recipe = self.sous_chef.adapt_recipe(
                    llm=llm,
                    recipe=selected_recipe,
                    user_preferences=user_prefs,
                    pantry_inventory=pantry_inventory
                )

                formatted = self.sous_chef.format_recipe_for_user(adapted_recipe, user_prefs)

                log.append("Agent Execute: Recipe adapted successfully")

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
            log = state.get("coordination_log", [])
            stage = state.get("current_workflow_stage")
            latest = state.get("latest_user_message")
            messages = state.get("messages", [])
            recommendations = state.get("sous_chef_recommendations", [])
            user_prefs = state.get("user_preferences", {})

            if stage != "sous_dialogue":
                # Safety fallback
                return Command(
                    update={"coordination_log": log, "current_workflow_stage": "awaiting_selection"},
                    goto="waiter_node"
                )

            if not latest:
                # No user message, go back to waiter
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
                    return Command(
                        update={
                            "coordination_log": log,
                            "messages": messages,
                            "current_workflow_stage": "idle"
                        }
                    )

                # Use Validator for safety checks
                validation = self.validator.validate_adapted_recipe(
                    formatted_recipe, user_prefs, messages
                )

                log.append(f"Validator: Recipe validation - {'passed' if validation['passed'] else 'FAILED'}")

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

if __name__ == "__main__":
    system = ModernCollaborativeSystem()

    # Seed sample pantry data for testing
    print("\n🌱 Seeding sample pantry data...")
    system.seed_sample_pantry()
    print()

    asyncio.run(system.run_hybrid())

