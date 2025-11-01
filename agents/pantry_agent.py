import asyncio
from typing import Dict, Any
from mcp.mcp_client import PantryMCPClient
from mcp.mcp_server import PantryMCPServer
from database.database import PantryDatabase

class PantryAgent:
    """
    PantryAgent handles user queries related to the food pantry.
    It acts as an intermediary between users and the AI assistant (MCP Client).
    """
    def __init__(self):
        # Initialize an empty pantry database
        self.pantry_db = PantryDatabase()

        # Initialize MCP server with the database
        self.mcp_server = PantryMCPServer(self.pantry_db)

        # Initialize MCP client (AI assistant) with the server
        self.mcp_client = PantryMCPClient(self.mcp_server)

    async def handle_query(self, user_query: str) -> Dict[str, Any]:
        """
        Accept a user query, forward it to the AI assistant, and return the result.
        """
        result = await self.mcp_client.process_query(user_query)
        return result


# ==============================
# Example usage
# ==============================
if __name__ == "__main__":
    agent = PantryAgent()
    print("PantryAgent ready!")

    async def main():
        query = "What are the items expiring in the next 3 days?"
        result = await agent.handle_query(query)
        if result["success"]:
            print("AI Response:")
            print(result["response"])
            print("Tools used:", result["tools_used"])
        else:
            print("Error:", result.get("error"))

    asyncio.run(main())
