# ============================================================================
# MCP CLIENT: OPENAI INTEGRATION
# ============================================================================

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio
import os
from dotenv import load_dotenv
import openai
from langchain_openai import ChatOpenAI
from .mcp_server import PantryMCPServer
from database.database import PantryDatabase
from datetime import datetime, timedelta, date
import uuid
from pydantic import BaseModel

print("Setting up Pantry MCP Client...")

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")

# Optional LangChain client
llm = ChatOpenAI(
    model="gpt-5-nano",
    temperature=0.7,
    api_key=OPENAI_API_KEY
)


def _deterministic_food_id(name: str) -> str:
    """Generate a deterministic, clean ID from food name."""
    return name.strip().lower().replace(' ', '-')

def _default_expiry() -> str:
    """Generate default expiry date 14 days from today"""
    return (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

class PantryMCPClient:
    """AI client that interacts with PantryMCPServer to answer user queries."""

    def __init__(self, mcp_server: PantryMCPServer):
        self.mcp_server = mcp_server
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

        self.system_prompt = """
        You are an expert Food Pantry AI Assistant with access to real-time inventory data.

        Your role:
        - Help users manage pantry inventory.
        - Interpret natural language statements about food usage, consumption, or restocking.
        - Suggest actionable recommendations.

        Tools you can use:
        - get_all_food_items
        - get_expiring_soon
        - get_food_item
        - add_food_item
        - update_food_item
        - delete_food_item

        - If the user mentions multiple items in one statement, produce one structured tool call per item.
        - Each call must include name, quantity, and optionally expire_date.
        - For any new food item:
            - If `expire_date` is not specified, automatically assign a 14-day default expiry.
            - If the item is generic (like "Vegetables") and no type is specified, add it as-is without asking for clarification.
            
        Semantic guidance:
        If the user mentions consuming, using, or eating an item:
            - Always produce a structured tool call to `update_food_item`.
            - Use negative quantity if decreasing inventory.
            - Generate an ID deterministically from the item name if unknown.
            - Do NOT call `get_all_food_items` unless explicitly requested by the user.
        - If the user mentions removing spoiled or unwanted items, call `delete_food_item`.
        - Only use `get_all_food_items` or `get_food_item` when the user explicitly wants to view inventory.
        - Always return structured actions for tool calls; infer quantities from user text.

        Example:
        - "I ate 2 eggs" → call `update_food_item` with quantity = current - 2
        - "Add 5 oranges" → call `add_food_item` with quantity = 5
        - "I have 2 eggs" → call `add_food_item` with quantity = 2
        - "i bought 1 egg and 2 oranges and 3 vegetables" → produce three calls: one for each item
        
        Always respond with a structured tool call if the user wants to add, consume, or remove items.
        Do not respond in text only. Only explain **after** executing the tool call.
        """


    def _convert_tools_to_openai_format(self) -> List[Dict[str, Any]]:
        """Convert MCP tools into OpenAI function format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self.mcp_server.tools.values()
        ]

    async def _execute_function_calls(self, function_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute any function calls requested by the model."""
        results = []
        for call in function_calls:
            function_name = call['function']['name']
            arguments = json.loads(call['function']['arguments'])
            result = await self.mcp_server.execute_tool(function_name, arguments)
            results.append({"call_id": call['id'], "function_name": function_name, "result": result})
        return results

    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query and execute MCP tool calls reliably."""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_query}
            ]

            tools = self._convert_tools_to_openai_format()

            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=messages,
                tools=tools,
                tool_choice="required"
            )

            message = response.choices[0].message
            tool_results = []

            # Process GPT tool calls
            for call in getattr(message, "tool_calls", []) or []:
                args = json.loads(call.function.arguments)

                # Ensure deterministic ID for all items
                if "id" not in args or not args["id"]:
                    args["id"] = _deterministic_food_id(args.get("name", ""))

                # Set default expiry for new additions
                if call.function.name == "add_food_item" and "expire_date" not in args:
                    args["expire_date"] = _default_expiry()

                # Directly call the server — let server handle quantity addition or subtraction
                result = await self.mcp_server.execute_tool(call.function.name, args)
                tool_results.append({"tool_name": call.function.name, "data": result})
                
                # messages.append({
                #     "role": "system",
                #     "tool_call_id": call.id,
                #     "name": call.function.name,
                #     "content": json.dumps(result)
                # })

            # Optionally, get final response from GPT after executing actions
            # final_response = self.client.chat.completions.create(
            #     model="gpt-5-nano",
            #     messages=messages,
            # )

            return {
                "success": True,
                "tools_used": [r["tool_name"] for r in tool_results],
                "tool_outputs": tool_results,
                "query": user_query,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "Error processing request. Please try again.",
                "query": user_query,
                "timestamp": datetime.now().isoformat()
            }
