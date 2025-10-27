# Executive Chef Orchestration - Example Interactions

This document shows real-world interaction flows through the orchestrated system.

## Example 1: Simple Pantry Check

### User Input

```
User: "Show me what's in my pantry"
```

### Workflow Trace

#### Step 1: Waiter Node

```
Waiter: Classifying query...
Classification: "pantry"
Delegation: Sending to Executive Chef
```

#### Step 2: Executive Chef Orchestrate

```
Executive Chef: Orchestrating workflow...
  Analyzing request complexity...

Complexity Analysis Result:
{
  "complexity": "simple",
  "strategy": "pantry",
  "required_agents": ["pantry"],
  "reasoning": "Direct inventory query with no constraints"
}

Creating lightweight task plan:
{
  "strategy": "pantry",
  "complexity": "simple",
  "agents": ["pantry"],
  "query_type": "pantry"
}

Delegating to Pantry Agent...
```

#### Step 3: Agent Execute (Pantry)

```
Pantry Agent: Processing request...
  Fetching inventory from cache...
  Total ingredients: 6
```

#### Step 4: Waiter Finalize

```
Waiter: Presenting pantry contents...

Your Pantry:
✅ Chicken breast: 2 lb (expires in 7 days)
⚠️  Spinach: 1 bunch (expires in 1 day - use soon!)
✅ Pasta: 1 lb
✅ Olive oil: 0.5 cup
✅ Garlic: 8 cloves
✅ Tomatoes: 5 pieces (expires in 7 days)
```

### Key Points

- **1 LLM Call**: Complexity analysis only
- **Fast Execution**: < 2 seconds
- **No Synthesis**: Direct presentation for simple query

---

## Example 2: Recipe Request with Constraints

### User Input

```
User: "I want a vegetarian dinner recipe. I'm allergic to nuts."
```

### Workflow Trace

#### Step 1: Waiter Node (Preference Collection)

```
Waiter: Extracting preferences...

Extracted:
{
  "allergies": ["nuts"],
  "restrictions": ["vegetarian"]
}

Preferences complete. Delegating to Executive Chef...
```

#### Step 2: Executive Chef Orchestrate (Analysis)

```
Executive Chef: Orchestrating workflow...
  Analyzing request complexity...

Complexity Analysis:
{
  "complexity": "medium",
  "strategy": "ingredient_first",
  "required_agents": ["pantry", "sous_chef"],
  "agent_sequence": ["pantry", "sous_chef"],
  "reasoning": "Recipe request with dietary constraints",
  "priority_factors": ["allergen_safety", "ingredient_availability"],
  "estimated_steps": 3
}

Creating detailed task plan...

Task Plan:
{
  "tasks": [
    {
      "agent": "pantry",
      "action": "check_inventory",
      "priority": "high",
      "expected_output": "ingredient list with expiration dates"
    },
    {
      "agent": "sous_chef",
      "action": "suggest_recipes",
      "priority": "high",
      "expected_output": "top 3 vegetarian, nut-free recipes"
    }
  ],
  "delegation_order": ["pantry", "sous_chef"],
  "success_criteria": [
    "recipes_suggested",
    "allergen_safe",
    "vegetarian_compliant"
  ]
}
```

#### Step 3: Agent Execute (Pantry Check)

```
Pantry Agent: Processing request...

Pantry Summary:
  Total ingredients: 6
  Expiring soon: 1 (spinach)
  Critical items: 1

⚠️  ALERT: Spinach expires in 1 day - prioritize usage!
```

#### Step 4: Agent Execute (Sous Chef Recommendations)

```
Sous Chef: Generating recommendations...
  Querying Recipe Knowledge Agent...
  Retrieved 10 candidate recipes
  Scoring based on pantry availability...
  Filtering for allergens (nuts)...
  Filtering for dietary restrictions (vegetarian)...

Generated 3 recommendations
```

#### Step 5: Executive Chef Orchestrate (Synthesis)

```
Executive Chef: Synthesizing agent responses...

Agent Responses:
{
  "pantry": {
    "total_ingredients": 6,
    "expiring_items": ["spinach"],
    "priority": "Use spinach today"
  },
  "sous_chef": [
    {
      "rank": 1,
      "title": "Garlic Spinach Pasta",
      "score": 95,
      "uses_expiring": ["spinach"]
    },
    {
      "rank": 2,
      "title": "Tomato Basil Pasta",
      "score": 88
    },
    {
      "rank": 3,
      "title": "Creamy Vegetable Pasta",
      "score": 82
    }
  ]
}

Synthesis: Generated user-friendly recommendations highlighting spinach urgency
```

