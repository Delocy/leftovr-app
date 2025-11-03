import asyncio
from typing import Dict, Any, List
from mcp.mcp_client import PantryMCPClient
from mcp.mcp_server import PantryMCPServer
from database.database import PantryDatabase
from pydantic import BaseModel
from datetime import date


class SingleItemResponse(BaseModel):
    """Represents a single food item in the pantry."""
    id: str
    name: str
    quantity: int
    expire_date: str  # Keep as string "YYYY-MM-DD" or use date type
    
class PantryItemsResponse(BaseModel):
    """Represents multiple food items in the pantry."""
    items: List[SingleItemResponse]


def convert_items(raw_items: list) -> PantryItemsResponse:
    """
    Converts a list of raw food items (dicts from MCP server) into
    strongly typed PantryItemsResponse.
    """
    typed_items = [SingleItemResponse(**item) for item in raw_items]
    return PantryItemsResponse(items=typed_items)

class PantryAgent:
    """
    PantryAgent handles user queries related to the food pantry.
    It acts as an intermediary between users and the AI assistant (MCP Client).
    """
    def __init__(self, name: str = "Pantry Agent"):
        # Initialize an empty pantry database
        self.name = name
        self.pantry_db = PantryDatabase()

        # Initialize MCP server with the database
        self.mcp_server = PantryMCPServer(self.pantry_db)

        # Initialize MCP client (AI assistant) with the server
        self.mcp_client = PantryMCPClient(self.mcp_server)

    async def handle_query(self, user_query: str) -> Any:
            """
            Accept a user query, forward it to the AI assistant, and return the typed result.
            """
            raw_result = await self.mcp_client.process_query(user_query)
            print("\n🗄️  Raw MCP Client Result:", raw_result)

            typed_result = None

            # Process 'get_all_food_items'
            if 'get_all_food_items' in raw_result.get('tools_used', []):
                tool_output = next(
                    (t["data"] for t in raw_result.get("tool_outputs", []) if t["tool_name"] == "get_all_food_items"),
                    {}
                )
                items_list = tool_output.get("data", [])
                typed_result = convert_items(items_list)

            # Process 'add_food_item' or 'update_food_item'
            elif any(tool in raw_result.get('tools_used', []) for tool in ["add_food_item", "update_food_item"]):
                tool_output = next(
                    (t["data"] for t in raw_result.get("tool_outputs", []) if t["tool_name"] in ["add_food_item", "update_food_item"]),
                    {}
                )
                item_data = tool_output.get("data", {})
                if item_data:
                    typed_result = convert_items([item_data])  # Wrap in list and convert
                else:
                    typed_result = PantryItemsResponse(items=[])

            # Optional: handle other tools if needed
            else:
                print("⚠️  No recognized tools used in this query.")

            return typed_result
    
    def identify_expiring_items(self, inventory):
        """Identify items that are expiring within 7 days."""
        expiring_items = []
        today = date.today()
        for item in inventory.items if inventory else []:
            expire_date = date.fromisoformat(item.expire_date)
            days_to_expiry = (expire_date - today).days
            if days_to_expiry <= 7:
                expiring_items.append(item)
        return expiring_items

# ==============================
# Example usage
# ==============================
# if __name__ == "__main__":
#     agent = PantryAgent()
#     print("PantryAgent ready!")

#     async def main():
#         query = "I bought 5 eggs"
#         result = await agent.handle_query(query)
#         if result["success"]:
#             print("AI Response:")
#             print(result['response'])
#             print("Tools used:", result["tools_used"])
#         else:
#             print("Error:", result.get("error"))

#     asyncio.run(main())
