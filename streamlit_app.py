import os
import re
import json
import asyncio
import threading
import time
import traceback
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from queue import Queue

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

from main import ModernCollaborativeSystem, llm

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
    """Orchestrates chat interactions using the waiter agent and other agents"""

    def __init__(self, waiter_agent, pantry_agent, system):
        self.waiter = waiter_agent
        self.pantry = pantry_agent
        self.system = system
        self.conversation_context = {
            "preferences_collected": False,
            "pantry_items_added": False,
            "awaiting_recipe_selection": False
        }

    def parse_intent(self, message: str, llm) -> Dict[str, Any]:
        """Parse user message to understand intent using LLM"""
        system_prompt = """You are an intent classifier for a recipe chatbot system.

Classify the user's message into ONE of these intents and extract relevant entities:

**INTENTS:**
1. "add_pantry" - User wants to add ingredients (e.g., "i got 3 apples", "I have chicken")
2. "request_recipes" - User wants recipe recommendations (e.g., "what can I make?", "give me recipes", "show me what to cook")
3. "select_recipe" - User selects a recipe (e.g., "recipe 1", "I'll make #2", "the first one")
4. "preferences" - User provides dietary info/preferences (e.g., "I'm vegetarian", "allergic to nuts", "I like Italian food")
5. "other" - General chat, questions, greetings, etc

Return ONLY valid JSON:
{
    "intent": "intent_name",
    "entities": {
        "ingredients": [{"name": "apple", "quantity": 3, "unit": "pieces"}],  // for add_pantry
        "recipe_number": 1,  // for select_recipe
        "preferences": {"diet": "vegetarian", "allergies": ["nuts"], "cuisines": ["italian"], "skill": "beginner"}  // for preferences
    }
}

Examples:
- "i got 3 apples" → {"intent": "add_pantry", "entities": {"ingredients": [{"name": "apple", "quantity": 3, "unit": "pieces"}]}}
- "what can I make?" → {"intent": "request_recipes", "entities": {}}
- "I'll make recipe 2" → {"intent": "select_recipe", "entities": {"recipe_number": 2}}
- "I'm allergic to nuts" → {"intent": "preferences", "entities": {"preferences": {"allergies": ["nuts"]}}}
- "hello" → {"intent": "other", "entities": {}}
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
            return parsed
        except Exception as e:
            print(f"Error parsing intent: {e}")
            print(f"Response text: {response_text}")
            return {"intent": "other", "entities": {}}

    async def handle_add_pantry_async(self, entities: Dict[str, Any], spreadsheet_id: Optional[str] = None) -> str:
        """Handle adding ingredients to pantry"""
        ingredients = entities.get("ingredients", [])

        if not ingredients:
            return "I didn't quite catch what ingredients you have. Could you tell me again? For example: 'I got 3 apples and 2 chicken breasts'"

        # Add to session state pantry
        added_items = []
        updates_for_sheets = []
        
        for ing in ingredients:
            item_name = ing.get("name", "")
            raw_quantity = ing.get("quantity", 1)
            unit = ing.get("unit") or "pieces"

            if item_name:
                name_clean = item_name.strip()
                if not name_clean:
                    continue

                pantry_quantity = raw_quantity
                display_quantity = raw_quantity
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

                # Update or insert into session pantry (case-insensitive)
                updated = False
                for stored_item in st.session_state.user_pantry:
                    if stored_item["name"].strip().lower() == name_clean.lower():
                        stored_item["quantity"] = pantry_quantity
                        stored_item["unit"] = unit
                        updated = True
                        break

                if not updated:
                    st.session_state.user_pantry.append({
                        "name": name_clean,
                        "quantity": pantry_quantity,
                        "unit": unit
                    })

                # Update pantry agent cache
                ingredient_record = self.pantry.add_or_update_ingredient(
                    ingredient_name=name_clean,
                    quantity=pantry_quantity,
                    unit=unit
                )
                
                updates_for_sheets.append(ingredient_record)

                added_items.append(f"{display_quantity_str} {unit} of {name_clean}")

        if updates_for_sheets and spreadsheet_id:
            try:
                success = await self.pantry.update_inventory_in_sheets(
                    spreadsheet_id=spreadsheet_id,
                    updates=updates_for_sheets
                )
                if success:
                    add_log(f"Synced {len(updates_for_sheets)} items to Google Sheets", "Pantry", "INFO")
                else:
                    add_log("Failed to sync with Google Sheets (MCP client not connected)", "Pantry", "WARNING")
            except Exception as e:
                add_log(f"Error syncing to Google Sheets: {str(e)}", "Pantry", "ERROR")

        if added_items:
            items_text = ", ".join(added_items)
            return f"Great! I've added {items_text} to your pantry. 🗄️\n\nWhat else would you like to add, or would you like to see what recipes you can make?"

        return "I couldn't add those items. Could you try again?"
    
    def handle_add_pantry(self, entities: Dict[str, Any]) -> str:
        """Handle adding ingredients to pantry (sync wrapper)"""
        # Get spreadsheet_id from session state or environment
        spreadsheet_id = st.session_state.get("google_sheets_id") or os.getenv("GOOGLE_SHEETS_ID")
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.handle_add_pantry_async(entities, spreadsheet_id)
            )
            return result
        finally:
            loop.close()

    def handle_request_recipes(self) -> Tuple[str, bool]:
        """Handle recipe request - returns (message, should_trigger_workflow)"""
        if not st.session_state.user_pantry:
            return ("I don't see any ingredients in your pantry yet. Tell me what you have! For example: 'I got 3 apples and some chicken'", False)

        has_basic_prefs = (
            st.session_state.user_diet or
            st.session_state.user_cuisines or
            st.session_state.user_difficulty
        )

        if not has_basic_prefs:
            return ("Before I find recipes, let me know a bit about your preferences! Are there any cuisines you prefer? Any dietary restrictions or allergies I should know about?", False)

        return (f"Perfect! Let me search for recipes using your {len(st.session_state.user_pantry)} pantry items... 🔍", True)

    def handle_select_recipe(self, recipe_number: int) -> Tuple[str, bool]:
        """Handle recipe selection - returns (message, should_trigger_adaptation)"""
        if not st.session_state.recipe_recommendations:
            return ("I don't have any recipe recommendations yet. Please request recipes first!", False)
        
        if recipe_number < 1 or recipe_number > len(st.session_state.recipe_recommendations):
            return (f"Please select a recipe number between 1 and {len(st.session_state.recipe_recommendations)}.", False)
        
        # Store selection
        st.session_state.user_recipe_selection = recipe_number
        return (f"Excellent choice! Let me prepare recipe #{recipe_number} for you... 👨‍🍳", True)

    def process_message(self, message: str, llm) -> Tuple[str, bool, Optional[str]]:
        """
        Process user message and return (bot_response, should_trigger_workflow, workflow_type)
        
        workflow_type can be: None, "recipe_search", "recipe_adapt"
        """
        # Parse intent
        intent_data = self.parse_intent(message, llm)
        intent = intent_data.get("intent", "other")
        entities = intent_data.get("entities", {})

        print(f"[ChatBot] Intent: {intent}, Entities: {entities}")

        # Fallback pattern matching for recipe selections if intent parsing fails
        if intent != "select_recipe" and st.session_state.recipe_recommendations:
            selection_match = re.search(r"(?:recipe|option|#)\s*(\d+)", message, re.IGNORECASE)
            if not selection_match:
                if re.search(r"\b(make|take|choose|pick|go with|cook)\b", message, re.IGNORECASE):
                    selection_match = re.search(r"\b(\d{1,2})\b", message)
            if selection_match:
                try:
                    fallback_recipe = int(selection_match.group(1))
                    response, should_trigger = self.handle_select_recipe(fallback_recipe)
                    workflow_type = "recipe_adapt" if should_trigger else None
                    return (response, should_trigger, workflow_type)
                except (TypeError, ValueError):
                    pass

        # Handle specific intents
        if intent == "add_pantry":
            response = self.handle_add_pantry(entities)
            return (response, False, None)

        elif intent == "request_recipes":
            response, should_trigger = self.handle_request_recipes()
            workflow_type = "recipe_search" if should_trigger else None
            return (response, should_trigger, workflow_type)

        elif intent == "select_recipe":
            recipe_num = entities.get("recipe_number")
            if recipe_num:
                try:
                    recipe_num = int(recipe_num)
                except (TypeError, ValueError):
                    return ("I couldn't tell which recipe number you meant. Please say 'recipe 1', 'recipe 2', or 'recipe 3'.", False, None)
                
                response, should_trigger = self.handle_select_recipe(recipe_num)
                workflow_type = "recipe_adapt" if should_trigger else None
                print("DEBUG: workflow_type =", workflow_type)
                return (response, should_trigger, workflow_type)
            else:
                return ("I didn't quite get which recipe you want. Could you say 'recipe 1', 'recipe 2', or 'recipe 3'?", False, None)

        elif intent == "preferences":
            # Use waiter agent to extract and respond to preferences
            prefs = entities.get("preferences", {})
            
            # Update session state with extracted preferences
            if prefs.get("diet"):
                st.session_state.user_diet = prefs["diet"]
            if prefs.get("allergies"):
                st.session_state.user_allergies.extend(prefs["allergies"])
                st.session_state.user_allergies = list(set(st.session_state.user_allergies))
            if prefs.get("cuisines"):
                st.session_state.user_cuisines.extend(prefs["cuisines"])
                st.session_state.user_cuisines = list(set(st.session_state.user_cuisines))
            if prefs.get("skill"):
                st.session_state.user_difficulty = prefs["skill"]

            # Have waiter respond
            response = self.waiter.respond(llm, message)
            return (response, False, None)

        else:  # "other" - general conversation
            # Use waiter agent to handle general conversation
            response = self.waiter.respond(llm, message)
            return (response, False, None)


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
# THREAD-SAFE LOGGING
# ============================================

log_queue = Queue()
status_queue = Queue()

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

def process_queued_updates():
    """Process queued log updates from background thread"""
    while not log_queue.empty():
        try:
            log_entry = log_queue.get_nowait()
            st.session_state.logs.append(log_entry)
        except:
            break


# ============================================
# WORKFLOW EXECUTION
# ============================================

async def run_workflow_async(
    initial_state: Dict[str, Any],
    system_instance,
    workflow_type: str,
    graph_config: Optional[Dict[str, Any]] = None
):
    """Run the workflow asynchronously"""
    try:
        add_log(f"Starting {workflow_type} workflow", "System", "INFO")
        
        system = system_instance
        
        print("\n" + "="*80)
        print(f"STARTING WORKFLOW - {workflow_type.upper()}")
        print("="*80)
        print(f"User preferences: {initial_state.get('user_preferences')}")
        print(f"User ingredients: {initial_state.get('user_ingredients')}")
        print("="*80 + "\n")
        
        # Execute the graph
        config = graph_config or {}
        state = await system.graph.ainvoke(initial_state, config=config)

        while (
            state.get("_interrupt") == "wait_for_user_selection"
            and state.get("user_recipe_selection")
        ):
            add_log("Auto-resuming workflow after applying recipe selection", "System", "DEBUG")
            resume_config = dict(config)
            resume_config["resume"] = True
            state = await system.graph.ainvoke(state, config=resume_config)
        
        print("\n" + "="*80)
        print("WORKFLOW EXECUTION COMPLETE")
        print("="*80)
        print(f"Recommendations: {len(state.get('sous_chef_recommendations', []))}")
        print("="*80 + "\n")
        
        # Process state updates based on coordination log
        coord_log = state.get("coordination_log", [])
        for log_entry in coord_log:
            if ":" in log_entry:
                parts = log_entry.split(":", 1)
                agent = parts[0].strip()
                message = parts[1].strip()
                add_log(message, agent, "INFO")
        
        # Store results
        result_data = {
            "recommendations": state.get("sous_chef_recommendations", []),
            "recipe_results": state.get("recipe_results", []),
            "formatted_recipe": state.get("formatted_recipe"),
            "final_state": state,
            "complete": True,
            "workflow_type": workflow_type
        }
        
        add_log(f"{workflow_type} workflow completed successfully", "System", "INFO")
        
        return result_data
        
    except Exception as e:
        add_log(f"Workflow error: {str(e)}", "System", "ERROR")
        stack_trace = traceback.format_exc()
        add_log(f"Full stack trace:\n{stack_trace}", "System", "DEBUG")
        print("=" * 80)
        print("WORKFLOW ERROR")
        print("=" * 80)
        print(stack_trace)
        print("=" * 80)
        return {"error": str(e), "stack_trace": stack_trace, "complete": False}

def run_workflow_threaded(
    initial_state: Dict[str, Any],
    system_instance,
    workflow_type: str,
    graph_config: Optional[Dict[str, Any]] = None
):
    """Run workflow in a thread"""
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


# ============================================
# INITIALIZE SYSTEM
# ============================================

if st.session_state.system is None:
    with st.spinner("🔧 Initializing AI agents..."):
        try:
            st.session_state.system = ModernCollaborativeSystem()
            st.session_state.chatbot = ChatbotOrchestrator(
                waiter_agent=st.session_state.system.waiter,
                pantry_agent=st.session_state.system.pantry,
                system=st.session_state.system
            )
            
            # Send initial greeting
            if not st.session_state.chat_history:
                greeting = st.session_state.system.waiter.run(llm)
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
    
    # Process message with chatbot
    if st.session_state.chatbot:
        bot_response, should_trigger_workflow, workflow_type = st.session_state.chatbot.process_message(user_input, llm)
        
        # Add bot response to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trigger workflow if needed
        if should_trigger_workflow and workflow_type:
            st.session_state.workflow_running = True
            
            # Build user preferences
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

# Process any queued updates
process_queued_updates()

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
