"""
Leftovr - Streamlit Frontend (Pure UI)
Uses main_refactored.py workflow as backend
"""

import streamlit as st
import asyncio
from typing import Dict, List, Any
from datetime import datetime

# Import the refactored workflow
from main_refactored import create_workflow

# Page config
st.set_page_config(
    page_title="Leftovr - Recipe Assistant",
    page_icon="🍽️",
    layout="wide"
)

# ============================================
# SESSION STATE INITIALIZATION
# ============================================

def init_session_state():
    """Initialize session state variables"""
    if "workflow" not in st.session_state:
        st.session_state.workflow = None
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "pantry_inventory" not in st.session_state:
        st.session_state.pantry_inventory = []
    
    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {}
    
    if "top_3_recommendations" not in st.session_state:
        st.session_state.top_3_recommendations = []
    
    if "current_stage" not in st.session_state:
        st.session_state.current_stage = "initial"
    
    if "messages" not in st.session_state:
        st.session_state.messages = []


# ============================================
# WORKFLOW INITIALIZATION
# ============================================

@st.cache_resource
def get_workflow():
    """Initialize and cache the workflow"""
    try:
        workflow = create_workflow()
        return workflow, None
    except Exception as e:
        return None, str(e)


# ============================================
# UI COMPONENTS
# ============================================

