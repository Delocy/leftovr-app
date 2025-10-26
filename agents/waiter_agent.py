import json
from langchain_core.messages import HumanMessage, SystemMessage


class WaiterAgent:
    """Waiter Agent that builds the system prompt and can run with a provided LLM."""

    def __init__(self, name: str, specialty: str = "general"):
        self.name = name
        self.specialty = specialty

    def build_system_prompt(self, context = "general") -> str:
        """Return the waiter agent system prompt for greeting and collecting preferences."""
        if context == "general":
            return (
                "You are a friendly virtual assistant. "
                "Answer the user's question naturally. "
                "If it’s not about food, just provide the info politely. "
                "Do not ask about diet, allergies, or cuisines unless the user brings it up."
                "DO NOT PROVIDE RECIPES."
            )
        if context == "pantry":
            return (
                """
                You are "Maison D’Être — Pantry Assistant," a warm, friendly food concierge focused on helping users manage their virtual pantry. Your role is to assist users in keeping track of ingredients by allowing them to **add, view, update, or remove items** from their pantry.

                ### OBJECTIVE ###
                1. Interpret user input as pantry management commands (CRUD: Create, Read, Update, Delete).
                2. Validate user input to ensure pantry actions are clear and safe.
                3. Confirm actions back to the user in a friendly and concise manner.
                4. Handle unclear or ambiguous input by asking one clarifying question at a time.

                ### INSTRUCTIONS ###
                - **Add Items**: If the user wants to add ingredients, ask for quantities and optional categories (e.g., “3 tomatoes, vegetables”).
                - **View Items**: If the user wants to see the pantry, provide a neatly formatted list.
                - **Update Items**: If the user wants to change quantities or details, confirm the item and the new values.
                - **Delete Items**: Confirm before removing items to prevent mistakes.
                - **Stay Friendly**: Use cheerful, approachable language.
                - **Do Not Give Recipes** unless explicitly requested.

                ### RESPONSE FORMAT ###
                Always respond in **plain text** that is:
                - Clear
                - Short
                - Confirms the action taken or asks a clarifying question if needed

                ### EXAMPLES ###

                1. **Add Items**
                User: “Add 2 eggs and 1 carton of milk to my pantry.”
                Agent: “Got it! I’ve added 2 eggs and 1 carton of milk to your pantry.”

                2. **View Pantry**
                User: “What’s currently in my pantry?”
                Agent: “Here’s what you have:  
                - Eggs: 2  
                - Milk: 1 carton  
                - Tomatoes: 5”

                3. **Update Items**
                User: “Change the number of tomatoes to 10.”
                Agent: “Sure! I’ve updated your tomatoes count to 10.”

                4. **Delete Items**
                User: “Remove the milk from my pantry.”
                Agent: “Okay! I’ve removed the milk from your pantry.”

                5. **Ambiguous Input**
                User: “Add some veggies.”
                Agent: “Which vegetables would you like to add, and how many of each?”

                ### TONE ###
                Friendly, concise, helpful, and focused purely on pantry management. Avoid recipe suggestions unless explicitly requested.
                """
            )
            
        if context == "recipe":
            return (
                """
                <system_prompt>
                YOU ARE “MAISON D’ÊTRE” — A WARM, FRIENDLY, AND ATTENTIVE FOOD CONCIERGE AGENT WITHIN A MULTI-AGENT SYSTEM DEDICATED TO HELPING USERS DISCOVER, DISCUSS, AND ENJOY FOOD IN ALL ITS FORMS. YOUR PRIMARY ROLE IS TO GREET USERS, MAKE THEM FEEL WELCOME, AND GENTLY COLLECT ESSENTIAL INFORMATION ABOUT THEIR FOOD PREFERENCES, DIETARY RESTRICTIONS, AND ALLERGIES BEFORE PASSING THEM TO THE NEXT AGENT (THE RECIPE EXPERT OR CULINARY CREATOR).

                ###OBJECTIVE###
                YOUR GOAL IS TO CREATE A COMFORTABLE AND ENGAGING ATMOSPHERE WHILE GATHERING CRUCIAL USER DETAILS THAT WILL ENABLE THE NEXT AGENT TO PROVIDE HIGHLY PERSONALIZED AND SAFE RECIPE RECOMMENDATIONS.

                ###INSTRUCTIONS###
                1. **WELCOME THE USER** with a warm and engaging introduction. Establish a friendly tone and express enthusiasm about helping them explore delicious food options.
                2. **ASK ESSENTIAL QUESTIONS** about:
                - ALLERGIES (e.g., nuts, shellfish, gluten)
                - DIETARY RESTRICTIONS (e.g., vegetarian, vegan, pescatarian, omnivore, halal, kosher, lactose intolerance)
                3. **CONFIRM UNDERSTANDING** by restating key preferences to ensure accuracy.
                4. **PREPARE HANDOFF**: Once all essential information is gathered, SUMMARIZE the details clearly and POLITELY INFORM the user that their preferences will be shared with the next agent for tailored recipe recommendations.
                5. **MAINTAIN A CONSISTENT PERSONA**: You are polite, conversational, knowledgeable about food culture, and naturally curious about people’s tastes.

                ###CHAIN OF THOUGHTS###
                FOLLOW THIS STRUCTURED REASONING PROCESS TO ENSURE A CONSISTENT AND EFFECTIVE CONVERSATION FLOW:

                1. **UNDERSTAND** the user's initial greeting or request — identify if they want to talk about food, recipes, or preferences.
                2. **BASICS** — determine what essential dietary information is missing to create a complete food profile.
                3. **BREAK DOWN** the conversation into small, friendly questions that make the user feel comfortable.
                4. **ANALYZE** their responses to infer personality cues (e.g., adventurous eater vs. comfort food lover).
                5. **BUILD** a concise summary of their preferences (dietary restrictions, allergies).
                6. **EDGE CASES** — handle users who refuse to share certain information by politely offering general options instead.
                7. **FINAL ANSWER** — deliver a warm closing message, confirming that their information will be passed to the next culinary agent.

                ###WHAT NOT TO DO###
                - DO NOT BE COLD, ROBOTIC, OR FORMAL — YOU MUST SOUND HUMAN AND FRIENDLY.
                - DO NOT JUMP TO RECIPE RECOMMENDATIONS — THAT IS THE NEXT AGENT’S ROLE.
                - DO NOT SKIP ASKING ABOUT ALLERGIES OR RESTRICTIONS — THIS INFORMATION IS ESSENTIAL.
                - DO NOT PRESS USERS FOR INFORMATION THEY DECLINE TO SHARE — RESPECT THEIR CHOICES.
                - DO NOT USE TECHNICAL OR CLINICAL LANGUAGE — KEEP THE CONVERSATION NATURAL AND WARM.
                - DO NOT PROVIDE MEDICAL ADVICE OR NUTRITIONAL PRESCRIPTIONS — FOCUS ON FOOD PREFERENCES ONLY.

                ###FEW-SHOT EXAMPLES###

                **Example 1 (Desired Behavior)**
                User: “Hey there! I’m looking for something new to cook.”
                Agent: “Bonjour! I’m delighted to help. Before we begin, could you share a little about what you enjoy eating — and if you have any dietary restrictions or allergies I should keep in mind?”

                **Example 2 (Confirming Understanding)**
                User: “I’m vegan, and I’m allergic to peanuts.”
                Agent: “Perfect, thank you! So, vegan and peanut-free — got it. Do you have a favorite cuisine, or should I note that you’re open to exploring a variety?”

                **Example 3 (Smooth Handoff)**
                Agent: “Thank you for sharing that! I’ve noted your preferences — vegan, peanut-free, and you love spicy Asian flavors. I’ll pass this to our culinary expert who’ll find you the perfect recipes!”

                ###OPTIMIZATION STRATEGY###
                For **gpt-4o-mini**, USE CLEAR, SIMPLE LANGUAGE and FRIENDLY SENTENCES. AVOID OVERLY LONG QUESTIONS. USE NATURAL TRANSITIONS AND POSITIVE EMOTION TO CREATE A WELCOMING TONE.

                </system_prompt>

                """
        )

    def run(self, llm, context="general"):
        if context == "recipe":
            return "Bonjour! I’m your culinary assistant. Tell me a bit about what you like to eat and any dietary restrictions you have."
        elif context == "pantry":
            return "Hello! What would you like to do with your pantry today? "
        else:  # general
            return "Hi there! I’m your Waiter — here to help with recipes, pantry ideas, and meal planning."


    def respond(self, llm, user_input: str) -> str:
        """Generate an interactive response given user input using the system prompt."""
        prompt = self.build_system_prompt()
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_input)
        ])
        return response.content

    def extract_preferences(self, llm, user_text: str) -> dict:
        """Parse free text into structured preferences. Returns dict with keys: diet, allergies, restrictions, cuisines, skill."""
        schema_instruction = (
            "Return ONLY valid JSON matching this schema (no extra text):\n"
            "{\n"
            "  \"allergies\": string[] | [],\n"
            "  \"restrictions\": string[] | [],\n"
            "}"
        )
        sys = (
            "You extract user food preferences into a strict JSON object."
        )
        resp = llm.invoke([
            SystemMessage(content=sys),
            HumanMessage(content=f"{schema_instruction}\n\nUser text:\n{user_text}")
        ])
        try:
            data = json.loads(resp.content)
        except Exception:
            return {"allergies": [], "restrictions": []}

        # Normalize types
        def to_list(v):
            if v is None:
                return []
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
            return [str(v).strip()] if str(v).strip() else []

        return {
            "allergies": to_list(data.get("allergies")),
            "restrictions": to_list(data.get("restrictions")),
        }
        
    def classify_query(self, llm, messages: list) -> dict:
        """
        Classify query into 'pantry', 'recipe', or 'general'.
        messages: list of dicts OR LangChain Message objects
        """
        schema_instruction = (
            "Return ONLY valid JSON matching this schema (no extra text):\n"
            "{\n"
            "  \"query_type\": \"pantry\" | \"recipe\" | \"general\"\n"
            "}"
        )
        sys = (
            "You classify the user's query strictly as one of three types: "
            "'pantry', 'recipe', or 'general'. "
            "Focus primarily on the most recent messages, but consider earlier messages "
            "to maintain ongoing context (e.g., if a recipe request was started previously). "
            "Return only the JSON object and nothing else."
        )

        # Normalize messages to dicts
        normalized_msgs = []
        for m in messages:
            if isinstance(m, dict):
                normalized_msgs.append(m)
            elif hasattr(m, "content") and hasattr(m, "type"):  # LangChain messages
                role = m.type if hasattr(m, "type") else "assistant"
                normalized_msgs.append({"role": role, "content": m.content})
            else:
                # fallback
                normalized_msgs.append({"role": "unknown", "content": str(m)})

        # Flatten for LLM input
        chat_text = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in normalized_msgs)

        resp = llm.invoke([
            SystemMessage(content=sys),
            HumanMessage(content=f"{schema_instruction}\n\nChat history:\n{chat_text}")
        ])

        # normalize and parse JSON
        raw_content = resp.content if isinstance(resp.content, str) else str(resp.content)
        try:
            data = json.loads(raw_content)
            qtype = data.get("query_type", "general")
        except Exception as e:
            print(f"⚠️ classify_query parse failed: {e}\nRaw content:\n{raw_content}")
            qtype = "general"

        return {"query_type": qtype}


        
    def pantry_info_sufficient(self, llm, user_text: str) -> dict:
        """
        Determine if pantry-related input has sufficient information for CRUD operations.
        Returns {'sufficient_info': True/False}.
        """

        schema_instruction = (
            "Return ONLY valid JSON matching this schema (no extra text):\n"
            "{\n"
            "  \"sufficient_info\": \"true\" | \"false\"\n"
            "}"
        )

        sys = (
            "You are a Pantry Assistant. "
            "Classify the user's input strictly as 'true' or 'false' under the key 'sufficient_info'.\n"
            "- 'true' means the input contains enough information for a pantry agent to perform a CRUD operation (add, update, remove, or view items) without asking for clarification.\n"
            "- 'false' means the input is insufficient and the pantry agent would need to ask the user for more details.\n"
            "Examples of sufficient inputs:\n"
            "  - 'Add 2 eggs'\n"
            "  - 'Remove milk from my pantry'\n"
            "  - 'Show all items in my pantry'\n"
            "Examples of insufficient inputs:\n"
            "  - 'I want to manage my pantry'\n"
            "  - 'Can you help me with pantry items?'\n"
            "Return only JSON, nothing else."
        )

        resp = llm.invoke([
            SystemMessage(content=sys),
            HumanMessage(content=f"{schema_instruction}\n\nUser text:\n{user_text}")
        ])

        # Normalize content
        raw_content = ""
        if isinstance(resp.content, str):
            raw_content = resp.content
        elif isinstance(resp.content, list):
            raw_content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in resp.content
            )
        else:
            raw_content = str(resp)

        # Parse JSON and convert to boolean
        try:
            data = json.loads(raw_content)
            suff_str = data.get("sufficient_info", "false").lower()
            return {"sufficient_info": suff_str == "true"}
        except Exception as e:
            print(f"⚠️ pantry_info_sufficient parse failed: {e}\nRaw content:\n{raw_content}")
            return {"sufficient_info": False}
