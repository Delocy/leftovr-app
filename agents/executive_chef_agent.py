import json
from typing import Dict, List, Any, Optional, Literal, Tuple
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


class ExecutiveChefAgent:
    """
    Executive Chef Agent - Orchestrator and Task Decomposer.

    Responsibilities:
    - Analyze user requests and determine complexity
    - Decompose complex queries into subtasks
    - Delegate tasks to appropriate subagents
    - Coordinate workflow between agents
    - Make strategic decisions about recipe selection
    - Perform quality checks on final outputs
    - Ensure all user constraints are satisfied
    """

    def __init__(self, name: str = "Executive Chef"):
        self.name = name
        self.task_history: List[Dict[str, Any]] = []
        self.delegation_log: List[Dict[str, Any]] = []

    def build_system_prompt(self) -> str:
        """Return the executive chef agent system prompt."""
        return """
        <system_prompt>
        YOU ARE THE "EXECUTIVE CHEF" — THE MASTER ORCHESTRATOR AND STRATEGIC DECISION-MAKER
        IN A MULTI-AGENT AI COOKING SYSTEM. YOUR PRIMARY ROLE IS TO ANALYZE USER REQUESTS,
        DECOMPOSE COMPLEX TASKS, DELEGATE TO SPECIALIZED AGENTS, AND ENSURE HIGH-QUALITY
        CULINARY SOLUTIONS.

        ###OBJECTIVE###
        YOUR GOAL IS TO COORDINATE THE ENTIRE COOKING ASSISTANCE WORKFLOW, MAKING INTELLIGENT
        DECISIONS ABOUT TASK COMPLEXITY, RESOURCE ALLOCATION, AND AGENT DELEGATION TO DELIVER
        OPTIMAL RECIPE RECOMMENDATIONS THAT REDUCE FOOD WASTE AND SATISFY USER PREFERENCES.

        ###RESPONSIBILITIES###
        1. **TASK ANALYSIS**: Evaluate incoming requests for complexity and requirements
        2. **DECOMPOSITION**: Break complex queries into manageable subtasks
        3. **DELEGATION**: Assign tasks to appropriate specialized agents
        4. **COORDINATION**: Manage workflow and inter-agent communication
        5. **QUALITY ASSURANCE**: Review outputs from subagents for completeness
        6. **STRATEGIC DECISIONS**: Choose between recipe options based on multiple factors
        7. **OPTIMIZATION**: Prioritize ingredients nearing expiration to reduce waste
        8. **CONSTRAINT SATISFACTION**: Ensure all user preferences and restrictions are met

        ###AGENT ECOSYSTEM###
        You coordinate these specialized agents:

        **Pantry Agent**:
        - Manages ingredient inventory via Google Sheets
        - Checks availability and quantities
        - Tracks expiration dates
        - Updates inventory after recipe preparation

        **Sous Chef Agent**:
        - Generates recipe suggestions based on available ingredients
        - Adapts recipes to user skill level
        - Provides step-by-step cooking instructions

        **Recipe Knowledge Agent**:
        - Retrieves recipes from vector database (Qdrant/Milvus)
        - Performs semantic search for recipe matching
        - Provides nutritional information and cooking tips

        **Quality Control Agent**:
        - Validates recipe completeness and safety
        - Checks allergen compliance
        - Verifies cooking instructions are clear

        **Waiter Agent**:
        - Collects user preferences (diet, allergies, skill level)
        - Communicates final results to user

        ###DECISION FRAMEWORK###

        **Query Type Classification**:
        1. **Simple Ingredient Query**: "What can I make with chicken?"
           → Delegate to: Pantry Agent → Sous Chef Agent

        2. **Recipe Request**: "I want pasta recipes"
           → Delegate to: Recipe Knowledge Agent → Quality Control Agent

        3. **Complex Multi-Constraint**: "Vegan recipes using ingredients expiring soon"
           → Delegate to: Pantry Agent → Recipe Knowledge Agent → Sous Chef Agent → Quality Control

        4. **Inventory Management**: "Update inventory after making carbonara"
           → Delegate to: Pantry Agent only

        **Complexity Assessment Criteria**:
        - Number of constraints (diet, allergies, cuisines, skill level)
        - Number of ingredients involved
        - Need for recipe customization
        - Expiration urgency
        - Shopping requirements

        **Prioritization Strategy**:
        1. **Expiration Priority**: Use ingredients expiring within 3 days first
        2. **Dietary Compliance**: Never suggest recipes violating restrictions
        3. **Skill Alignment**: Match recipe complexity to user skill level
        4. **Preference Matching**: Favor user's preferred cuisines
        5. **Ingredient Efficiency**: Minimize waste and maximize usage

        ###INSTRUCTIONS###
        1. **RECEIVE** handoff packet from Waiter Agent with user preferences
        2. **ANALYZE** query type and complexity level
        3. **CONSULT** Pantry Agent for current inventory and expiring items
        4. **DETERMINE** optimal recipe strategy (use-what-you-have vs. specific recipe)
        5. **DELEGATE** to appropriate agents in correct sequence
        6. **COLLECT** responses from subagents
        7. **SYNTHESIZE** information into coherent recommendation
        8. **VALIDATE** via Quality Control Agent
        9. **OPTIMIZE** for food waste reduction
        10. **RETURN** final recommendation to Waiter Agent for user delivery

        ###CHAIN OF THOUGHTS###
        1. **UNDERSTAND**: What is the user really asking for?
        2. **ASSESS**: How complex is this request? (simple/medium/complex)
        3. **INVENTORY**: What ingredients are available? What's expiring?
        4. **CONSTRAINTS**: What are the hard requirements? (allergies, diet, skill)
        5. **OPTIONS**: What recipe strategies are feasible?
        6. **PRIORITIZE**: Which option best reduces waste and satisfies user?
        7. **DELEGATE**: Which agents need to be involved and in what order?
        8. **INTEGRATE**: How do I combine subagent outputs into a solution?
        9. **VALIDATE**: Does this solution satisfy all constraints?
        10. **COMMUNICATE**: How do I present this clearly to the user?

        ###DELEGATION PATTERNS###

        **Pattern 1: Ingredient-First Recipe**
        User wants recipe using specific ingredients
        Flow: Pantry Check → Recipe Search → Sous Chef Adaptation → Quality Check

        **Pattern 2: Recipe-First Approach**
        User wants specific recipe type
        Flow: Recipe Retrieval → Ingredient Check → Substitution Planning → Quality Check

        **Pattern 3: Waste-Reduction Mode**
        Focus on using expiring ingredients
        Flow: Expiration Check → Ingredient Prioritization → Recipe Match → Validation

        **Pattern 4: Full Discovery**
        User has no specific request
        Flow: Inventory Analysis → Preference Matching → Multiple Options → User Choice

        ###QUALITY CRITERIA###
        A successful recommendation must:
        - ✅ Satisfy all dietary restrictions and allergies
        - ✅ Match user's cooking skill level
        - ✅ Use available ingredients OR provide clear shopping list
        - ✅ Prioritize ingredients nearing expiration
        - ✅ Include clear, actionable cooking instructions
        - ✅ Have valid nutritional information
        - ✅ Be culturally and culinarily appropriate

        ###WHAT NOT TO DO###
        - DO NOT SUGGEST RECIPES WITH USER'S ALLERGENS — this is dangerous
        - DO NOT SKIP PANTRY CHECK — always know what's available
        - DO NOT IGNORE EXPIRING INGREDIENTS — waste reduction is a core goal
        - DO NOT DELEGATE TO NON-EXISTENT AGENTS — stay within the system
        - DO NOT MAKE ASSUMPTIONS ABOUT USER SKILL — respect their level
        - DO NOT PROVIDE INCOMPLETE RECIPES — ensure all steps are included
        - DO NOT FORGET TO UPDATE INVENTORY — track consumption

        ###EXAMPLE SCENARIOS###

        **Scenario 1: Simple Request**
        Input: "What can I cook tonight?"
        Analysis: Open-ended, medium complexity
        Actions:
        1. Check pantry for available ingredients
        2. Identify expiring items (spinach, milk)
        3. Query Recipe Knowledge for spinach + milk recipes
        4. Filter by user skill level (home cook)
        5. Suggest: Spinach and Cheese Quiche
        Delegation: Pantry → Recipe Knowledge → Sous Chef → Quality Control

        **Scenario 2: Complex Constraint**
        Input: "Vegan dinner, no soy, beginner level, using tomatoes"
        Analysis: High complexity, multiple constraints
        Actions:
        1. Verify tomato availability and quantity
        2. Search vegan, soy-free recipes for beginners
        3. Cross-reference with available ingredients
        4. Generate 2-3 options
        5. Present with ingredient gaps and substitutions
        Delegation: Pantry → Recipe Knowledge → Sous Chef → Quality Control

        **Scenario 3: Expiration Alert**
        Input: System detects milk expires tomorrow
        Analysis: Proactive waste reduction
        Actions:
        1. Alert about expiring milk
        2. Find recipes prominently featuring milk
        3. Filter by user preferences
        4. Suggest: Creamy Pasta or Pancakes
        Delegation: Pantry → Recipe Knowledge → Sous Chef

        ###COMMUNICATION PROTOCOL###
        When delegating to agents, provide:
        - Clear task description
        - Relevant context (user preferences, constraints)
        - Expected output format
        - Priority level (urgent/normal/low)

        When receiving from agents, validate:
        - Completeness of information
        - Constraint satisfaction
        - Data quality and consistency

        ###OPTIMIZATION PRINCIPLES###
        1. **Minimize API Calls**: Cache agent responses when possible
        2. **Parallel Processing**: Query independent agents simultaneously
        3. **Early Filtering**: Apply hard constraints (allergies) first
        4. **Graceful Degradation**: Provide alternatives if ideal solution unavailable
        5. **User-Centric**: Always prioritize user safety and satisfaction

        </system_prompt>
        """

    def analyze_request_complexity(
        self,
        llm,
        user_preferences: Dict[str, Any],
        query_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze the complexity of a user request and determine processing strategy.

        Returns:
            Dict with 'complexity', 'strategy', 'required_agents', 'reasoning'
        """
        system_prompt = self.build_system_prompt()

        analysis_instruction = """
        Analyze the following user request and preferences to determine:
        1. Complexity level: "simple", "medium", or "complex"
        2. Optimal processing strategy
        3. Which agents to involve and in what order
        4. Reasoning for your decision

        Return ONLY valid JSON:
        {
            "complexity": "simple|medium|complex",
            "strategy": "ingredient_first|recipe_first|waste_reduction|full_discovery",
            "required_agents": ["agent1", "agent2", ...],
            "agent_sequence": ["first_agent", "second_agent", ...],
            "reasoning": "explanation",
            "priority_factors": ["factor1", "factor2", ...],
            "estimated_steps": number
        }
        """

        user_info = f"""
        User Preferences:
        {json.dumps(user_preferences, indent=2)}

        Query Context: {query_context or "General recipe request"}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{analysis_instruction}\n\n{user_info}")
        ]

        try:
            response = llm.invoke(messages)
            analysis = json.loads(response.content)

            # Log the analysis
            self.task_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'complexity_analysis',
                'analysis': analysis
            })

            return analysis

        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                'complexity': 'medium',
                'strategy': 'ingredient_first',
                'required_agents': ['pantry', 'sous_chef', 'quality_control'],
                'agent_sequence': ['pantry', 'sous_chef', 'quality_control'],
                'reasoning': 'Default analysis due to parsing error',
                'priority_factors': ['availability', 'preferences'],
                'estimated_steps': 3
            }

    def create_task_plan(
        self,
        llm,
        user_preferences: Dict[str, Any],
        complexity_analysis: Dict[str, Any],
        pantry_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a detailed execution plan with subtasks for each agent.

        Returns:
            Dict with 'tasks', 'delegation_order', 'success_criteria'
        """
        system_prompt = self.build_system_prompt()

        planning_instruction = """
        Create a detailed execution plan for fulfilling this user request.

        Return ONLY valid JSON:
        {
            "tasks": [
                {
                    "agent": "agent_name",
                    "action": "specific_action",
                    "input": "what to provide to agent",
                    "expected_output": "what agent should return",
                    "priority": "high|medium|low"
                }
            ],
            "delegation_order": ["agent1", "agent2", ...],
            "success_criteria": ["criterion1", "criterion2", ...],
            "expected_duration": "estimate in minutes",
            "fallback_strategy": "what to do if primary plan fails"
        }
        """

        context = f"""
        User Preferences:
        {json.dumps(user_preferences, indent=2)}

        Complexity Analysis:
        {json.dumps(complexity_analysis, indent=2)}
        """

        if pantry_context:
            context += f"\n\nPantry Context:\n{json.dumps(pantry_context, indent=2)}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{planning_instruction}\n\n{context}")
        ]

        try:
            response = llm.invoke(messages)
            plan = json.loads(response.content)

            # Log the plan
            self.task_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'task_planning',
                'plan': plan
            })

            return plan

        except json.JSONDecodeError:
            # Fallback plan
            return {
                'tasks': [
                    {
                        'agent': 'pantry',
                        'action': 'check_inventory',
                        'input': user_preferences,
                        'expected_output': 'available ingredients list',
                        'priority': 'high'
                    },
                    {
                        'agent': 'sous_chef',
                        'action': 'suggest_recipes',
                        'input': 'inventory + preferences',
                        'expected_output': 'recipe suggestions',
                        'priority': 'high'
                    }
                ],
                'delegation_order': ['pantry', 'sous_chef', 'quality_control'],
                'success_criteria': ['recipe_suggested', 'constraints_met'],
                'expected_duration': '5-10 minutes',
                'fallback_strategy': 'Suggest recipes with shopping list'
            }

    def decide_query_type(
        self,
        user_preferences: Dict[str, Any],
        pantry_available: bool = True,
        recipe_db_available: bool = True
    ) -> Literal["ingredient", "recipe"]:
        """
        Decide whether to use ingredient-first or recipe-first approach.

        This is a critical decision that affects the workflow routing.
        """
        # If pantry is not available, must use recipe-first
        if not pantry_available:
            return "recipe"

        # If recipe DB is not available, must use ingredient-first
        if not recipe_db_available:
            return "ingredient"

        # Check for explicit recipe requests in cuisines or preferences
        cuisines = user_preferences.get('cuisines', [])
        if cuisines and len(cuisines) > 0:
            # User has specific cuisine preferences - prefer recipe search
            return "recipe"

        # Check for dietary restrictions that might benefit from recipe DB
        restrictions = user_preferences.get('restrictions', [])
        allergies = user_preferences.get('allergies', [])
        if len(restrictions) + len(allergies) > 2:
            # Complex constraints - recipe DB better for filtering
            return "recipe"

        # Default to ingredient-first (use what you have - reduce waste)
        return "ingredient"

    def delegate_to_pantry(
        self,
        action: Literal["check_inventory", "check_expiring", "check_feasibility", "update_inventory"],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a delegation packet for Pantry Agent.

        Returns:
            Dict with delegation details to be processed by pantry agent
        """
        delegation = {
            'agent': 'pantry',
            'action': action,
            'parameters': parameters,
            'timestamp': datetime.now().isoformat(),
            'delegated_by': self.name
        }

        self.delegation_log.append(delegation)

        return delegation

    def delegate_to_sous_chef(
        self,
        action: Literal["suggest_recipes", "adapt_recipe", "generate_instructions"],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a delegation packet for Sous Chef Agent.
        """
        delegation = {
            'agent': 'sous_chef',
            'action': action,
            'parameters': parameters,
            'timestamp': datetime.now().isoformat(),
            'delegated_by': self.name
        }

        self.delegation_log.append(delegation)

        return delegation

    def delegate_to_recipe_knowledge(
        self,
        action: Literal["search_recipes", "get_recipe_details", "semantic_search"],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a delegation packet for Recipe Knowledge Agent.
        """
        delegation = {
            'agent': 'recipe_knowledge',
            'action': action,
            'parameters': parameters,
            'timestamp': datetime.now().isoformat(),
            'delegated_by': self.name
        }

        self.delegation_log.append(delegation)

        return delegation

    def delegate_to_quality_control(
        self,
        action: Literal["validate_recipe", "check_allergens", "verify_instructions"],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a delegation packet for Quality Control Agent.
        """
        delegation = {
            'agent': 'quality_control',
            'action': action,
            'parameters': parameters,
            'timestamp': datetime.now().isoformat(),
            'delegated_by': self.name
        }

        self.delegation_log.append(delegation)

        return delegation

    def synthesize_recommendations(
        self,
        llm,
        agent_responses: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> str:
        """
        Synthesize responses from multiple agents into a coherent recommendation.

        Args:
            agent_responses: Dict mapping agent names to their responses
            user_preferences: Original user preferences

        Returns:
            Formatted recommendation text
        """
        system_prompt = self.build_system_prompt()

        synthesis_instruction = """
        You are synthesizing responses from multiple specialized agents into a
        coherent, user-friendly recommendation. Create a warm, helpful message that:

        1. Acknowledges what ingredients are available
        2. Highlights any items expiring soon (to encourage their use)
        3. Presents 1-3 recipe options with:
           - Recipe name and brief description
           - Required ingredients (with availability status)
           - Cooking time and difficulty
           - Key steps overview
        4. Provides a shopping list if needed
        5. Offers alternatives or substitutions

        Be conversational, encouraging, and focused on reducing food waste.
        """

        context = f"""
        User Preferences:
        {json.dumps(user_preferences, indent=2)}

        Agent Responses:
        {json.dumps(agent_responses, indent=2, default=str)}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{synthesis_instruction}\n\n{context}")
        ]

        response = llm.invoke(messages)

        # Log synthesis
        self.task_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'synthesis',
            'output': response.content
        })

        return response.content

    def perform_quality_check(
        self,
        llm,
        recommendation: str,
        user_preferences: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Perform executive-level quality check on final recommendation.

        Returns:
            Tuple of (passed: bool, issues: List[str])
        """
        system_prompt = self.build_system_prompt()

        quality_instruction = """
        Review this recipe recommendation against the user's requirements.
        Check for:
        1. Allergen compliance (CRITICAL - must not contain user's allergens)
        2. Dietary restriction compliance (e.g., vegan, halal)
        3. Skill level appropriateness
        4. Ingredient availability transparency
        5. Clear cooking instructions
        6. Waste reduction focus (using expiring items)

        Return ONLY valid JSON:
        {
            "passed": true/false,
            "issues": ["issue1", "issue2", ...],
            "score": 0-100,
            "critical_failures": ["failure1", ...],
            "suggestions": ["suggestion1", ...]
        }
        """

        context = f"""
        User Preferences:
        {json.dumps(user_preferences, indent=2)}

        Recommendation:
        {recommendation}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{quality_instruction}\n\n{context}")
        ]

        try:
            response = llm.invoke(messages)
            result = json.loads(response.content)

            passed = result.get('passed', False)
            issues = result.get('issues', [])
            critical = result.get('critical_failures', [])

            # If there are critical failures, definitely fail
            if critical:
                passed = False
                issues.extend([f"CRITICAL: {cf}" for cf in critical])

            # Log quality check
            self.task_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'quality_check',
                'result': result
            })

            return passed, issues

        except json.JSONDecodeError:
            # If we can't parse response, assume it passed but log warning
            return True, ["Quality check response could not be parsed"]

    def orchestrate_full_workflow(
        self,
        llm,
        user_preferences: Dict[str, Any],
        pantry_agent,
        query_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate the complete workflow from user request to final recommendation.
        This is the main entry point for the Executive Chef.

        Args:
            llm: Language model for reasoning
            user_preferences: User's dietary preferences and constraints
            pantry_agent: Instance of PantryAgent
            query_context: Optional additional context about the user's request

        Returns:
            Dict with 'success', 'recommendation', 'metadata', 'issues'
        """
        print(f"\n🔷 {self.name}: Initiating workflow orchestration")

        # Step 1: Analyze complexity
        print(f"   Analyzing request complexity...")
        complexity = self.analyze_request_complexity(llm, user_preferences, query_context)
        print(f"   Complexity: {complexity['complexity']} | Strategy: {complexity['strategy']}")

        # Step 2: Check pantry status
        print(f"   Consulting Pantry Agent...")
        pantry_summary = pantry_agent.get_pantry_summary()
        expiring_items = pantry_agent.get_expiring_soon()

        print(f"   Pantry: {pantry_summary['total_ingredients']} ingredients, "
              f"{len(expiring_items)} expiring soon")

        if expiring_items:
            print(f"   ⚠️  Priority items: {', '.join([item['name'] for item in expiring_items[:3]])}")

        # Step 3: Create task plan
        print(f"   Creating execution plan...")
        plan = self.create_task_plan(
            llm,
            user_preferences,
            complexity,
            {'summary': pantry_summary, 'expiring': expiring_items}
        )

        # Step 4: Collect agent responses (stub - will be filled by actual agents)
        agent_responses = {
            'pantry': {
                'summary': pantry_summary,
                'expiring_items': expiring_items,
                'inventory': pantry_agent.get_inventory()
            },
            'complexity_analysis': complexity,
            'execution_plan': plan
        }

        # Step 5: Synthesize recommendation
        print(f"   Synthesizing recommendation...")
        recommendation = self.synthesize_recommendations(llm, agent_responses, user_preferences)

        # Step 6: Quality check
        print(f"   Performing quality check...")
        passed, issues = self.perform_quality_check(llm, recommendation, user_preferences)

        if not passed:
            print(f"   ❌ Quality check failed: {', '.join(issues)}")
        else:
            print(f"   ✅ Quality check passed")

        # Step 7: Return final result
        result = {
            'success': passed,
            'recommendation': recommendation,
            'metadata': {
                'complexity': complexity,
                'plan': plan,
                'pantry_summary': pantry_summary,
                'expiring_items': expiring_items,
                'task_history': self.task_history
            },
            'issues': issues if not passed else []
        }

        print(f"🔷 {self.name}: Workflow complete\n")

        return result

    def get_delegation_log(self) -> List[Dict[str, Any]]:
        """Return the full delegation log for debugging/monitoring."""
        return self.delegation_log

    def get_task_history(self) -> List[Dict[str, Any]]:
        """Return the full task history for debugging/monitoring."""
        return self.task_history

    def clear_logs(self):
        """Clear logs (useful for starting fresh workflow)."""
        self.task_history = []
        self.delegation_log = []

