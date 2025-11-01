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


class PantryMCPClient:
    """AI client that interacts with PantryMCPServer to answer user queries."""

    def __init__(self, mcp_server: PantryMCPServer):
        self.mcp_server = mcp_server
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

        self.system_prompt = """You are an expert Food Pantry AI Assistant with access to real-time inventory data.

        Your role is to help users understand the pantry inventory, identify items that are low or expired, and provide actionable recommendations.

        You have access to these tools:
        - get_inventory_status: Check current inventory levels including quantity and expiry
        - get_low_stock_items: Find items that need replenishment
        - check_product_availability: Check availability for a specific food item
        - get_products: Browse food items by category

        Guidelines:
        - Always use relevant tools to get current data
        - Provide clear, actionable insights for pantry management
        - Highlight risks such as low stock or expired items
        - Suggest practical actions
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
        """Process a user query and optionally execute MCP tool calls."""
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
                tool_choice="auto"
            )

            message = response.choices[0].message

            if getattr(message, "tool_calls", None):
                # Model requested function/tool calls
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {"id": call.id, "type": call.type,
                         "function": {"name": call.function.name, "arguments": call.function.arguments}}
                        for call in message.tool_calls
                    ]
                })

                function_results = await self._execute_function_calls([
                    {"id": call.id, "function": {"name": call.function.name, "arguments": call.function.arguments}}
                    for call in message.tool_calls
                ])

                for result in function_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["call_id"],
                        "name": result["function_name"],
                        "content": json.dumps(result["result"])
                    })

                final_response = self.client.chat.completions.create(
                    model="gpt-5-nano",
                    messages=messages,
                )

                return {
                    "success": True,
                    "response": final_response.choices[0].message.content,
                    "tools_used": [result["function_name"] for result in function_results],
                    "query": user_query,
                    "timestamp": datetime.now().isoformat()
                }

            # If no tools were called
            return {
                "success": True,
                "response": message.content,
                "tools_used": [],
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


