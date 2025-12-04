"""
FastAPI Backend for Leftovr Application

This API server provides endpoints for:
- Chat interface with AI agents
- Pantry management (CRUD operations)
- Recipe search and recommendations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import sys

# Add parent directory to path to import agents
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.executive_chef_agent import ExecutiveChefAgent
from agents.pantry_agent import PantryAgent
from agents.recipe_knowledge_agent import RecipeKnowledgeAgent
from agents.sous_chef_agent import SousChefAgent
from main import LeftovrWorkflow

# Initialize FastAPI app
app = FastAPI(
    title="Leftovr API",
    description="AI-powered recipe recommendations and pantry management",
    version="1.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    user_message: str = Field(..., description="User's message to the AI chef")
    user_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User dietary preferences")
    pantry_inventory: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Current pantry inventory")

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant's response")
    current_stage: Optional[str] = Field(None, description="Current conversation stage")
    top_3_recommendations: Optional[List[Dict[str, Any]]] = Field(None, description="Top recipe recommendations")
    pantry_inventory: Optional[List[Dict[str, Any]]] = Field(None, description="Updated pantry inventory")
    expiring_items: Optional[List[Dict[str, Any]]] = Field(None, description="Items expiring soon")

class PantryItem(BaseModel):
    ingredient_name: str = Field(..., description="Name of the ingredient")
    quantity: float = Field(..., description="Quantity available")
    unit: str = Field(..., description="Unit of measurement")
    expiration_date: Optional[str] = Field(None, description="Expiration date (YYYY-MM-DD)")

class PantryResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    inventory: Optional[List[Dict[str, Any]]] = Field(None, description="Current inventory")

class RecipeSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for recipes")
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences")
    top_k: Optional[int] = Field(10, description="Number of results to return")

class RecipeSearchResponse(BaseModel):
    recipes: List[Dict[str, Any]] = Field(..., description="List of recipes")
    total_results: int = Field(..., description="Total number of results")

# Initialize workflow (lazy loading)
_workflow = None

def get_workflow():
    """Get or create workflow instance"""
    global _workflow
    if _workflow is None:
        _workflow = LeftovrWorkflow()
    return _workflow


# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Leftovr API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    workflow = get_workflow()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agents": {
            "executive_chef": workflow.executive_chef is not None,
            "pantry": workflow.pantry_agent is not None,
            "sous_chef": workflow.sous_chef is not None,
            "recipe_knowledge": workflow.recipe_agent is not None,
        }
    }


# ============================================
# CHAT ENDPOINTS
# ============================================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI chef and get a response.
    
    This endpoint handles all conversational interactions including:
    - Recipe recommendations
    - Pantry management queries
    - General cooking questions
    """
    try:
        workflow = get_workflow()
        
        # Prepare input state
        input_state = {
            "user_message": request.user_message,
            "user_preferences": request.user_preferences,
            "pantry_inventory": request.pantry_inventory,
        }
        
        # Process through workflow
        result = workflow.invoke(input_state)
        
        # Return response
        return ChatResponse(
            response=result.get("response", "I'm sorry, I couldn't process that request."),
            current_stage=result.get("current_stage"),
            top_3_recommendations=result.get("top_3_recommendations"),
            pantry_inventory=result.get("pantry_inventory"),
            expiring_items=result.get("expiring_items"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


# ============================================
# PANTRY ENDPOINTS
# ============================================

@app.get("/pantry/inventory")
async def get_inventory():
    """Get current pantry inventory"""
    try:
        workflow = get_workflow()
        inventory = workflow.get_current_inventory()
        
        return {
            "status": "success",
            "inventory": inventory,
            "total_items": len(inventory)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inventory: {str(e)}")

@app.post("/pantry/add")
async def add_pantry_item(item: PantryItem):
    """Add a new item to the pantry"""
    try:
        workflow = get_workflow()
        
        # Use pantry agent to add item
        result = await workflow.pantry_agent.add_ingredient(
            ingredient_name=item.ingredient_name,
            quantity=item.quantity,
            unit=item.unit,
            expiration_date=item.expiration_date
        )
        
        return {
            "status": "success",
            "message": f"Added {item.ingredient_name} to pantry",
            "item": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding item: {str(e)}")

@app.put("/pantry/update/{item_name}")
async def update_pantry_item(item_name: str, item: PantryItem):
    """Update an existing pantry item"""
    try:
        workflow = get_workflow()
        
        # Use pantry agent to update item
        result = await workflow.pantry_agent.update_ingredient(
            ingredient_name=item_name,
            quantity=item.quantity,
            unit=item.unit,
            expiration_date=item.expiration_date
        )
        
        return {
            "status": "success",
            "message": f"Updated {item_name}",
            "item": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating item: {str(e)}")

@app.delete("/pantry/delete/{item_name}")
async def delete_pantry_item(item_name: str):
    """Delete an item from the pantry"""
    try:
        workflow = get_workflow()
        
        # Use pantry agent to delete item
        await workflow.pantry_agent.remove_ingredient(ingredient_name=item_name)
        
        return {
            "status": "success",
            "message": f"Deleted {item_name} from pantry"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")


# ============================================
# RECIPE ENDPOINTS
# ============================================

@app.post("/recipes/search")
async def search_recipes(request: RecipeSearchRequest):
    """
    Search for recipes based on query and preferences.
    
    Supports:
    - Ingredient-based search
    - Dietary preferences
    - Cuisine preferences
    """
    try:
        workflow = get_workflow()
        
        if not workflow.recipe_agent:
            raise HTTPException(
                status_code=503,
                detail="Recipe search is not available. Please run the ingestion script first."
            )
        
        # Get pantry items for ingredient matching
        inventory = workflow.get_current_inventory()
        pantry_items = [item.get("ingredient_name", "") for item in inventory]
        
        # Perform hybrid search
        results = workflow.recipe_agent.hybrid_query(
            pantry_items=pantry_items if pantry_items else None,
            query_text=request.query,
            top_k=request.top_k,
            allow_missing=3,
            use_semantic=True
        )
        
        # Format results
        recipes = []
        for recipe_metadata, score, num_used, missing in results:
            recipes.append({
                **recipe_metadata,
                "score": score,
                "num_pantry_used": num_used,
                "missing_ingredients": missing,
                "match_percentage": round((num_used / len(recipe_metadata.get("ner", []))) * 100) if recipe_metadata.get("ner") else 0
            })
        
        return {
            "recipes": recipes,
            "total_results": len(recipes)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching recipes: {str(e)}")


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