#### Step 6: Waiter Node (Presentation)

```
Waiter: Presenting recipe recommendations...

========================================
🍽️  RECIPE RECOMMENDATIONS
========================================

Great news! I found some delicious vegetarian recipes using what you have.
⚠️  I noticed your spinach expires tomorrow - let's use it today!

🥇 GARLIC SPINACH PASTA (Score: 95) ⭐ TOP PICK
Why: Uses your spinach that expires tomorrow!

Uses from your pantry:
  ✅ Spinach (2 cups - expires tomorrow!)
  ✅ Pasta (400g)
  ✅ Garlic (4 cloves)
  ✅ Olive oil (3 tbsp)

Missing ingredients:
  🛒 Salt and pepper to taste

⏱️  Time: 20 minutes | Difficulty: Beginner
✅ Safe for your allergies (nut-free)

🥈 TOMATO BASIL PASTA (Score: 88)
Why: Fresh and simple with ingredients on hand

Uses from your pantry:
  ✅ Tomatoes (5 pieces)
  ✅ Pasta (400g)
  ✅ Garlic (3 cloves)
  ✅ Olive oil (2 tbsp)

Missing ingredients:
  🛒 Fresh basil (1/4 cup)
  🛒 Parmesan cheese (optional, can use vegan alternative)

⏱️  Time: 25 minutes | Difficulty: Beginner
✅ Safe for your allergies (nut-free)

🥉 CREAMY VEGETABLE PASTA (Score: 82)
Why: Hearty and nutritious

Uses from your pantry:
  ✅ Pasta (400g)
  ✅ Garlic (2 cloves)
  ✅ Olive oil (2 tbsp)

Missing ingredients:
  🛒 Heavy cream or coconut milk (1 cup)
  🛒 Mixed vegetables (2 cups)

⏱️  Time: 30 minutes | Difficulty: Beginner
✅ Safe for your allergies (nut-free)

Which recipe would you like to make? (Reply 1, 2, or 3)
```

### User Selection

```
User: "1"
```

#### Step 7: Waiter Node (Selection Processing)

```
Waiter: User selected recipe #1
Delegating to Executive Chef for adaptation...
```

#### Step 8: Executive Chef Orchestrate (Adaptation Coordination)

```
Executive Chef: Coordinating recipe adaptation...

Delegation to Sous Chef:
{
  "action": "adapt_recipe",
  "parameters": {
    "selection": 1,
    "preferences": {
      "allergies": ["nuts"],
      "restrictions": ["vegetarian"]
    }
  }
}
```

#### Step 9: Agent Execute (Recipe Adaptation)

```
Sous Chef: Adapting recipe...
  Selected: Garlic Spinach Pasta
  Checking allergen compliance...
  ✅ No nuts in recipe
  Checking dietary compliance...
  ✅ Recipe is vegetarian
  Simplifying for beginner level...
  Generating step-by-step instructions...

Recipe adapted successfully!
```

#### Step 10: Executive Chef (Route to QA)

```
Executive Chef: Adaptation complete
Routing to Waiter for final quality check...
```

#### Step 11: Waiter Finalize (Quality Check)

```
Waiter: Performing quality check with conversation context...

Quality Check:
{
  "passed": true,
  "issues": [],
  "score": 95,
  "critical_failures": []
}

✅ Recipe is safe and meets all requirements!

Presenting final recipe...
```

#### Step 12: Final Presentation

