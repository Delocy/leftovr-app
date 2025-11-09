#!/usr/bin/env python3
# ============================================================================
# PANTRY AGENT (MCP Client)
# ============================================================================
#
# This module provides the PantryAgent that IS an MCP client.
# It manages pantry operations through proper MCP client-server communication.
#
# Architecture:
#   PantryAgent (MCP Client) → [JSON-RPC/stdio] → MCP Server → Database
#
# The agent has NO direct access to the database and must communicate
# through the MCP protocol for all operations.
#
# ============================================================================

import asyncio
import json
import os
import subprocess
import sys
import threading
import queue
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import openai
import inflect
from pydantic import BaseModel

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY")

# Inflect engine for pluralization
p = inflect.engine()


def normalize_food_id(name: str) -> str:
    """
    Normalize a food name for deterministic IDs:
    - singularize
    - lowercase
    - strip spaces
    - replace spaces with hyphens
    """
    if not name:
        return ""
    singular = p.singular_noun(name)  # Returns False if already singular
    singular_name = singular if singular else name
    return singular_name.lower().strip().replace(' ', '-')


class SingleItemResponse(BaseModel):
    """Represents a single food item in the pantry."""
    id: str
    name: str
    quantity: int
    expire_date: str  # Keep as string "YYYY-MM-DD"


class PantryItemsResponse(BaseModel):
    """Represents multiple food items in the pantry."""
    items: List[SingleItemResponse]


def convert_items(raw_items: list) -> PantryItemsResponse:
    """
    Converts a list of raw food items (dicts) into strongly typed PantryItemsResponse.
    """
    typed_items = [SingleItemResponse(**item) for item in raw_items]
    return PantryItemsResponse(items=typed_items)


