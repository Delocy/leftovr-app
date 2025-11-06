import os
import re
import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

from main import (
    ModernCollaborativeSystem,
    llm,
    run_workflow_threaded,
    process_queued_log_updates
)

load_dotenv()

st.set_page_config(
    page_title="Leftovr - Recipe Chatbot",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        max-width: 80%;
    }
    .user-message {
        background-color: #E3F2FD;
        margin-left: auto;
        text-align: right;
    }
    .bot-message {
        background-color: #F5F5F5;
        margin-right: auto;
    }
    .ingredient-badge {
        display: inline-block;
        padding: 0.3rem 0.6rem;
        margin: 0.2rem;
        background-color: #4ECDC4;
        color: white;
        border-radius: 1rem;
        font-size: 0.85rem;
    }
    .pref-badge {
        display: inline-block;
        padding: 0.3rem 0.6rem;
        margin: 0.2rem;
        background-color: #FFD93D;
        color: #333;
        border-radius: 1rem;
        font-size: 0.85rem;
    }
    .recipe-card {
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
    }
    .stTextInput input {
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

class ChatbotOrchestrator:
    """
    Thin orchestrator that handles:
    1. Guardrails (cooking-related filtering)
    2. Conversation memory
    3. Delegates ALL logic to ModernCollaborativeSystem.process_chat_message()
    """

    def __init__(self, system):
        self.system = system
        self.conversation_history = []  # Maintain conversation memory

    def is_cooking_related(self, message: str, llm) -> bool:
        """Guardrail: Check if message is cooking/recipe related"""
        system_prompt = """You are a classifier that determines if a user message is related to cooking, recipes, food, or ingredients.

Return ONLY valid JSON:
{
    "is_cooking_related": true/false,
    "reason": "brief explanation"
}

Examples:
- "i got 3 apples" → {"is_cooking_related": true, "reason": "ingredients"}
- "what's the weather?" → {"is_cooking_related": false, "reason": "weather question"}
- "I'm allergic to nuts" → {"is_cooking_related": true, "reason": "dietary preference"}
- "tell me a joke" → {"is_cooking_related": false, "reason": "unrelated request"}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User message: {message}")
        ]

        try:
            response = llm.invoke(messages)
            response_text = response.content.strip()

            if response_text.startswith("```"):
                parts = response_text.split("```")
                if len(parts) >= 2:
                    response_text = parts[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                response_text = response_text.strip()

            parsed = json.loads(response_text)
            return parsed.get("is_cooking_related", True)  # Default to true to be permissive
        except Exception as e:
            print(f"Error checking cooking relevance: {e}")
            return True  # Default to permissive

    def process_message(
        self,
        message: str,
        llm,
        user_pantry: list[Dict],
        user_preferences: Dict,
        recipe_recommendations: list[Dict]
    ) -> Dict[str, Any]:
        """
        Process user message with guardrails and conversation memory.
        Delegates ALL logic to ModernCollaborativeSystem.process_chat_message()

        Guardrails:
        - Filters out non-cooking related questions
        - Maintains conversation history

        Returns:
            Dict with bot_response, should_trigger_workflow, workflow_type, updated_pantry, updated_preferences
        """
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})

        # Guardrail: Check if cooking-related
        if not self.is_cooking_related(message, llm):
            response = "I'm a recipe and cooking assistant! I can help you with ingredients, recipes, dietary preferences, and cooking questions. Is there anything food-related I can help you with?"
            self.conversation_history.append({"role": "assistant", "content": response})
            return {
                "bot_response": response,
                "should_trigger_workflow": False,
                "workflow_type": None,
                "updated_pantry": user_pantry,
                "updated_preferences": user_preferences
            }

        # Delegate to ModernCollaborativeSystem for ALL logic
        result = self.system.process_chat_message(
            user_message=message,
            conversation_history=self.conversation_history.copy(),
            user_pantry=user_pantry,
            user_preferences=user_preferences,
            recipe_recommendations=recipe_recommendations
        )

        # Add bot response to conversation history
        self.conversation_history.append({"role": "assistant", "content": result["bot_response"]})

        return result


# ============================================
# SESSION STATE INITIALIZATION
# ============================================

def init_session_state():
    """Initialize all session state variables"""
    if 'system' not in st.session_state:
        st.session_state.system = None
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'logs' not in st.session_state:
        st.session_state.logs = []

    # User pantry and preferences
    if 'user_pantry' not in st.session_state:
        st.session_state.user_pantry = []
    if 'user_cuisines' not in st.session_state:
        st.session_state.user_cuisines = []
    if 'user_allergies' not in st.session_state:
        st.session_state.user_allergies = []
    if 'user_difficulty' not in st.session_state:
        st.session_state.user_difficulty = "intermediate"
    if 'user_diet' not in st.session_state:
        st.session_state.user_diet = "omnivore"

    # Recipe workflow state
    if 'recipe_recommendations' not in st.session_state:
        st.session_state.recipe_recommendations = []
    if 'recipe_results' not in st.session_state:
        st.session_state.recipe_results = []
    if 'user_recipe_selection' not in st.session_state:
        st.session_state.user_recipe_selection = None
    if 'adapted_recipe' not in st.session_state:
        st.session_state.adapted_recipe = None
    if 'workflow_running' not in st.session_state:
        st.session_state.workflow_running = False
    if 'workflow_complete' not in st.session_state:
        st.session_state.workflow_complete = False
    if 'final_state' not in st.session_state:
        st.session_state.final_state = None

    # Google Sheets integration
    if 'google_sheets_id' not in st.session_state:
        st.session_state.google_sheets_id = os.getenv("GOOGLE_SHEETS_ID")

init_session_state()


# ============================================
# INITIALIZE SYSTEM
# ============================================

if st.session_state.system is None:
    with st.spinner("🔧 Initializing AI agents..."):
        try:
            st.session_state.system = ModernCollaborativeSystem()
            st.session_state.chatbot = ChatbotOrchestrator(
                system=st.session_state.system
            )

            if not st.session_state.chat_history:
                try:
                    greeting = st.session_state.system.exec_chef.run_waiter(llm)
                except Exception:
                    greeting = "Hi there! I'm your culinary assistant."
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": greeting,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            st.error(f"❌ Failed to initialize system: {str(e)}")


# ============================================
# UI LAYOUT
# ============================================

st.title("🍽️ Leftovr - Your AI Recipe Assistant")
st.markdown("**Chat naturally to add ingredients, set preferences, and get personalized recipes**")

# Create two columns: main chat + sidebar info
col_chat, col_sidebar = st.columns([3, 1])

with col_sidebar:
    st.subheader("📊 Your Profile")

    # Display current pantry
    if st.session_state.user_pantry:
        st.markdown("**🗄️ Pantry:**")
        for item in st.session_state.user_pantry:
            qty_value = item["quantity"]
            if isinstance(qty_value, float):
                qty_display = f"{qty_value:.2f}".rstrip("0").rstrip(".")
            else:
                qty_display = str(qty_value)
            st.markdown(f'<span class="ingredient-badge">{qty_display} {item["unit"]} {item["name"]}</span>', unsafe_allow_html=True)
    else:
        st.info("No ingredients yet. Try: 'I got 3 apples'")

    st.divider()

    # Display preferences
    st.markdown("**👤 Preferences:**")
    if st.session_state.user_diet != "omnivore":
        st.markdown(f'<span class="pref-badge">Diet: {st.session_state.user_diet}</span>', unsafe_allow_html=True)
    if st.session_state.user_allergies:
        for allergy in st.session_state.user_allergies:
            st.markdown(f'<span class="pref-badge">No {allergy}</span>', unsafe_allow_html=True)
    if st.session_state.user_cuisines:
        for cuisine in st.session_state.user_cuisines:
            st.markdown(f'<span class="pref-badge">{cuisine}</span>', unsafe_allow_html=True)
    if st.session_state.user_difficulty != "intermediate":
        st.markdown(f'<span class="pref-badge">{st.session_state.user_difficulty}</span>', unsafe_allow_html=True)

    st.divider()

    # Status
    if st.session_state.workflow_running:
        st.info("🔄 Searching for recipes...")
    elif st.session_state.recipe_recommendations:
        st.success(f"✅ {len(st.session_state.recipe_recommendations)} recipes found!")

    st.divider()

    # Google Sheets Configuration
    with st.expander("⚙️ Settings"):
        st.markdown("**Google Sheets Integration**")
        current_sheets_id = st.session_state.get("google_sheets_id", "")
        sheets_id_input = st.text_input(
            "Spreadsheet ID",
            value=current_sheets_id or "",
            placeholder="Enter your Google Sheets ID",
            help="Your ingredients will be synced to this Google Sheet"
        )

        if sheets_id_input != current_sheets_id:
            st.session_state.google_sheets_id = sheets_id_input
            if sheets_id_input:
                st.success("✅ Google Sheets ID saved!")

        if st.session_state.google_sheets_id:
            st.info(f"📊 Syncing to: `{st.session_state.google_sheets_id[:20]}...`")
        else:
            st.warning("⚠️ No Google Sheets ID set. Items won't sync to cloud.")

    # Reset button
    if st.button("🔄 Start Over", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

with col_chat:
    # Chat history container
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.chat_history:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>You:</strong><br/>{content}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>🍽️ Leftovr:</strong><br/>{content}
                </div>
                """, unsafe_allow_html=True)

    # Show recipe recommendations if available
    if st.session_state.recipe_recommendations and not st.session_state.adapted_recipe:
        st.markdown("---")
        st.subheader("🍳 Top Recipe Recommendations")

        for i, rec in enumerate(st.session_state.recipe_recommendations[:3], 1):
            with st.expander(f"**#{i}. {rec.get('title', 'Unknown Recipe')}** (Score: {rec.get('score', 0):.0f})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Uses:** {rec.get('pantry_items_used', 0)}/{len(st.session_state.user_pantry)} of your ingredients")
                    if rec.get('missing_ingredients'):
                        st.markdown(f"**Need to buy:** {', '.join(rec.get('missing_ingredients', []))}")

                    st.markdown("**Difficulty:** " + rec.get("difficulty", "Unknown"))
                    st.markdown("**Reason:** " + rec.get("why_recommended", "N/A"))
                with col2:
                    if rec.get('link'):
                        st.markdown(f"[View Recipe]({rec['link']})")

                if st.button(f"Select Recipe #{i}", key=f"select_{i}"):
                    # Add user message
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": f"I'll make recipe {i}",
                        "timestamp": datetime.now().isoformat()
                    })
                    st.session_state.user_recipe_selection = i
                    st.rerun()

    # Show adapted recipe if available
    if st.session_state.adapted_recipe:
        st.markdown("---")
        st.subheader("📖 Your Personalized Recipe")
        st.markdown(st.session_state.adapted_recipe)

    # Chat input
    user_input = st.chat_input("Type your message... (e.g., 'i got 3 apples', 'what can I make?')")

