# Leftovr - Refactored Architecture (Simplified)

## Overview
Clean separation: **Streamlit = UI Frontend** | **LangGraph = Backend Workflow**

---

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (Frontend)                   │
│  - Display chat messages                                     │
│  - Collect user input                                        │
│  - Show recipe cards                                         │
│  - Display pantry sidebar                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    (All logic goes to)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 LANGGRAPH WORKFLOW (Backend)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## LangGraph Nodes (Simplified)

### **Node 1: orchestrator_node (Executive Chef)**
**Purpose**: Single entry point - classify & route

**Responsibilities**:
- Classify query type (pantry/recipe/general)
- Extract user preferences (allergies, diet, etc.)
- Decide which agent to call
- Route to appropriate node

**Outputs**:
- `query_type`: "pantry" | "recipe" | "general"
- `user_preferences`: Dict of dietary info
- `next_action`: Which node to go to

**Routes to**:
→ `pantry_node` (if pantry operation)
→ `recipe_search_node` (if recipe request)
→ `general_response_node` (if general chat)

---

### **Node 2: pantry_node (Pantry Agent)**
**Purpose**: Handle inventory operations only

**Responsibilities**:
- Add/update/remove ingredients
- Check expiration dates
- Return inventory summary

**Inputs**:
- User message with ingredients

**Outputs**:
- `pantry_inventory`: Updated list
- `operation_result`: Success message

**Routes to**:
→ `END` (workflow complete)

---

### **Node 3: recipe_search_node (Recipe Knowledge Agent)**
**Purpose**: Search for recipes using hybrid search

**Responsibilities**:
- Get pantry inventory
- Run hybrid search (keyword + semantic)
- Filter by dietary restrictions
- Return top-k recipes (e.g., 10 recipes)

**Inputs**:
- `user_preferences`: Dietary restrictions
- `pantry_inventory`: Available ingredients

**Outputs**:
- `recipe_results`: List of top-k recipes (10)

**Routes to**:
→ `recommendation_node` (pass results to Sous Chef)

---

### **Node 4: recommendation_node (Sous Chef - Recommend)**
**Purpose**: Generate top 3 recommendations from top-k results

**Responsibilities**:
- Analyze top-k recipes from Recipe Knowledge Agent
- Consider: ingredient match %, expiring items, user skill level
- Select best 3 recipes
- Format for presentation

**Inputs**:
- `recipe_results`: Top-k recipes (10)
- `user_preferences`: User constraints
- `expiring_items`: Prioritize these

**Outputs**:
- `top_3_recommendations`: Best 3 recipes with reasoning

**Routes to**:
→ `END` (show user, wait for selection)

---

### **Node 5: customization_node (Sous Chef - Customize)**
**Purpose**: Adapt selected recipe to user's pantry & preferences

**Responsibilities**:
- Take user's recipe selection (1, 2, or 3)
- Adapt recipe to available ingredients
- Adjust for dietary restrictions
- Simplify/complexify based on skill level
- Format final recipe

**Inputs**:
- `user_recipe_selection`: 1, 2, or 3
- `selected_recipe_data`: Full recipe details
- `pantry_inventory`: Available ingredients
- `user_preferences`: Constraints

**Outputs**:
- `customized_recipe`: Final adapted recipe

**Routes to**:
→ `END` (workflow complete)

---

### **Node 6: general_response_node (Executive Chef)**
**Purpose**: Handle general conversation

**Responsibilities**:
- Answer general cooking questions
- Provide helpful responses
- No agent calls needed

**Inputs**:
- `user_message`: Question/comment

**Outputs**:
- `response`: Text response

**Routes to**:
→ `END` (workflow complete)

---

## Complete Workflow Graph

```
                        START
                          ↓
                  [orchestrator_node]
                  (Executive Chef)
                  - Classify query
                  - Extract preferences
                  - Decide route
                          ↓
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓
    [pantry_node]   [recipe_search_node]  [general_response_node]
    (Pantry Agent)  (Recipe Knowledge)    (Executive Chef)
    - Update inv.   - Hybrid search       - Answer question
         ↓                ↓                     ↓
        END        [recommendation_node]      END
                   (Sous Chef)
                   - Top 3 from top-k
                         ↓
                        END
                   (User selects)
                         ↓
                  [customization_node]
                  (Sous Chef)
                  - Adapt recipe
                         ↓
                        END
```