class PantryAgent:
    """
    PantryAgent - MCP Client for pantry operations.

    This agent IS an MCP client that communicates with the MCP server via JSON-RPC.

    Architecture (Proper MCP):
    ┌──────────────────────────────────────────┐
    │         PantryAgent                      │
    │  (IS THE MCP CLIENT - No DB Access)      │
    │                                          │
    │  Methods:                                │
    │  • add_or_update_ingredient()            │
    │  • get_inventory()                       │
    │  • remove_ingredient()                   │
    │  • handle_query() [AI-powered]           │
    │                                          │
    │  Communicates via JSON-RPC ↓             │
    └──────────────┬───────────────────────────┘
                   ↓ (JSON-RPC via stdio)
    ┌──────────────────────────────────────────┐
    │        MCP Server                         │
    │    (Separate Process - Owns Database)     │
    │                                          │
    │  Tools:                                  │
    │  • add_food_item                         │
    │  • get_all_food_items                    │
    │  • update_food_item                      │
    │  • delete_food_item                      │
    │  • get_expiring_soon                     │
    └──────────────┬───────────────────────────┘
                   ↓
    ┌──────────────────────────────────────────┐
    │        PantryDatabase                     │
    │        (SQLite - single source of truth)  │
    └──────────────────────────────────────────┘

    Note: MCP server runs as a separate process and can be accessed by
    multiple clients (Claude Desktop, this agent, external tools, etc.)
    """

    def __init__(self, name: str = "Pantry Agent", server_script_path: Optional[str] = None):
        """
        Initialize the PantryAgent as an MCP client.

        Args:
            name: Name of the agent
            server_script_path: Path to MCP server script (auto-detected if None)
        """
        self.name = name

        # MCP client state - NO direct database access!
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._response_queue = queue.Queue()
        self._reader_thread = None
        self._connected = False

        # Determine server script path
        if server_script_path is None:
            # Auto-detect: assume we're in agents/, server is in mcp/server.py
            current_dir = Path(__file__).parent.parent
            server_script_path = str(current_dir / "mcp" / "server.py")

        self.server_script_path = server_script_path

        # OpenAI client for natural language interpretation
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

        self.system_prompt = """
        You are an expert Food Pantry AI Assistant with access to real-time inventory data.

        Your role:
        - Help users manage pantry inventory.
        - Interpret natural language statements about food usage, consumption, or restocking.
        - Suggest actionable recommendations.

        Tools you can use:
        - get_all_food_items: View current inventory
        - get_expiring_soon: Get items expiring within N days
        - add_food_item: Add new items or increment quantity
        - set_food_quantity: Set exact quantity for an item
        - adjust_food_quantity: Adjust quantity by delta (positive/negative)
        - delete_food_item: Remove a specific item completely
        - clear_pantry: Delete ALL items from the pantry

        Guidelines:
        - If the user mentions multiple items in one statement, produce one tool call per item.
        - Each call must include name, quantity, and optionally expire_date.
        - For new items without expire_date, a 14-day default will be assigned.
        - If the item is generic (like "Vegetables"), add it as-is.

        Semantic guidance:
        - "I have X" / "I bought X" / "add X" / "got X" → call `add_food_item` with quantity
        - "Update to have X" / "Set to X" / "Change to X" → call `set_food_quantity` with exact quantity
        - "I ate X" / "I used X" / "consumed X" / "cooked with X" → call `adjust_food_quantity` with negative quantity
        - "Remove X" (NO quantity) / "Delete X" / "Get rid of X" / "Throw away X" / "I don't have X anymore" → call `delete_food_item`
        - "Remove N X" (WITH quantity) / "Take out N X" / "Use N X" → call `adjust_food_quantity` with negative quantity
        - "Clear pantry" / "Clear everything" / "Delete all" / "Remove all items" / "Empty pantry" → call `clear_pantry`
        - Viewing inventory → call `get_all_food_items`

        CRITICAL RULES:
        1. "remove X" without a number → delete_food_item (remove completely)
        2. "remove N X" with a number → adjust_food_quantity (subtract N)
        3. "clear pantry" / "clear everything" / "empty pantry" / "delete all items" → call `clear_pantry` (ONE simple call)
        4. NEVER use add_food_item when user says "remove", "delete", "clear", or "get rid of"

        Examples:
        - "I have 2 eggs" → add_food_item(name="egg", quantity=2)
        - "I ate 2 eggs" → adjust_food_quantity(name="egg", quantity=-2)
        - "Update to have 3 tomatoes" → set_food_quantity(name="tomato", quantity=3)
        - "Remove garlic" (no number) → delete_food_item(name="garlic")
        - "Remove 1 garlic" (with number) → adjust_food_quantity(name="garlic", quantity=-1)
        - "Let's remove 2 garlics" → adjust_food_quantity(name="garlic", quantity=-2)
        - "Get rid of the onions" → delete_food_item(name="onion")
        - "Clear the pantry" → clear_pantry()
        - "Delete everything" → clear_pantry()
        - "Empty my pantry" → clear_pantry()

        Always respond with structured tool calls when users want to modify inventory.
        """

    # ============================================
    # MCP CLIENT IMPLEMENTATION
    # Core protocol communication methods
    # ============================================

    def _run_sync(self, coro):
        """
        Helper to run async coroutines synchronously.
        Handles both cases: running event loop and no event loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            return asyncio.run(coro)
        else:
            # Already in a loop - use run_in_executor with a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()

    def _read_responses(self):
        """Background thread to read JSON-RPC responses from server"""
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.decode('utf-8').strip()
                if line:
                    try:
                        response = json.loads(line)
                        self._response_queue.put(response)
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse response: {e}")
        except Exception as e:
            print(f"Error reading responses: {e}")

    async def ensure_connected(self):
        """Connect to MCP server by starting it as subprocess"""
        if self._connected:
            return

        try:
            # Start server as subprocess
            self.process = subprocess.Popen(
                [sys.executable, self.server_script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )

            # Start background thread to read responses
            self._reader_thread = threading.Thread(target=self._read_responses, daemon=True)
            self._reader_thread.start()

            # Give server a moment to start
            await asyncio.sleep(0.1)

            self._connected = True
            print(f"✅ {self.name} connected to MCP server")

        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {str(e)}")
            raise

    async def disconnect(self):
        """Disconnect from MCP server and cleanup"""
        if not self._connected:
            return

        try:
            if self.process:
                # Close stdin to signal server to shut down
                if self.process.stdin:
                    self.process.stdin.close()

                # Wait for process to terminate
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()

                self.process = None

            self._connected = False
            print(f"👋 {self.name} disconnected from MCP server")

        except Exception as e:
            print(f"Error disconnecting: {str(e)}")

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send JSON-RPC request to server and wait for response.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            Result dictionary
        """
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError("Not connected to MCP server. Call ensure_connected() first.")

        try:
            # Generate request
            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params or {}
            }

            # Send request
            request_line = json.dumps(request) + "\n"
            self.process.stdin.write(request_line.encode('utf-8'))
            self.process.stdin.flush()

            # Wait for response (with timeout)
            timeout = 5.0
            start_time = asyncio.get_event_loop().time()

            while True:
                try:
                    response = self._response_queue.get(timeout=0.1)
                    if response.get("id") == self._request_id:
                        if "error" in response:
                            error = response["error"]
                            raise RuntimeError(f"Server error: {error.get('message', 'Unknown error')}")
                        return response.get("result", {})
                    else:
                        # Put it back if it's not our response
                        self._response_queue.put(response)
                except queue.Empty:
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        raise TimeoutError(f"No response received for request {self._request_id}")
                    await asyncio.sleep(0.05)

        except Exception as e:
            print(f"Error sending request: {str(e)}")
            raise

    # ============================================
    # METHODS USING MCP CLIENT
    # All operations go through proper MCP protocol
    # ============================================

    def add_or_update_ingredient(
        self,
        ingredient_name: str,
        quantity: int,
        unit: str = "pieces",
        expire_date: str = None
    ) -> Dict[str, Any]:
        """
        Add or update an ingredient in the pantry via MCP.

        Args:
            ingredient_name: Name of the ingredient
            quantity: Quantity to add (will increment if exists)
            unit: Unit of measurement (stored as metadata, currently unused)
            expire_date: Optional expiration date in YYYY-MM-DD format

        Returns:
            Dict with success status, item_id, action, and quantity
        """
        return self._run_sync(self._add_or_update_ingredient_async(
            ingredient_name, quantity, unit, expire_date
        ))

    async def _add_or_update_ingredient_async(
        self,
        ingredient_name: str,
        quantity: int,
        unit: str = "pieces",
        expire_date: str = None
    ) -> Dict[str, Any]:
        """Async implementation of add_or_update_ingredient"""
        await self.ensure_connected()

        try:
            # Generate deterministic ID
            item_id = normalize_food_id(ingredient_name)

            # Default expiry date if not provided (14 days from now)
            exp_date = expire_date
            if not exp_date:
                exp_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

            # Call through MCP protocol
            args = {
                "name": ingredient_name,
                "quantity": quantity,
                "expire_date": exp_date
            }
            result = await self._send_request("tools/call", {
                "name": "add_food_item",
                "arguments": args
            })

            # Return consistent format
            if result.get("success"):
                return {
                    "success": True,
                    "item_id": item_id,
                    "action": result.get("action", "added"),
                    "quantity": quantity,
                    "data": result.get("data")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error adding ingredient"),
                    "item_id": item_id
                }
        except Exception as e:
            print(f"❌ Error in add_or_update_ingredient: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "item_id": item_id if 'item_id' in locals() else None
            }

    def get_inventory(self) -> List[Dict[str, Any]]:
        """
        Get all pantry items via MCP.

        Returns:
            List of dicts with keys: id, name, quantity, expire_date
        """
        return self._run_sync(self._get_inventory_async())

    async def _get_inventory_async(self) -> List[Dict[str, Any]]:
        """Async implementation of get_inventory"""
        await self.ensure_connected()

        try:
            result = await self._send_request("tools/call", {
                "name": "get_all_food_items",
                "arguments": {}
            })

            if result.get("success"):
                return result.get("data", [])
            else:
                print(f"⚠️  Error getting inventory: {result.get('error')}")
                return []
        except Exception as e:
            print(f"❌ Error in get_inventory: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def get_expiring_soon(self, days_threshold: int = 7) -> List[Dict[str, Any]]:
        """
        Get items expiring within the specified number of days via MCP.

        Args:
            days_threshold: Number of days to check (default: 7)

        Returns:
            List of dicts containing expiring food items
        """
        return self._run_sync(self._get_expiring_soon_async(days_threshold))

    async def _get_expiring_soon_async(self, days_threshold: int = 7) -> List[Dict[str, Any]]:
        """Async implementation of get_expiring_soon"""
        await self.ensure_connected()

        try:
            result = await self._send_request("tools/call", {
                "name": "get_expiring_soon",
                "arguments": {"days": days_threshold}
            })

            if result.get("success"):
                return result.get("data", [])
            else:
                print(f"⚠️  Error getting expiring items: {result.get('error')}")
                return []
        except Exception as e:
            print(f"❌ Error in get_expiring_soon: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def remove_ingredient(self, ingredient_id: str) -> Dict[str, Any]:
        """
        Remove an ingredient from the pantry via MCP.

        Args:
            ingredient_id: ID or name of the ingredient to remove

        Returns:
            Dict with success status and item_id
        """
        return self._run_sync(self._remove_ingredient_async(ingredient_id))

    async def _remove_ingredient_async(self, ingredient_id: str) -> Dict[str, Any]:
        """Async implementation of remove_ingredient"""
        await self.ensure_connected()

        try:
            # Normalize ID (handles both IDs and names)
            item_id = normalize_food_id(ingredient_id)

            # Call through MCP protocol
            result = await self._send_request("tools/call", {
                "name": "delete_food_item",
                "arguments": {"id": item_id}
            })

            return {
                "success": result.get("success", False),
                "item_id": item_id,
                "action": result.get("action", "deleted"),
                "message": result.get("message"),
                "error": result.get("error"),
                "data": result.get("data")  # Include deleted item data
            }
        except Exception as e:
            print(f"❌ Error in remove_ingredient: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "item_id": item_id if 'item_id' in locals() else None
            }

    def clear_pantry(self) -> List[Dict[str, Any]]:
        """
        Clear all items from the pantry via MCP.

        Returns:
            List of items that were deleted
        """
        return self._run_sync(self._clear_pantry_async())

    async def _clear_pantry_async(self) -> List[Dict[str, Any]]:
        """
        Async implementation of clear_pantry.
        Gets all items and deletes them one by one.

        Returns:
            List of deleted items (with their data before deletion)
        """
        await self.ensure_connected()

        try:
            # Get all items in the pantry
            inventory = await self._get_inventory_async()

            if not inventory:
                print("📭 Pantry is already empty")
                return []

            print(f"🔥 Clearing {len(inventory)} items from pantry...")

            # Delete each item
            deleted_items = []
            for item in inventory:
                result = await self._remove_ingredient_async(item['id'])
                if result.get('success'):
                    deleted_items.append(item)
                    print(f"   ✓ Deleted: {item['name']}")
                else:
                    print(f"   ✗ Failed to delete: {item['name']} - {result.get('error')}")

            print(f"✅ Cleared {len(deleted_items)}/{len(inventory)} items")
            return deleted_items

        except Exception as e:
            print(f"❌ Error clearing pantry: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def update_quantity(self, ingredient_id: str, new_quantity: int, mode: str = "absolute") -> Dict[str, Any]:
        """
        Update quantity for an ingredient via MCP.

        Args:
            ingredient_id: ID or name of the ingredient
            new_quantity: Quantity value
            mode: "absolute" (set to exact value) or "delta" (add/subtract)

        Returns:
            Dict with success status and action taken
        """
        return self._run_sync(self._update_quantity_async(ingredient_id, new_quantity, mode))

    async def _update_quantity_async(self, ingredient_id: str, new_quantity: int, mode: str = "absolute") -> Dict[str, Any]:
        """Async implementation of update_quantity"""
        await self.ensure_connected()

        try:
            item_id = normalize_food_id(ingredient_id)

            # If quantity is 0 or negative in absolute mode, delete the item
            if mode == "absolute" and new_quantity <= 0:
                return await self._remove_ingredient_async(item_id)

            # Call through MCP protocol with mode parameter
            args = {
                "id": item_id,
                "quantity": new_quantity,
                "mode": mode
            }
            result = await self._send_request("tools/call", {
                "name": "update_food_item",
                "arguments": args
            })

            # If item doesn't exist and we're in absolute mode, add it instead
            if not result.get("success") and mode == "absolute" and "not found" in result.get("error", "").lower():
                print(f"📝 Item '{item_id}' not found, adding it instead")
                return await self._add_or_update_ingredient_async(
                    ingredient_name=ingredient_id,
                    quantity=new_quantity
                )

            return {
                "success": result.get("success", False),
                "action": result.get("action", "updated"),
                "item_id": item_id,
                "data": result.get("data"),
                "error": result.get("error"),
                "message": result.get("message")
            }
        except Exception as e:
            print(f"❌ Error in update_quantity: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "item_id": item_id if 'item_id' in locals() else None
            }

    # ============================================
    # AI NATURAL LANGUAGE INTERFACE
    # Async method using OpenAI for query interpretation
    # ============================================

    async def handle_query(self, user_query: str) -> Any:
        """
        Process natural language queries using OpenAI.
        All operations go through MCP client.

        Examples:
            - "I ate 2 eggs"
            - "What's in my pantry?"
            - "Add 5 oranges"
            - "I bought 3 tomatoes and 2 onions"
            - "Clear the pantry"

        Args:
            user_query: Natural language query from user

        Returns:
            PantryItemsResponse with typed items, or None if no items affected
        """
        await self.ensure_connected()

        if not self.openai_client:
            print("⚠️  OpenAI client not initialized. Please set OPENAI_API_KEY.")
            return None

        # Define tools for OpenAI function calling
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_all_food_items",
                    "description": "Get all food items in the pantry with quantity and expiration date",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_food_item",
                    "description": "Add a new food item to the pantry (use when user says 'I have X', 'I bought X', 'add X')",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the food item"},
                            "quantity": {"type": "integer", "description": "Quantity to add"}
                        },
                        "required": ["name", "quantity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_food_quantity",
                    "description": "Set the exact quantity of a food item (use when user says 'update to have X', 'set to X', 'change to X')",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the food item"},
                            "quantity": {"type": "integer", "description": "Exact quantity to set"}
                        },
                        "required": ["name", "quantity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "adjust_food_quantity",
                    "description": "Adjust quantity by a delta amount (use when user says 'I ate X', 'I used X', 'consumed X')",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the food item"},
                            "quantity": {"type": "integer", "description": "Quantity delta (negative for consumption, positive for addition)"}
                        },
                        "required": ["name", "quantity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_food_item",
                    "description": "Delete/remove a food item completely from the pantry (use when user says 'remove X', 'delete X', 'I don't have X anymore')",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the food item to delete"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_expiring_soon",
                    "description": "Get food items expiring within a given number of days",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "description": "Number of days to check (default 7)"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_pantry",
                    "description": "Delete ALL items from the pantry at once (use when user says 'clear pantry', 'empty everything', 'delete all items', 'remove everything')",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

        try:
            # Let OpenAI interpret the query and decide which tools to call
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_query}
                ],
                tools=tools,
                tool_choice="auto"
            )

            message = response.choices[0].message
            tool_results = []
            affected_items = []

            # Execute tool calls through MCP client
            for tool_call in getattr(message, "tool_calls", []) or []:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                print(f"🔧 Tool Call: {func_name}({args})")

                # Execute appropriate method based on tool name
                # All methods now go through MCP client (use async versions)
                if func_name == "add_food_item":
                    result = await self._add_or_update_ingredient_async(
                        ingredient_name=args["name"],
                        quantity=args["quantity"]
                    )
                    if result.get("success") and result.get("data"):
                        affected_items.append(result["data"])

                elif func_name == "set_food_quantity":
                    # Set exact quantity (absolute mode)
                    item_id = normalize_food_id(args["name"])
                    result = await self._update_quantity_async(
                        ingredient_id=item_id,
                        new_quantity=args["quantity"],
                        mode="absolute"
                    )
                    if result.get("success") and result.get("data"):
                        affected_items.append(result["data"])

                elif func_name == "adjust_food_quantity":
                    # Adjust quantity by delta (delta mode)
                    item_id = normalize_food_id(args["name"])
                    result = await self._update_quantity_async(
                        ingredient_id=item_id,
                        new_quantity=args["quantity"],
                        mode="delta"
                    )
                    if result.get("success") and result.get("data"):
                        affected_items.append(result["data"])

                elif func_name == "delete_food_item":
                    result = await self._remove_ingredient_async(args["name"])
                    # Track deleted item (data contains the item before deletion)
                    if result.get("success") and result.get("data"):
                        affected_items.append(result["data"])

                elif func_name == "get_all_food_items":
                    items = await self._get_inventory_async()
                    affected_items.extend(items)
                    result = {"success": True, "count": len(items)}

                elif func_name == "get_expiring_soon":
                    days = args.get("days", 7)
                    items = await self._get_expiring_soon_async(days_threshold=days)
                    affected_items.extend(items)
                    result = {"success": True, "count": len(items)}

                elif func_name == "clear_pantry":
                    items = await self._clear_pantry_async()
                    affected_items.extend(items)
                    result = {"success": True, "count": len(items), "message": f"Cleared {len(items)} items"}

                tool_results.append({"tool_name": func_name, "result": result})

            # Convert affected items to typed response
            if affected_items:
                typed_result = convert_items(affected_items)
            else:
                typed_result = PantryItemsResponse(items=[])

            print(f"\n✅ Query processed: {len(tool_results)} tool(s) executed")
            return typed_result

        except Exception as e:
            print(f"❌ Error processing query: {str(e)}")
            return None

    # ============================================
    # UTILITY METHODS
    # ============================================

    def identify_expiring_items(
        self,
        inventory: Optional[PantryItemsResponse] = None
    ) -> List[SingleItemResponse]:
        """
        Identify items expiring within 7 days.
        Can work with typed inventory or fetch fresh data.

        Args:
            inventory: Optional pre-fetched inventory

        Returns:
            List of SingleItemResponse items expiring soon
        """
        if inventory is None:
            raw_items = self.get_expiring_soon(days_threshold=7)
            return [SingleItemResponse(**item) for item in raw_items]

        expiring_items = []
        today = date.today()

        for item in inventory.items:
            expire_date = date.fromisoformat(item.expire_date)
            days_to_expiry = (expire_date - today).days
            if days_to_expiry <= 7:
                expiring_items.append(item)

        return expiring_items

    # ============================================
    # CONTEXT MANAGER SUPPORT
    # ============================================

    async def __aenter__(self):
        """Context manager entry - ensures MCP connection"""
        await self.ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup MCP connection"""
        await self.disconnect()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of the PantryAgent with proper MCP architecture.
    """
    import asyncio

    async def main():
        # Use context manager for automatic connection/cleanup
        async with PantryAgent() as agent:
            print("=== PantryAgent with MCP Client ===\n")

            # Example 1: Add items
            print("1. Adding items...")
            result = agent.add_or_update_ingredient("Apple", 5)
            print(f"   Result: {result}\n")

            # Example 2: Get inventory
            print("2. Getting inventory...")
            inventory = agent.get_inventory()
            print(f"   Items: {len(inventory)}\n")

            # Example 3: Natural language query
            print("3. Processing natural language query...")
            result = await agent.handle_query("I ate 2 apples")
            print(f"   Result: {result}\n")

            # Example 4: Get expiring items
            print("4. Getting expiring items...")
            expiring = agent.get_expiring_soon(7)
            print(f"   Expiring soon: {len(expiring)}\n")

    asyncio.run(main())