# ============================================
# HANDLE USER INPUT
# ============================================

if user_input:
    # Add user message to history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })

    # Process message with chatbot (delegates to main.py)
    if st.session_state.chatbot:
        # Build current preferences from session state
        user_prefs = {
            "diet": st.session_state.user_diet,
            "allergies": st.session_state.user_allergies,
            "restrictions": [],
            "cuisines": st.session_state.user_cuisines,
            "skill": st.session_state.user_difficulty
        }

        # Call chatbot (which delegates to main.py's process_chat_message)
        result = st.session_state.chatbot.process_message(
            message=user_input,
            llm=llm,
            user_pantry=st.session_state.user_pantry,
            user_preferences=user_prefs,
            recipe_recommendations=st.session_state.recipe_recommendations
        )

        # Extract results
        bot_response = result["bot_response"]
        should_trigger_workflow = result["should_trigger_workflow"]
        workflow_type = result.get("workflow_type")

        # Update session state with any changes from main.py
        st.session_state.user_pantry = result["updated_pantry"]
        updated_prefs = result["updated_preferences"]
        st.session_state.user_diet = updated_prefs.get("diet", st.session_state.user_diet)
        st.session_state.user_allergies = updated_prefs.get("allergies", st.session_state.user_allergies)
        st.session_state.user_cuisines = updated_prefs.get("cuisines", st.session_state.user_cuisines)
        st.session_state.user_difficulty = updated_prefs.get("skill", st.session_state.user_difficulty)

        # Store recipe selection if present
        if "user_recipe_selection" in result:
            st.session_state.user_recipe_selection = result["user_recipe_selection"]

        # Add bot response to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().isoformat()
        })

        # Trigger workflow if needed
        if should_trigger_workflow and workflow_type:
            st.session_state.workflow_running = True

            # Build final user preferences for workflow
            user_prefs = {
                "diet": st.session_state.user_diet,
                "allergies": st.session_state.user_allergies,
                "restrictions": [],
                "cuisines": st.session_state.user_cuisines,
                "skill": st.session_state.user_difficulty
            }

            # Extract ingredient names
            ingredients = [item["name"] for item in st.session_state.user_pantry]

            if workflow_type == "recipe_search":
                # Prepare initial state for recipe search
                initial_state = {
                    "user_preferences": user_prefs,
                    "waiter_satisfied": True,
                    "handoff_packet": {
                        "user_preferences": user_prefs,
                        "timestamp": datetime.now().isoformat(),
                        "notes": "Preferences collected via chatbot"
                    },
                    "query_type": None,
                    "latest_user_message": None,
                    "final_recommendation": None,
                    "quality_passed": False,
                    "quality_issues": [],
                    "messages": [],
                    "coordination_log": [],
                    "user_ingredients": ingredients,
                    "pantry_inventory": [],
                    "expiring_items": [],
                    "pantry_summary": {},
                    "recipe_results": [],
                    "sous_chef_recommendations": [],
                    "user_recipe_selection": None,
                    "selected_recipe_data": None,
                    "adapted_recipe": None,
                    "formatted_recipe": None,
                    "auto_select_recipe": False,
                    "show_adapted_preview": False
                }

                # Run workflow in background thread
                thread = threading.Thread(
                    target=run_workflow_threaded,
                    args=(initial_state, st.session_state.system, workflow_type),
                    kwargs={},
                    daemon=True
                )
                thread.start()

            elif workflow_type == "recipe_adapt":
                # Prepare state for recipe adaptation
                initial_state = {
                    "user_preferences": user_prefs,
                    "waiter_satisfied": True,
                    "handoff_packet": {
                        "user_preferences": user_prefs,
                        "timestamp": datetime.now().isoformat(),
                        "notes": "User selected recipe via chatbot"
                    },
                    "query_type": None,
                    "latest_user_message": None,
                    "final_recommendation": None,
                    "quality_passed": False,
                    "quality_issues": [],
                    "messages": [],
                    "coordination_log": [],
                    "user_ingredients": ingredients,
                    "recipe_results": st.session_state.recipe_results,
                    "sous_chef_recommendations": st.session_state.recipe_recommendations,
                    "user_recipe_selection": st.session_state.user_recipe_selection,
                    "pantry_inventory": st.session_state.system.pantry.get_inventory() if st.session_state.system else [],
                    "auto_select_recipe": False,
                    "show_adapted_preview": False
                }

                adapt_kwargs = {"graph_config": {"interrupt_before": ["return_to_user"]}}
                # Run adaptation workflow
                thread = threading.Thread(
                    target=run_workflow_threaded,
                    args=(initial_state, st.session_state.system, workflow_type),
                    kwargs=adapt_kwargs,
                    daemon=True
                )
                thread.start()

    st.rerun()