---

## Simplified State Schema

```python
class RecipeWorkflowState(MessagesState):
    # User context
    user_message: str
    user_preferences: Dict[str, Any]  # {allergies, diet, cuisines, skill}
    
    # Workflow control
    query_type: Literal["pantry", "recipe", "general"]
    current_stage: str  # Track where we are
    
    # Pantry data
    pantry_inventory: List[Dict[str, Any]]
    expiring_items: List[Dict[str, Any]]
    
    # Recipe search results
    recipe_results: List[Dict[str, Any]]  # Top-k from search
    top_3_recommendations: List[Dict[str, Any]]  # Sous Chef picks
    
    # User selection & final recipe
    user_recipe_selection: Optional[int]  # 1, 2, or 3
    selected_recipe_data: Optional[Dict[str, Any]]
    customized_recipe: Optional[Dict[str, Any]]
    
    # Response
    response: Optional[str]
```

---

## Agent Responsibilities (Clear Separation)

### **Executive Chef Agent** (Orchestrator)
- Query classification
- Preference extraction
- Decision making
- General responses
- **Does NOT** search recipes or customize

### **Pantry Agent** (Inventory Manager)
- Add/update/remove ingredients
- Track expiration dates
- Provide inventory summary
- **Does NOT** make decisions

### **Recipe Knowledge Agent** (Search Engine)
- Hybrid search (keyword + semantic)
- Filter by constraints
- Return top-k recipes
- **Does NOT** rank or recommend

### **Sous Chef Agent** (Recipe Specialist)
- Rank top-k → select top 3
- Customize recipes
- Format for presentation
- **Does NOT** search recipes

---

## Streamlit Flow (Pure Frontend)

```python
# 1. Display chat
for msg in chat_history:
    display_message(msg)

# 2. Get user input
user_input = st.text_input("Your message:")

# 3. Send to LangGraph
if user_input:
    result = await graph.ainvoke({
        "user_message": user_input,
        "user_preferences": st.session_state.preferences,
        "pantry_inventory": st.session_state.pantry
    })
    
    # 4. Display results
    if result["query_type"] == "recipe":
        if result["top_3_recommendations"]:
            display_recipe_cards(result["top_3_recommendations"])
        if result["customized_recipe"]:
            display_final_recipe(result["customized_recipe"])
    else:
        display_message(result["response"])
```

---

## Key Benefits of This Architecture

1. **✅ Clear Separation**: UI vs Logic
2. **✅ Single Entry Point**: All logic in LangGraph
3. **✅ Agent Specialization**: Each agent has ONE job
4. **✅ Linear Flow**: Easy to understand and debug
5. **✅ Testable**: Can test workflow without Streamlit
6. **✅ Scalable**: Easy to add new agents/nodes

---

## Migration Steps

1. ✅ Create new simplified state schema
2. ✅ Refactor Executive Chef (just classify + route)
3. ✅ Create recipe_search_node
4. ✅ Create recommendation_node  
5. ✅ Create customization_node
6. ✅ Simplify Streamlit (remove process_chat_message logic)
7. ✅ Update tests

---

## Example User Journey

### Journey 1: Add Ingredients → Get Recommendations
```
User: "I have chicken, tomatoes, and pasta"
  ↓ orchestrator_node → query_type="pantry"
  ↓ pantry_node → add ingredients
  ↓ END
  
User: "What can I make? I'm vegetarian"
  ↓ orchestrator_node → query_type="recipe", extract preferences
  ↓ recipe_search_node → search with constraints
  ↓ recommendation_node → top 3 recipes
  ↓ END (show options)
  
User: "I'll try recipe 2"
  ↓ orchestrator_node → detect selection
  ↓ customization_node → adapt recipe
  ↓ END (show final recipe)
```

### Journey 2: Direct Recipe Question
```
User: "How do I make carbonara?"
  ↓ orchestrator_node → query_type="general"
  ↓ general_response_node → answer
  ↓ END
```
