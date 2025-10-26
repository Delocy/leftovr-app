import json
from typing import Dict, List, Any, Optional, Literal, Tuple
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


class SousChefAgent:
    """
    Sous Chef Agent - Recipe Recommendation and Adaptation Specialist.

    Responsibilities:
    - Analyze pantry inventory and user preferences
    - Generate top N recipe recommendations
    - Score recipes based on ingredient availability and constraints
    - Suggest ingredient substitutions
    - Adapt selected recipes to dietary requirements
    - Communicate with Recipe Knowledge Agent and Pantry Agent
    - Provide detailed cooking instructions
    """

    def __init__(self, name: str = "Sous Chef", recipe_knowledge_agent=None):
        self.name = name
        self.recipe_knowledge_agent = recipe_knowledge_agent
        self.recommendation_history: List[Dict[str, Any]] = []
        self.adaptation_log: List[Dict[str, Any]] = []
        self.current_recommendations: List[Dict[str, Any]] = []
        self.selected_recipe: Optional[Dict[str, Any]] = None

    def build_system_prompt(self) -> str:
        """Return the sous chef agent system prompt."""
        return """
        <system_prompt>
        YOU ARE THE "SOUS CHEF" — THE CREATIVE RECIPE EXPERT AND CULINARY PROBLEM-SOLVER
        IN A MULTI-AGENT AI COOKING SYSTEM. YOUR PRIMARY ROLE IS TO PROPOSE RECIPES THAT
        MAXIMIZE USE OF AVAILABLE INGREDIENTS WHILE RESPECTING USER PREFERENCES, DIETARY
        RESTRICTIONS, AND SKILL LEVELS.

        ###OBJECTIVE###
        YOUR GOAL IS TO RECOMMEND 3 EXCELLENT RECIPE OPTIONS THAT MAKE THE BEST USE OF
        AVAILABLE INGREDIENTS, PRIORITIZE ITEMS NEARING EXPIRATION, RESPECT ALL DIETARY
        CONSTRAINTS, AND MATCH THE USER'S COOKING ABILITY — ULTIMATELY REDUCING FOOD WASTE
        AND DELIVERING SATISFYING MEALS.

        ###CORE RESPONSIBILITIES###
        1. **RECIPE RECOMMENDATION**: Generate top 3 recipe suggestions based on available ingredients
        2. **INGREDIENT OPTIMIZATION**: Maximize use of on-hand ingredients, especially expiring items
        3. **CONSTRAINT SATISFACTION**: Ensure recipes comply with dietary restrictions and allergies
        4. **SUBSTITUTION PLANNING**: Suggest appropriate ingredient substitutions when needed
        5. **RECIPE ADAPTATION**: Modify recipes to match user preferences and requirements
        6. **SCORING & RANKING**: Evaluate recipes based on multiple criteria
        7. **SHOPPING LIST GENERATION**: Identify missing ingredients and suggest where to buy
        8. **INTER-AGENT COMMUNICATION**: Coordinate with Recipe Knowledge Agent and Pantry Agent

        ###INGREDIENT ANALYSIS FRAMEWORK###

        **Availability Scoring**:
        - **Perfect Match** (100): All ingredients available in sufficient quantities
        - **Excellent** (80-99): 1-2 minor ingredients missing (e.g., garnishes, optional spices)
        - **Good** (60-79): 2-3 ingredients missing but easily substitutable
        - **Acceptable** (40-59): 3-4 ingredients missing, requires shopping trip
        - **Poor** (<40): 5+ ingredients missing, not recommended

        **Expiration Priority**:
        - **CRITICAL** (expires 0-1 days): Must use immediately — boost score by +30
        - **HIGH** (expires 2-3 days): Should use soon — boost score by +20
        - **MEDIUM** (expires 4-7 days): Plan to use this week — boost score by +10
        - **LOW** (expires 8+ days): No urgency — no boost

        **Substitution Quality**:
        - **Excellent**: Maintains flavor profile (e.g., butter → olive oil in pasta)
        - **Good**: Slight flavor change but acceptable (e.g., basil → parsley)
        - **Acceptable**: Noticeable difference (e.g., chicken → tofu)
        - **Poor**: Major flavor impact (e.g., beef → fish) — avoid unless necessary

        ###RECIPE SCORING ALGORITHM###

        **Base Score Calculation**:
        ```
        base_score = (pantry_items_used / total_ingredients) * 100
        expiration_boost = sum of priority boosts for expiring ingredients
        skill_match = 20 if recipe difficulty matches user skill, else -10
        dietary_compliance = 100 if compliant, else -1000 (disqualify)
        allergen_check = 0 if safe, else -10000 (immediate disqualification)
        
        final_score = base_score + expiration_boost + skill_match + dietary_compliance + allergen_check
        ```

        **Ranking Priorities** (in order):
        1. **Safety First**: NEVER suggest recipes with user's allergens
        2. **Dietary Compliance**: Respect vegan, halal, kosher, etc.
        3. **Waste Reduction**: Prioritize expiring ingredients
        4. **Ingredient Efficiency**: Use maximum number of pantry items
        5. **Skill Appropriateness**: Match user's cooking level
        6. **Preference Alignment**: Favor user's preferred cuisines

        ###RECIPE ADAPTATION CAPABILITIES###

        **Dietary Adaptations You Can Perform**:
        1. **Vegan Conversion**:
           - Replace eggs → flax eggs, aquafaba, or banana
           - Replace dairy → plant-based alternatives
           - Replace meat → tofu, tempeh, legumes
           - Replace honey → maple syrup, agave

        2. **Gluten-Free Conversion**:
           - Replace wheat flour → almond flour, rice flour, gluten-free blend
           - Replace pasta → rice noodles, zucchini noodles
           - Replace breadcrumbs → crushed gluten-free crackers
           - Check sauces and condiments for hidden gluten

        3. **Allergen Removal**:
           - Nuts → seeds (sunflower, pumpkin)
           - Shellfish → fish or plant-based alternatives
           - Soy → coconut aminos (for soy sauce)
           - Eggs → commercial egg replacers

        4. **Religious Dietary Laws**:
           - Halal: Remove pork/alcohol, ensure halal meat
           - Kosher: Separate meat/dairy, remove shellfish/pork
           - Hindu vegetarian: Remove all meat, eggs

        5. **Skill Level Adjustment**:
           - Beginner: Simplify techniques, reduce steps, suggest premade components
           - Home cook: Keep as-is with helpful tips
           - Expert: Add advanced techniques, flavor variations

        ###COMMUNICATION PROTOCOLS###

        **With Recipe Knowledge Agent**:
        - Request: "Find recipes using [ingredients] matching [preferences]"
        - Receive: List of candidate recipes with metadata
        - Process: Score, rank, filter for safety and compliance

        **With Pantry Agent**:
        - Request: "Check availability of [ingredient list]"
        - Receive: Availability status, quantities, expiration dates
        - Process: Calculate feasibility, plan substitutions

        **With Executive Chef**:
        - Receive: Strategic direction, user preferences, complexity level
        - Send: Top 3 recommendations with justifications
        - Respond: Adapt recipe based on feedback

        **Message Format**:
        {
            "from": "sous_chef",
            "to": "target_agent",
            "action": "action_type",
            "data": {...},
            "timestamp": "ISO-8601"
        }

        ###RECIPE RECOMMENDATION OUTPUT FORMAT###

        For each of the top 3 recipes, provide:
        ```json
        {
            "rank": 1,
            "title": "Creamy Spinach Pasta",
            "score": 92,
            "why_recommended": "Uses 8/10 pantry items including spinach (expires tomorrow)",
            "uses": [
                {"item": "spinach", "quantity": "2 cups", "status": "expires_tomorrow"},
                {"item": "pasta", "quantity": "400g", "status": "available"}
            ],
            "substitutions": [
                {
                    "from": "heavy cream",
                    "to": "coconut milk",
                    "why": "Vegan alternative, maintains creaminess",
                    "quality": "excellent"
                }
            ],
            "missing": [
                {
                    "item": "parmesan cheese",
                    "quantity": "50g",
                    "optional": false,
                    "store_note": "Available at any grocery store"
                }
            ],
            "tags": ["vegetarian", "30-minutes", "Italian"],
            "time_minutes": 25,
            "difficulty": "beginner",
            "servings": 4,
            "dietary_compliance": {
                "vegan": false,
                "vegetarian": true,
                "gluten_free": false,
                "allergen_free": ["nuts", "shellfish"]
            }
        }
        ```

        ###RECIPE ADAPTATION WORKFLOW###

        When user selects a recipe, you must:
        1. **CONFIRM SELECTION**: Acknowledge the user's choice
        2. **REVIEW CONSTRAINTS**: Check dietary restrictions and allergies
        3. **IDENTIFY MODIFICATIONS**: Determine necessary substitutions
        4. **VALIDATE SAFETY**: Ensure no allergens remain after adaptation
        5. **ADJUST DIFFICULTY**: Simplify/enhance based on skill level
        6. **PROVIDE INSTRUCTIONS**: Generate step-by-step cooking directions
        7. **SUGGEST VARIATIONS**: Offer optional enhancements

        **Adapted Recipe Output**:
        ```json
        {
            "original_title": "Chicken Parmesan",
            "adapted_title": "Vegan Eggplant Parmesan",
            "adaptations_made": [
                "Replaced chicken with eggplant slices",
                "Used vegan mozzarella and parmesan",
                "Replaced eggs in breading with flax eggs"
            ],
            "ingredients": [
                {"item": "eggplant", "quantity": "2 large", "form": "sliced 1/4 inch", "alternative": "zucchini"},
                {"item": "vegan mozzarella", "quantity": "200g", "form": "shredded", "alternative": "cashew cheese"}
            ],
            "steps": [
                {
                    "id": 1,
                    "text": "Salt eggplant slices and let sit 20 minutes to remove bitterness",
                    "time_minutes": 20,
                    "skill_note": "This step reduces bitterness and improves texture",
                    "depends_on": []
                }
            ],
            "cooking_time": {
                "prep": 30,
                "cook": 45,
                "total": 75
            },
            "difficulty_level": "intermediate",
            "safety_notes": [
                "Allergen-free: Contains no animal products, nuts, or soy",
                "Cross-contamination: Use separate cutting board if preparing for severe allergies"
            ]
        }
        ```

        ###INSTRUCTIONS###
        1. **RECEIVE** pantry summary and user preferences from Executive Chef
        2. **QUERY** Recipe Knowledge Agent for candidate recipes
        3. **SCORE** each recipe based on ingredient availability and constraints
        4. **FILTER** out any recipes with allergens or dietary conflicts
        5. **RANK** recipes by final score (highest first)
        6. **SELECT** top 3 recipes to recommend
        7. **PRESENT** recommendations with clear justifications
        8. **AWAIT** user selection (1, 2, or 3)
        9. **ADAPT** selected recipe if modifications needed
        10. **VALIDATE** final recipe for safety and completeness
        11. **COMMUNICATE** with Pantry Agent to reserve ingredients

        ###CHAIN OF THOUGHTS###
        1. **UNDERSTAND**: What ingredients are available? What's expiring?
        2. **CONSTRAINTS**: What are the hard requirements? (allergies, diet, skill)
        3. **QUERY**: What recipes match these ingredients and preferences?
        4. **ANALYZE**: Which recipes use the most pantry items?
        5. **SCORE**: Calculate scores considering all factors
        6. **FILTER**: Remove any unsafe or non-compliant options
        7. **RANK**: Order by final score (waste reduction + compliance)
        8. **JUSTIFY**: Why is each recipe a good choice?
        9. **PRESENT**: Show top 3 with clear reasoning
        10. **ADAPT**: If selected recipe needs modifications, how to adjust?
        11. **VALIDATE**: Is the adapted recipe safe and practical?

        ###WHAT NOT TO DO###
        - DO NOT SUGGEST RECIPES WITH USER'S ALLERGENS — This is life-threatening
        - DO NOT IGNORE DIETARY RESTRICTIONS — Respect religious/ethical choices
        - DO NOT RECOMMEND RECIPES BEYOND USER'S SKILL LEVEL — Set them up for success
        - DO NOT SKIP EXPIRING INGREDIENTS — Waste reduction is a core mission
        - DO NOT MAKE POOR SUBSTITUTIONS — Maintain recipe quality and flavor
        - DO NOT PROVIDE INCOMPLETE STEPS — Ensure instructions are clear and complete
        - DO NOT ASSUME INGREDIENT AVAILABILITY — Always verify with Pantry Agent
        - DO NOT OVERCOMPLICATE ADAPTATIONS — Keep modifications practical and simple

        ###FEW-SHOT EXAMPLES###

        **Example 1: Initial Recommendation**
        
        Input: User is vegan, beginner level, has: spinach (expires tomorrow), pasta, garlic, olive oil
        
        Output:
        "Based on your pantry, here are my top 3 recommendations:

        🥇 **Garlic Spinach Pasta** (Score: 95)
        Why: Uses 4/4 of your ingredients, including spinach that expires tomorrow!
        - Uses: spinach (2 cups, expires tomorrow), pasta (400g), garlic (4 cloves), olive oil (3 tbsp)
        - Missing: salt, pepper, red pepper flakes (optional)
        - Time: 20 minutes | Difficulty: Beginner
        - Perfect for: Quick weeknight dinner that prevents waste

        🥈 **Creamy Vegan Spinach Pasta** (Score: 88)
        Why: Uses all your greens plus adds richness with cashew cream
        - Uses: spinach (2 cups), pasta (400g), garlic (3 cloves), olive oil (2 tbsp)
        - Missing: cashews (1/2 cup), lemon juice (2 tbsp)
        - Time: 30 minutes | Difficulty: Beginner
        - Perfect for: Comfort food lovers

        🥉 **Spinach Pesto Pasta** (Score: 82)
        Why: Creative way to use expiring spinach in a pesto sauce
        - Uses: spinach (2 cups), pasta (400g), garlic (2 cloves), olive oil (1/2 cup)
        - Missing: pine nuts (1/4 cup), nutritional yeast (2 tbsp), lemon juice
        - Time: 25 minutes | Difficulty: Beginner
        - Perfect for: Making ahead for meal prep

        Which recipe would you like to make? (Reply 1, 2, or 3)"

        **Example 2: Recipe Adaptation**
        
        User selects Recipe #2, but is allergic to nuts

        Output:
        "Great choice! I'm adapting the Creamy Vegan Spinach Pasta to be nut-free:

        **Adapted Recipe: Creamy Vegan Spinach Pasta (Nut-Free)**

        ✅ Modifications Made:
        - Replaced cashew cream with silken tofu blend (nut-free, still creamy)
        - Added nutritional yeast for cheesy flavor

        **Ingredients You Have:**
        - 2 cups fresh spinach (use today!)
        - 400g pasta
        - 3 cloves garlic, minced
        - 2 tbsp olive oil

        **Ingredients to Buy:**
        - 200g silken tofu (soft or medium)
        - 2 tbsp lemon juice
        - 2 tbsp nutritional yeast
        - Salt and pepper to taste

        **Step-by-Step Instructions:**

        1. **Cook pasta** (10 min)
           - Boil salted water in large pot
           - Cook pasta according to package directions
           - Reserve 1 cup pasta water before draining

        2. **Prepare cream sauce** (5 min)
           - Blend silken tofu + lemon juice + nutritional yeast + 1/4 tsp salt until smooth
           - Set aside

        3. **Sauté aromatics** (3 min)
           - Heat olive oil in large pan over medium heat
           - Add minced garlic, cook until fragrant (1-2 minutes)

        4. **Wilt spinach** (2 min)
           - Add spinach to pan
           - Cook until just wilted (important: use this today!)

        5. **Combine** (2 min)
           - Add cooked pasta to pan
           - Pour in tofu cream sauce
           - Toss to combine, add pasta water if needed for consistency
           - Season with salt and pepper

        **Beginner Tips:**
        - Don't overcook spinach — it should be bright green
        - Save some pasta water — it helps sauce stick to pasta
        - Taste and adjust seasoning at the end

        ⏱️ Total Time: 22 minutes
        🍽️ Servings: 4
        💪 Difficulty: Beginner-friendly
        ✅ Allergen Status: Nut-free, Vegan

        Ready to start cooking? I'll guide you through any step!"

        **Example 3: Handling Missing Critical Ingredient**
        
        User wants recipe but is missing key ingredient

        Output:
        "I notice this recipe requires tomato sauce, which isn't in your pantry. Here are your options:

        **Option 1: Substitute** (Recommended)
        Use what you have: Crush canned tomatoes (if available) or make a cream-based sauce instead

        **Option 2: Simplify**
        Remove tomato component and make Aglio e Olio style (garlic & oil pasta)

        **Option 3: Shop**
        Quick shopping list: 1 can tomato sauce ($2-3, available at any grocery store)

        Which would you prefer?"

        ###OPTIMIZATION STRATEGY###
        - **Clarity**: Use simple language, avoid culinary jargon for beginners
        - **Safety**: Triple-check allergen compliance before recommending
        - **Waste Focus**: Always highlight expiring ingredients
        - **Practical**: Ensure substitutions are commonly available
        - **Supportive**: Encourage users and provide helpful cooking tips
        - **Efficient**: Prioritize recipes that minimize shopping needs

        ###SUCCESS METRICS###
        A successful recommendation achieves:
        - ✅ Zero allergen violations (critical)
        - ✅ Full dietary compliance (vegan, halal, etc.)
        - ✅ Uses 60%+ of available ingredients
        - ✅ Prioritizes expiring items (within 3 days)
        - ✅ Matches user skill level
        - ✅ Clear, actionable instructions
        - ✅ Realistic cooking time
        - ✅ Positive user feedback

        </system_prompt>
        """

    def generate_recommendations(
        self,
        llm,
        pantry_summary: Dict[str, Any],
        user_preferences: Dict[str, Any],
        expiring_items: List[Dict[str, Any]],
        recipe_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate top 3 recipe recommendations based on pantry and preferences.
        
        Args:
            llm: Language model for reasoning
            pantry_summary: Summary of pantry inventory
            user_preferences: User's dietary preferences and constraints
            expiring_items: List of items expiring soon
            recipe_results: Optional pre-fetched recipe results from Recipe Knowledge Agent
            
        Returns:
            List of top 3 recipe recommendations
        """
        print(f"\n👨‍🍳 {self.name}: Analyzing recipes and generating recommendations...")
        
        system_prompt = self.build_system_prompt()
        
        context = {
            "pantry_summary": pantry_summary,
            "user_preferences": user_preferences,
            "expiring_items": expiring_items,
            "recipe_results": recipe_results[:10] if recipe_results else []  # Top 10 for analysis
        }
        
        instruction = """
        Based on the provided pantry inventory, user preferences, and recipe results,
        generate your TOP 3 recipe recommendations.
        
        CRITICAL REQUIREMENTS:
        1. NEVER recommend recipes containing user's allergens
        2. Respect dietary restrictions (vegan, halal, kosher, etc.)
        3. Prioritize recipes using expiring ingredients
        4. Match user's cooking skill level
        5. Maximize use of available pantry items
        
        Return ONLY valid JSON in this format:
        {
            "recommendations": [
                {
                    "rank": 1,
                    "recipe_id": "id_from_results",
                    "title": "Recipe Name",
                    "score": 95,
                    "why_recommended": "Brief justification",
                    "pantry_items_used": 8,
                    "total_ingredients": 10,
                    "missing_ingredients": ["item1", "item2"],
                    "expiring_items_used": ["spinach"],
                    "time_minutes": 25,
                    "difficulty": "beginner",
                    "tags": ["vegetarian", "quick"],
                    "allergen_safe": true,
                    "dietary_compliant": true
                }
            ],
            "recommendation_summary": "Brief explanation of why these are the best choices"
        }
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{instruction}\n\nContext:\n{json.dumps(context, indent=2, default=str)}")
        ]
        
        try:
            response = llm.invoke(messages)
            
            response_text = response.content.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            result = json.loads(response_text)
            recommendations = result.get("recommendations", [])
            if not recommendations and recipe_results:
                recommendations = self.build_fallback_recommendations(recipe_results, user_preferences)
                print("⚠️  Using fallback recommendations due to parsing issues")
            
            self.current_recommendations = recommendations
            
            # Log the recommendations
            self.recommendation_history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "generate_recommendations",
                "context": context,
                "recommendations": recommendations
            })
            
            print(f"✅ Generated {len(recommendations)} recommendations")
            return recommendations
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse recommendation response: {e}")
            print(f"Response was: {response.content[:200]}...")
            return []
        except Exception as e:
            print(f"❌ Error generating recommendations: {e}")
            return []

    def present_recommendations(
        self,
        llm,
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """
        Format recommendations for user-friendly presentation.
        
        Args:
            llm: Language model for formatting
            recommendations: List of recipe recommendations
            
        Returns:
            Formatted string for user presentation
        """
        system_prompt = self.build_system_prompt()
        
        instruction = """
        Present these recipe recommendations to the user in a warm, engaging way.
        
        Format:
        - Use emojis for visual appeal (🥇 🥈 🥉)
        - Highlight why each recipe is recommended
        - Emphasize expiring ingredients being used
        - Show missing ingredients clearly
        - Include time and difficulty
        - End with: "Which recipe would you like to make? (Reply 1, 2, or 3)"
        
        Be conversational, encouraging, and focus on waste reduction!
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{instruction}\n\nRecommendations:\n{json.dumps(recommendations, indent=2)}")
        ]
        
        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"❌ Error formatting recommendations: {e}")
            # Fallback to basic formatting
            output = "Here are my top 3 recommendations:\n\n"
            for i, rec in enumerate(recommendations[:3], 1):
                output += f"{i}. {rec.get('title', 'Unknown Recipe')} (Score: {rec.get('score', 0)})\n"
                output += f"   Time: {rec.get('time_minutes', '?')} minutes | "
                output += f"Difficulty: {rec.get('difficulty', 'unknown')}\n\n"
            output += "Which recipe would you like to make? (Reply 1, 2, or 3)"
            return output

    def handle_user_selection(
        self,
        selection: int,
        recipe_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle user's recipe selection.
        
        Args:
            selection: User's choice (1, 2, or 3)
            recipe_results: Full recipe results from Recipe Knowledge Agent
            
        Returns:
            Selected recipe data or None if invalid selection
        """
        if not 1 <= selection <= 3:
            print(f"❌ Invalid selection: {selection}. Please choose 1, 2, or 3.")
            return None
        
        if not self.current_recommendations:
            if recipe_results:
                print("⚠️  No cached recommendations, falling back to raw recipe results")
                self.current_recommendations = recipe_results[:3]
            else:
                print(f"❌ No current recommendations available")
                return None
        
        if selection > len(self.current_recommendations):
            print(f"❌ Selection {selection} out of range")
            return None
        
        # Get the selected recommendation
        selected_rec = self.current_recommendations[selection - 1]
        recipe_id = selected_rec.get("recipe_id")
        
        # Find full recipe data
        selected_recipe = None
        for recipe in recipe_results:
            if recipe.get("id") == recipe_id or recipe.get("title") == selected_rec.get("title"):
                selected_recipe = recipe
                break
        
        if not selected_recipe:
            print(f"⚠️  Could not find full recipe data, using recommendation data")
            selected_recipe = selected_rec
        
        self.selected_recipe = selected_recipe
        
        print(f"✅ User selected: {selected_recipe.get('title', 'Unknown')}")
        
        return selected_recipe

    def adapt_recipe(
        self,
        llm,
        recipe: Dict[str, Any],
        user_preferences: Dict[str, Any],
        pantry_inventory: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Adapt the selected recipe based on dietary requirements and preferences.
        
        Args:
            llm: Language model for adaptation
            recipe: Selected recipe data
            user_preferences: User's preferences and restrictions
            pantry_inventory: Current pantry inventory
            
        Returns:
            Adapted recipe with modifications
        """
        print(f"\n🔧 {self.name}: Adapting recipe to meet dietary requirements...")
        
        system_prompt = self.build_system_prompt()
        
        instruction = """
        Adapt this recipe to meet the user's dietary requirements and preferences.
        
        CRITICAL SAFETY CHECKS:
        1. Remove ALL ingredients matching user's allergies
        2. Ensure recipe complies with dietary restrictions (vegan, halal, etc.)
        3. Provide safe substitutions for removed ingredients
        4. Double-check final recipe has NO allergens
        
        Adaptation Steps:
        1. Identify ingredients that violate dietary requirements
        2. Find appropriate substitutions
        3. Adjust cooking instructions if needed
        4. Simplify/enhance based on skill level
        5. Provide shopping list for missing items
        6. Add helpful cooking tips for beginners
        
        Return ONLY valid JSON in this format:
        {
            "original_title": "Original Recipe Name",
            "adapted_title": "Adapted Recipe Name",
            "adaptations_made": [
                "Replaced chicken with tofu for vegan diet",
                "Removed peanuts due to allergy"
            ],
            "ingredients": [
                {
                    "item": "ingredient name",
                    "quantity": "amount",
                    "unit": "measurement",
                    "form": "preparation",
                    "alternative": "substitute if needed",
                    "available_in_pantry": true/false
                }
            ],
            "steps": [
                {
                    "id": 1,
                    "text": "Step instruction",
                    "time_minutes": 10,
                    "skill_note": "Helpful tip for this step",
                    "depends_on": []
                }
            ],
            "cooking_time": {
                "prep": 20,
                "cook": 30,
                "total": 50
            },
            "difficulty_level": "beginner|intermediate|advanced",
            "servings": 4,
            "safety_notes": [
                "Allergen-free verification",
                "Cross-contamination warnings if needed"
            ],
            "shopping_list": [
                {
                    "item": "ingredient",
                    "quantity": "amount",
                    "estimated_cost": "$X-Y",
                    "where_to_buy": "any grocery store"
                }
            ],
            "waste_reduction_note": "This recipe uses [expiring ingredients]"
        }
        """
        
        context = {
            "recipe": recipe,
            "user_preferences": user_preferences,
            "pantry_inventory": pantry_inventory
        }
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{instruction}\n\nContext:\n{json.dumps(context, indent=2, default=str)}")
        ]
        
        try:
            response = llm.invoke(messages)
            
            response_text = response.content.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            adapted_recipe = json.loads(response_text)
            
            self.adaptation_log.append({
                "timestamp": datetime.now().isoformat(),
                "action": "adapt_recipe",
                "original_recipe": recipe.get("title"),
                "adapted_recipe": adapted_recipe.get("adapted_title"),
                "adaptations": adapted_recipe.get("adaptations_made", [])
            })
            
            print(f"✅ Recipe adapted successfully")
            print(f"   Adaptations made: {len(adapted_recipe.get('adaptations_made', []))}")
            
            return adapted_recipe
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse adaptation response: {e}")
            print(f"Response was: {response.content[:200]}...")
            return {"error": "Failed to adapt recipe", "original_recipe": recipe}
        except Exception as e:
            print(f"❌ Error adapting recipe: {e}")
            return {"error": str(e), "original_recipe": recipe}

    def format_adapted_recipe(
        self,
        llm,
        adapted_recipe: Dict[str, Any]
    ) -> str:
        """
        Format adapted recipe for user-friendly presentation.
        
        Args:
            llm: Language model for formatting
            adapted_recipe: Adapted recipe data
            
        Returns:
            Formatted string for user presentation
        """
        system_prompt = self.build_system_prompt()
        
        instruction = """
        Present this adapted recipe to the user in a clear, step-by-step format.
        
        Format Requirements:
        - Start with adapted recipe title
        - Show what modifications were made
        - List all ingredients with quantities (mark which are in pantry with ✅)
        - Provide numbered step-by-step instructions
        - Include timing for each step
        - Add beginner-friendly tips
        - Show total cooking time
        - Include safety notes about allergens
        - End with shopping list if needed
        
        Be warm, encouraging, and supportive. Make the user feel confident!
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{instruction}\n\nAdapted Recipe:\n{json.dumps(adapted_recipe, indent=2, default=str)}")
        ]
        
        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"❌ Error formatting adapted recipe: {e}")
            title = adapted_recipe.get("adapted_title", "Adapted Recipe")
            output = f"# {title}\n\n"
            
            adaptations = adapted_recipe.get("adaptations_made", [])
            if adaptations:
                output += "## Modifications Made:\n"
                for mod in adaptations:
                    output += f"- {mod}\n"
                output += "\n"
            
            ingredients = adapted_recipe.get("ingredients", [])
            if ingredients:
                output += "## Ingredients:\n"
                for ing in ingredients:
                    mark = "✅" if ing.get("available_in_pantry") else "🛒"
                    output += f"{mark} {ing.get('quantity')} {ing.get('unit', '')} {ing.get('item')}\n"
                output += "\n"
            
            steps = adapted_recipe.get("steps", [])
            if steps:
                output += "## Instructions:\n"
                for step in steps:
                    output += f"{step.get('id')}. {step.get('text')} ({step.get('time_minutes')}min)\n"
                output += "\n"
            
            cooking_time = adapted_recipe.get("cooking_time", {})
            output += f"⏱️ Total Time: {cooking_time.get('total', '?')} minutes\n"
            
            return output

    def build_fallback_recipe_summary(
        self,
        recipe: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> str:
        """
        Construct a lightweight fallback recipe summary when adaptation fails.
        
        Args:
            recipe: Original recipe data from Recipe Knowledge Agent
            user_preferences: User dietary preferences (for contextual tips)
        
        Returns:
            Human-readable markdown summary.
        """
        title = recipe.get("title", "Selected Recipe")
        ingredients = recipe.get("ingredients", [])
        missing = recipe.get("missing_ingredients", [])
        link = recipe.get("link")
        prefs_note = []
        if user_preferences.get("diet") and user_preferences.get("diet") != "omnivore":
            prefs_note.append(f"Diet: {user_preferences['diet']}")
        if user_preferences.get("allergies"):
            prefs_note.append("Avoid: " + ", ".join(user_preferences["allergies"]))
        if user_preferences.get("skill"):
            prefs_note.append(f"Skill level: {user_preferences['skill']}")

        lines = [f"# {title}", ""]
        if prefs_note:
            lines.append("_Preferences noted: " + " | ".join(prefs_note) + "_")
            lines.append("")
        lines.append("## Ingredients to Gather")
        if ingredients:
            for item in ingredients:
                lines.append(f"- {item}")
        else:
            lines.append("- Ingredient list unavailable in dataset")
        lines.append("")
        if missing:
            lines.append("### Items to shop for")
            for item in missing:
                lines.append(f"- 🛒 {item}")
            lines.append("")
        if link:
            lines.append(f"[View full instructions online]({link})")
            lines.append("")
        lines.append("> Unable to fully customize this recipe automatically. Follow the original instructions and adjust seasonings to taste.")
        return "\n".join(lines)

    def build_fallback_recommendations(
        self,
        recipe_results: List[Dict[str, Any]],
        user_preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate a simple deterministic top-3 recommendation list."""
        fallback = []
        for rank, recipe in enumerate(recipe_results[:3], 1):
            fallback.append({
                "rank": rank,
                "recipe_id": recipe.get("id"),
                "title": recipe.get("title", f"Recipe {rank}"),
                "score": float(recipe.get("score", 0)),
                "why_recommended": "High overlap with your pantry items.",
                "pantry_items_used": recipe.get("pantry_items_used", 0),
                "total_ingredients": len(recipe.get("ingredients", [])),
                "missing_ingredients": recipe.get("missing_ingredients", []),
                "expiring_items_used": [],
                "time_minutes": recipe.get("time_minutes") or "?",
                "difficulty": recipe.get("difficulty") or user_preferences.get("skill", "intermediate"),
                "tags": [],
                "allergen_safe": True,
                "dietary_compliant": True,
                "link": recipe.get("link")
            })
        return fallback

    def create_message_to_agent(
        self,
        target_agent: Literal["recipe_knowledge", "pantry", "executive_chef", "quality_control"],
        action: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a standardized message to send to another agent.
        
        Args:
            target_agent: Target agent identifier
            action: Action type
            data: Message data payload
            
        Returns:
            Formatted message dictionary
        """
        message = {
            "from": "sous_chef",
            "to": target_agent,
            "action": action,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        return message

    def request_recipes_from_knowledge_agent(
        self,
        pantry_items: List[str],
        user_preferences: Dict[str, Any],
        allow_missing: int = 2
    ) -> Dict[str, Any]:
        """
        Request recipe recommendations from Recipe Knowledge Agent.
        
        Args:
            pantry_items: Available ingredients
            user_preferences: User's dietary preferences
            allow_missing: Maximum number of missing ingredients allowed
            
        Returns:
            Message to send to Recipe Knowledge Agent
        """
        return self.create_message_to_agent(
            target_agent="recipe_knowledge",
            action="search_recipes",
            data={
                "pantry_items": pantry_items,
                "preferences": user_preferences,
                "allow_missing": allow_missing,
                "top_k": 20 
            }
        )

    def check_ingredient_availability(
        self,
        required_ingredients: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check ingredient availability with Pantry Agent.
        
        Args:
            required_ingredients: List of required ingredients for recipe
            
        Returns:
            Message to send to Pantry Agent
        """
        return self.create_message_to_agent(
            target_agent="pantry",
            action="check_feasibility",
            data={
                "required_ingredients": required_ingredients
            }
        )

    def get_recommendation_history(self) -> List[Dict[str, Any]]:
        """Return the full recommendation history for debugging/monitoring."""
        return self.recommendation_history

    def get_adaptation_log(self) -> List[Dict[str, Any]]:
        """Return the full adaptation log for debugging/monitoring."""
        return self.adaptation_log

    def clear_logs(self):
        """Clear logs (useful for starting fresh workflow)."""
        self.recommendation_history = []
        self.adaptation_log = []
        self.current_recommendations = []
        self.selected_recipe = None


# Helper function for integration
def sous_chef_workflow(
    llm,
    pantry_summary: Dict[str, Any],
    user_preferences: Dict[str, Any],
    expiring_items: List[Dict[str, Any]],
    recipe_results: List[Dict[str, Any]],
    pantry_inventory: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Complete Sous Chef workflow: recommend -> select -> adapt.
    
    Args:
        llm: Language model
        pantry_summary: Pantry summary
        user_preferences: User preferences
        expiring_items: Expiring items list
        recipe_results: Recipe results from Recipe Knowledge Agent
        pantry_inventory: Full pantry inventory
        
    Returns:
        Dict with recommendations, selected recipe, and adapted recipe
    """
    sous_chef = SousChefAgent()
    
    # Step 1: Generate recommendations
    recommendations = sous_chef.generate_recommendations(
        llm, pantry_summary, user_preferences, expiring_items, recipe_results
    )
    
    if not recommendations:
        return {"error": "Failed to generate recommendations"}
    
    # Step 2: Present to user
    presentation = sous_chef.present_recommendations(llm, recommendations)
    print("\n" + "="*80)
    print(presentation)
    print("="*80 + "\n")
    
    # Step 3: Get user selection
    selection = 1
    print(f"[Auto-selecting recipe #{selection} for demo]\n")
    
    selected_recipe = sous_chef.handle_user_selection(selection, recipe_results)
    
    if not selected_recipe:
        return {"error": "Failed to handle selection"}
    
    # Step 4: Adapt recipe
    adapted_recipe = sous_chef.adapt_recipe(
        llm, selected_recipe, user_preferences, pantry_inventory
    )
    
    # Step 5: Format for presentation
    formatted_recipe = sous_chef.format_adapted_recipe(llm, adapted_recipe)
    print("\n" + "="*80)
    print("🍳 YOUR PERSONALIZED RECIPE")
    print("="*80)
    print(formatted_recipe)
    print("="*80 + "\n")
    
    return {
        "recommendations": recommendations,
        "selected_recipe": selected_recipe,
        "adapted_recipe": adapted_recipe,
        "formatted_output": formatted_recipe
    }