```
========================================
🍽️  YOUR RECIPE - Garlic Spinach Pasta
========================================

🎉 Great choice! This recipe will help you use up that spinach before it expires!

## Modifications Made:
✅ Confirmed nut-free for your allergy
✅ Confirmed vegetarian
✅ Simplified for beginner skill level

## Ingredients You Have:
✅ 2 cups fresh spinach (use today - expires tomorrow!)
✅ 400g pasta
✅ 4 cloves garlic, minced
✅ 3 tbsp olive oil

## Ingredients to Buy:
🛒 Salt to taste
🛒 Black pepper to taste
🛒 Red pepper flakes (optional, for heat)

## Step-by-Step Instructions:

1. **Boil water for pasta** (5 min)
   - Fill large pot with water
   - Add 1 tbsp salt
   - Bring to rolling boil
   💡 Tip: Use plenty of water so pasta doesn't stick

2. **Cook pasta** (8-10 min)
   - Add pasta to boiling water
   - Stir occasionally
   - Cook until al dente (tender but firm)
   - SAVE 1 cup of pasta water before draining!
   💡 Tip: Pasta water helps sauce stick better

3. **Prepare garlic** (2 min)
   - While pasta cooks, mince 4 cloves of garlic
   - Set aside
   💡 Tip: Don't cook garlic yet - it burns easily!

4. **Sauté garlic** (2 min)
   - Heat 3 tbsp olive oil in large pan over MEDIUM heat
   - Add minced garlic
   - Cook until fragrant (30-60 seconds)
   - Don't let it brown! Remove from heat if it starts browning
   💡 Tip: Garlic cooks fast - watch it carefully

5. **Wilt spinach** (2 min)
   - Add all spinach to pan with garlic
   - Stir constantly
   - Cook until just wilted (bright green, not mushy)
   ⚠️  Use your spinach today - it expires tomorrow!
   💡 Tip: Spinach shrinks a LOT when cooked

6. **Combine everything** (2 min)
   - Add drained pasta to pan
   - Toss with garlic and spinach
   - Add 1/4 cup saved pasta water if too dry
   - Season with salt and pepper to taste
   💡 Tip: Taste before serving and adjust seasoning

⏱️  Total Time: 20 minutes
🍽️  Servings: 4
💪 Difficulty: Beginner-friendly

## Safety Notes:
✅ Allergen Status: Nut-free, Safe for your allergy
✅ Dietary Status: Vegetarian
✅ No cross-contamination concerns

## Nutrition Highlights:
- High in iron (from spinach)
- Good source of fiber
- Heart-healthy olive oil
- Low in saturated fat

Enjoy your meal! 🍝

Would you like me to help with anything else?
```

### Key Points

- **7 LLM Calls**: Analysis, planning, synthesis, recommendations, adaptation, formatting, QA
- **Execution Time**: 10-15 seconds
- **Complete Orchestration**: All agents coordinated by Executive Chef
- **Safety First**: Quality check with conversation context catches issues
- **Waste Reduction**: Highlighted expiring spinach

---

## Example 3: Complex Multi-Constraint Request

### User Input

```
User: "I need a quick vegan dinner that's gluten-free, no soy, using ingredients that expire soon. I'm a beginner cook and only have 30 minutes."
```

### Workflow Trace (Abbreviated)

#### Complexity Analysis

```
{
  "complexity": "complex",
  "strategy": "waste_reduction",
  "required_agents": ["pantry", "recipe_knowledge", "sous_chef"],
  "reasoning": "Multiple constraints + time limit + skill level + expiration priority",
  "priority_factors": [
    "allergen_safety",
    "dietary_compliance",
    "expiration_urgency",
    "skill_appropriateness",
    "time_constraint"
  ],
  "estimated_steps": 5
}
```

#### Task Plan (Full LLM-Generated)

```
{
  "tasks": [
    {
      "agent": "pantry",
      "action": "check_expiring",
      "input": "3 day threshold",
      "priority": "high"
    },
    {
      "agent": "pantry",
      "action": "check_inventory",
      "input": "full inventory",
      "priority": "high"
    },
    {
      "agent": "recipe_knowledge",
      "action": "semantic_search",
      "input": "vegan gluten-free quick recipes",
      "priority": "high"
    },
    {
      "agent": "sous_chef",
      "action": "filter_and_rank",
      "input": "recipes + constraints + expiring items",
      "priority": "high"
    },
    {
      "agent": "sous_chef",
      "action": "suggest_recipes",
      "input": "filtered results",
      "priority": "high"
    }
  ],
  "delegation_order": ["pantry", "recipe_knowledge", "sous_chef"],
  "success_criteria": [
    "vegan_compliant",
    "gluten_free_verified",
    "soy_free_verified",
    "time_under_30_minutes",
    "beginner_appropriate",
    "uses_expiring_items"
  ],
  "fallback_strategy": "Offer alternatives with shopping list if perfect match not found"
}
```

#### Synthesis Output

```
Great news! I found recipes that:
✅ Are completely vegan
✅ Are gluten-free (verified)
✅ Contain no soy
✅ Can be made in under 30 minutes
✅ Match beginner skill level
✅ Use your spinach that expires tomorrow!

I'm prioritizing recipes using your expiring spinach to reduce waste.
```

### Key Points