# ============================================
# CHECK FOR WORKFLOW COMPLETION
# ============================================

# Process any queued log updates from background thread
st.session_state.logs = process_queued_log_updates(st.session_state.logs)

# Check for completed workflow results
if st.session_state.workflow_running:
    try:
        if os.path.exists('/tmp/leftovr_result_path.txt'):
            with open('/tmp/leftovr_result_path.txt', 'r') as f:
                result_path = f.read().strip()
            if os.path.exists(result_path):
                with open(result_path, 'r') as f:
                    result = json.load(f)

                # Apply results to session state
                if result.get("complete"):
                    workflow_type = result.get("workflow_type", "")

                    if workflow_type == "recipe_search":
                        st.session_state.recipe_recommendations = result.get("recommendations", [])
                        st.session_state.recipe_results = result.get("recipe_results", [])

                        # Add bot message with recommendations
                        num_recipes = len(st.session_state.recipe_recommendations)
                        if num_recipes > 0:
                            bot_msg = f"I found {num_recipes} great recipes for you! Check them out below and let me know which one you'd like to make."
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": bot_msg,
                                "timestamp": datetime.now().isoformat()
                            })

                    elif workflow_type == "recipe_adapt":
                        st.session_state.adapted_recipe = result.get("formatted_recipe")

                        # Add bot message with adapted recipe
                        if st.session_state.adapted_recipe:
                            bot_msg = "Here's your personalized recipe adapted to your preferences! Check it out below. 👨‍🍳"
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": bot_msg,
                                "timestamp": datetime.now().isoformat()
                            })

                    st.session_state.final_state = result
                    st.session_state.workflow_running = False
                    st.session_state.workflow_complete = True

                    # Clean up temp files
                    os.remove(result_path)
                    os.remove('/tmp/leftovr_result_path.txt')

                    st.rerun()
                else:
                    st.session_state.workflow_running = False
                    error_msg = result.get("error") or "The workflow did not finish."
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"I'm sorry, something went wrong: {error_msg}",
                        "timestamp": datetime.now().isoformat()
                    })
                    st.session_state.logs.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                        "agent": "System",
                        "level": "ERROR",
                        "message": error_msg
                    })
                    if os.path.exists(result_path):
                        os.remove(result_path)
                    if os.path.exists('/tmp/leftovr_result_path.txt'):
                        os.remove('/tmp/leftovr_result_path.txt')
                    st.rerun()
    except Exception as e:
        print(f"Error checking workflow results: {e}")

# Auto-refresh while workflow is running
if st.session_state.workflow_running:
    time.sleep(1)
    st.rerun()