def render_sidebar():
    """Render sidebar with pantry and preferences"""
    with st.sidebar:
        st.title("🗄️ Your Pantry")
        
        # Pantry items
        if st.session_state.pantry_inventory:
            st.write(f"**{len(st.session_state.pantry_inventory)} items**")
            for item in st.session_state.pantry_inventory:
                # Handle both 'ingredient_name' and 'name' keys
                name = item.get('ingredient_name') or item.get('name', 'Unknown')
                qty = item.get('quantity', '')
                unit = item.get('unit', '')
                st.write(f"- {qty} {unit} {name}")
        else:
            st.info("No items yet. Tell me what you have!")
        
        st.divider()
        
        # User preferences
        st.title("👤 Preferences")
        if st.session_state.user_preferences:
            prefs = st.session_state.user_preferences
            if prefs.get("allergies"):
                st.write(f"**Allergies:** {', '.join(prefs['allergies'])}")
            if prefs.get("restrictions"):
                st.write(f"**Diet:** {', '.join(prefs['restrictions'])}")
            if prefs.get("cuisines"):
                st.write(f"**Cuisines:** {', '.join(prefs['cuisines'])}")
        else:
            st.info("No preferences set yet")
        
        st.divider()
        
        # System status
        st.title("⚙️ System")
        if st.session_state.workflow:
            st.success("✅ Workflow ready")
            if st.session_state.workflow.recipe_agent:
                st.success("✅ Hybrid search enabled")
            else:
                st.warning("⚠️ Hybrid search disabled")
        else:
            st.error("❌ Workflow not initialized")
        
        # Reset button
        if st.button("🔄 Reset Session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def render_recipe_card(recipe: Dict, index: int):
    """Render a recipe recommendation card"""
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader(f"{index}. {recipe.get('title', 'Unknown Recipe')}")
            
            # Metadata row 1
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.write(f"⏱️ {recipe.get('readyInMinutes', 'N/A')} min")
            with col_b:
                st.write(f"👥 {recipe.get('servings', 'N/A')} servings")
            with col_c:
                match = recipe.get('match_percentage', recipe.get('score', 0))
                st.write(f"🎯 {match}% match")
            
            # Show ingredients from metadata
            ingredients = recipe.get('ner', []) or recipe.get('ingredients', [])
            if ingredients:
                st.write(f"🥘 **{len(ingredients)} ingredients:** {', '.join(ingredients[:5])}")
                if len(ingredients) > 5:
                    st.caption(f"...and {len(ingredients) - 5} more")
            
            # Show source
            source = recipe.get('source')
            if source:
                st.caption(f"📚 Source: {source}")
            
            # Show directions preview
            directions = recipe.get('directions', [])
            if directions and len(directions) > 0:
                with st.expander("👁️ Preview directions"):
                    for i, step in enumerate(directions[:3], 1):
                        st.write(f"{i}. {step}")
                    if len(directions) > 3:
                        st.caption(f"...{len(directions) - 3} more steps")
            
            # Reasoning
            reason = recipe.get('recommendation_reason', recipe.get('reasoning', ''))
            if reason:
                st.info(f"💡 {reason}")
        
        with col2:
            if st.button(f"Select Recipe {index}", key=f"select_{index}"):
                return index
    
    
    st.divider()
    return None


def render_chat_message(role: str, content: str):
    """Render a chat message"""
    with st.chat_message(role):
        st.markdown(content)


# ============================================
# MAIN APP
# ============================================

def main():
    """Main Streamlit app"""
    
    # Initialize
    init_session_state()
    
    # Get workflow
    if st.session_state.workflow is None:
        workflow, error = get_workflow()
        if error:
            st.error(f"❌ Failed to initialize workflow: {error}")
            st.stop()
        st.session_state.workflow = workflow
    
    workflow = st.session_state.workflow
    
    # Render sidebar
    render_sidebar()
    
    # Main content
    st.title("🍽️ Leftovr - Your AI Recipe Assistant")
    st.markdown("Tell me what ingredients you have, and I'll suggest delicious recipes!")
    
    # Display chat history
    for msg in st.session_state.chat_history:
        render_chat_message(msg["role"], msg["content"])
    
    # Display recipe recommendations if available
    if st.session_state.top_3_recommendations and st.session_state.current_stage == "presenting_options":
        st.markdown("---")
        st.subheader("🍽️ Recipe Recommendations")
        
        selected = None
        for i, recipe in enumerate(st.session_state.top_3_recommendations, 1):
            result = render_recipe_card(recipe, i)
            if result:
                selected = result
        
        # Handle recipe selection
        if selected:
            with st.spinner(f"Customizing recipe {selected}..."):
                try:
                    # Call workflow with selection
                    result = workflow.invoke({
                        "user_message": f"I'll try recipe {selected}",
                        "user_preferences": st.session_state.user_preferences,
                        "pantry_inventory": st.session_state.pantry_inventory,
                        "top_3_recommendations": st.session_state.top_3_recommendations,
                        "user_recipe_selection": selected,
                        "messages": st.session_state.messages,
                        "coordination_log": [],
                        "current_stage": "initial"
                    })
                    
                    # Update state
                    if result.get("response"):
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": result["response"]
                        })
                    
                    st.session_state.current_stage = result.get("current_stage", "idle")
                    st.session_state.messages = result.get("messages", [])
                    
                    st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error customizing recipe: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to chat
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Display user message
        render_chat_message("user", user_input)
        
        # Call workflow
        with st.spinner("Thinking..."):
            try:
                # Invoke workflow with current state
                result = workflow.invoke({
                    "user_message": user_input,
                    "user_preferences": st.session_state.user_preferences,
                    "pantry_inventory": st.session_state.pantry_inventory,
                    "top_3_recommendations": st.session_state.top_3_recommendations,
                    "messages": st.session_state.messages,
                    "coordination_log": [],
                    "current_stage": st.session_state.current_stage
                })
                
                # Update session state from result
                if result.get("pantry_inventory"):
                    st.session_state.pantry_inventory = result["pantry_inventory"]
                
                if result.get("user_preferences"):
                    st.session_state.user_preferences = result["user_preferences"]
                
                if result.get("top_3_recommendations"):
                    st.session_state.top_3_recommendations = result["top_3_recommendations"]
                
                if result.get("messages"):
                    st.session_state.messages = result["messages"]
                
                st.session_state.current_stage = result.get("current_stage", "idle")
                
                # Add bot response to chat
                if result.get("response"):
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["response"]
                    })
                
                # Rerun to display updates
                st.rerun()
            
            except Exception as e:
                st.error(f"❌ Error processing message: {str(e)}")
                import traceback
                with st.expander("Show error details"):
                    st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