- **Complex constraints** trigger full LLM orchestration
- **Multiple agents** coordinated in sequence
- **Success criteria** explicitly tracked
- **Fallback strategy** defined upfront
- **User constraints** all validated before presentation

---

## Delegation Log Example

### Complete Audit Trail

```
Delegation Log for Session:

[2025-10-26 14:30:15] Executive Chef → Pantry Agent
  Action: check_inventory
  Parameters: {user_message: "I want recipes", preferences: {...}}
  Status: Completed

[2025-10-26 14:30:16] Executive Chef → Pantry Agent
  Action: check_expiring
  Parameters: {days_threshold: 3}
  Status: Completed

[2025-10-26 14:30:18] Executive Chef → Sous Chef
  Action: suggest_recipes
  Parameters: {pantry_context: {...}, preferences: {...}}
  Status: Completed

[2025-10-26 14:30:45] Executive Chef → Sous Chef
  Action: adapt_recipe
  Parameters: {selection: 1, preferences: {...}}
  Status: Completed
```

---

## Quality Check Example

### Waiter QA Process

```
Quality Check Input:
- Recipe: Garlic Spinach Pasta
- User Preferences: {allergies: ["nuts"], restrictions: ["vegetarian"]}
- Conversation Context: Last 10 messages

Quality Check Analysis:

✅ PASSED: No allergens found (nut-free verified)
✅ PASSED: Dietary compliance (vegetarian confirmed)
✅ PASSED: Addresses user's original intent (quick vegetarian dinner)
✅ PASSED: Uses expiring ingredients (spinach)
✅ PASSED: Skill level appropriate (beginner)

Score: 95/100

Issues: None

Critical Failures: None
```

---

## Comparison: Simple vs Complex Flow

### Simple Pantry Request

```
Waiter → EC (analyze) → Agent Execute → Waiter Finalize
         ↓
    lightweight plan

Time: ~2 seconds
LLM Calls: 1
```

### Complex Recipe Request

```
Waiter → EC (analyze) → EC (plan) → Agent Execute (pantry)
         ↓               ↓           ↓
    complexity      full plan    Agent Execute (sous chef)
    analysis                     ↓
                                EC (synthesize) → Waiter (present)
                                ↓                ↓
                          synthesis         User selection
                                                ↓
                                         EC (adapt) → Agent Execute
                                                       ↓
                                                 Waiter (QA) → Final

Time: ~15 seconds
LLM Calls: 7
```

---

## Error Handling Examples

### Example 1: No Recipes Match Constraints

```
Sous Chef: No recipes found matching all constraints

Executive Chef: Executing fallback strategy...
  Relaxing constraint: "gluten-free" → "can be made gluten-free with substitutions"

New search: Found 3 recipes with gluten-free alternatives

Synthesis:
"I couldn't find recipes that are naturally gluten-free with your exact
ingredients, but here are 3 vegan recipes you can easily make gluten-free
by substituting regular pasta with rice noodles..."
```

### Example 2: Quality Check Failure

```
Waiter Quality Check Result:
{
  "passed": false,
  "issues": [
    "CRITICAL: Recipe contains soy sauce (user allergic to soy)"
  ],
  "critical_failures": ["allergen_present"]
}

Waiter: ⚠️  I found a safety concern with this recipe.
        It contains soy sauce, which conflicts with your soy allergy.

        Would you like me to:
        1. Find an alternative recipe
        2. Suggest a substitution (e.g., coconut aminos)
```

---

## Performance Metrics

| Request Type   | Complexity | Agents Used | LLM Calls | Time | Cost Estimate |
| -------------- | ---------- | ----------- | --------- | ---- | ------------- |
| Pantry check   | Simple     | 1           | 1         | 2s   | $0.001        |
| Recipe request | Medium     | 2           | 4         | 8s   | $0.005        |
| Complex recipe | Complex    | 3           | 7         | 15s  | $0.012        |
| Full workflow  | Complex    | 3           | 9         | 20s  | $0.015        |

\*Cost estimates based on GPT-4o-mini pricing

---

## Conclusion

The orchestration system successfully handles requests of varying complexity:

- **Simple requests**: Fast and efficient with minimal overhead
- **Medium requests**: Balanced synthesis with good user experience
- **Complex requests**: Full orchestration with comprehensive safety checks

All flows maintain:

- ✅ Complete delegation tracking
- ✅ Proper quality assurance
- ✅ Context-aware responses
- ✅ Waste reduction focus
- ✅ User safety first
