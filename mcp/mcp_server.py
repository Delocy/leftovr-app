import sys
import os
import sqlite3
import json
import asyncio
import threading
import nest_asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import openai
from enum import Enum
from contextlib import contextmanager
import random
import logging
import time
from database.database import PantryDatabase

# ============================================================================
# MCP SERVER
# ============================================================================

print("Building MCP Server...")

class MCPTool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], handler):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    async def call(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = await self.handler(arguments)
            return {
                "success": True,
                "data": result,
                "message": f"Successfully executed {self.name}"
            }
        except Exception as e:
            logging.error(f"Error executing tool {self.name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to execute {self.name}"
            }

# ==========================================
# Pantry MCP Server
# ==========================================
class PantryMCPServer:
    def __init__(self, database):
        self.db = database
        self.tools = {}
        self._register_tools()

    def _register_tools(self):
        # Get all food items
        self.tools["get_all_food_items"] = MCPTool(
            name="get_all_food_items",
            description="Get all food items in the pantry with quantity and expiration date",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=self._get_all_food_items
        )

        # Get food items expiring soon
        self.tools["get_expiring_soon"] = MCPTool(
            name="get_expiring_soon",
            description="Get food items expiring within a given number of days",
            parameters={
                "type": "object",
                "properties": {"days": {"type": "integer", "description": "Number of days to check"}},
                "required": []
            },
            handler=self._get_expiring_soon
        )

        # Check a specific food item
        self.tools["get_food_item"] = MCPTool(
            name="get_food_item",
            description="Get a specific food item by its ID",
            parameters={
                "type": "object",
                "properties": {"id": {"type": "string", "description": "Food item ID"}},
                "required": ["id"]
            },
            handler=self._get_food_item
        )

        # Add a new food item
        self.tools["add_food_item"] = MCPTool(
            name="add_food_item",
            description="Add a new food item",
            parameters={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "expire_date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["id", "name", "quantity", "expire_date"]
            },
            handler=self._add_food_item
        )

        # Update an existing food item
        self.tools["update_food_item"] = MCPTool(
            name="update_food_item",
            description="Update quantity or expiration date for a food item",
            parameters={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "expire_date": {"type": "string"}
                },
                "required": ["id"]
            },
            handler=self._update_food_item
        )

        # Delete a food item
        self.tools["delete_food_item"] = MCPTool(
            name="delete_food_item",
            description="Delete a food item by ID",
            parameters={
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"]
            },
            handler=self._delete_food_item
        )

    # -------------------------------
    # Tool Handlers
    # -------------------------------
    async def _get_all_food_items(self, args: Dict[str, Any]):
        return self.db.get_all_food_items()

    async def _get_expiring_soon(self, args: Dict[str, Any]):
        days = args.get("days", 7)
        return self.db.get_expiring_soon(days)

    async def _get_food_item(self, args: Dict[str, Any]):
        return self.db.get_food_item_by_id(args["id"])

    async def _add_food_item(self, args: Dict[str, Any]):
        self.db.add_food_item(args["id"], args["name"], args["quantity"], args["expire_date"])
        return {"success": True}

    async def _update_food_item(self, args: Dict[str, Any]):
        self.db.update_food_item(args["id"], args.get("name"), args.get("quantity"), args.get("expire_date"))
        return {"success": True}

    async def _delete_food_item(self, args: Dict[str, Any]):
        self.db.delete_food_item(args["id"])
        return {"success": True}

    # -------------------------------
    # Tool Access
    # -------------------------------
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [{"name": tool.name, "description": tool.description, "parameters": tool.parameters} 
                for tool in self.tools.values()]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]):
        if tool_name not in self.tools:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}
        return await self.tools[tool_name].call(arguments)

db = PantryDatabase()
pantry_server = PantryMCPServer(db)
print(f"MCP Server ready with {len(pantry_server.tools)} tools!")