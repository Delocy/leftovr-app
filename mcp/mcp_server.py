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
import inflect

p = inflect.engine()

# ============================================================================
# MCP SERVER
# ============================================================================
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
            # return {
            #     "success": True,
            #     "data": result,
            #     "message": f"Successfully executed {self.name}"
            # }
            return result
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
        '''Returns all food items in the database'''
        return self.db.get_all_food_items()

    async def _get_expiring_soon(self, args: Dict[str, Any]):
        '''Returns food items expiring within the next `7 days'''
        days = args.get("days", 7)
        return self.db.get_expiring_soon(days)


    async def _get_food_item(self, args: Dict[str, Any]):
        '''Returns a specific food item by ID'''
        # Normalize ID
        args["id"] = normalize_food_id(args.get("id") or "")
        return self.db.get_food_item_by_id(args["id"])

    async def _add_food_item(self, args):
        '''Adds a new food item to the database'''
        # Ensure ID is normalized
        args["id"] = normalize_food_id(args.get("id") or args.get("name", ""))
        self.db.add_food_item(args["id"], args["name"], args["quantity"], args["expire_date"])
        return {"success": True, "data": args}

    async def _update_food_item(self, args: Dict[str, Any]):
        if "id" not in args or not args["id"]:
            args["id"] = normalize_food_id(args.get("name", ""))

        item = self.db.get_food_item_by_id(args["id"])
        if not item:
            return {"success": False, "error": "Item not found"}

        delta = args.get("quantity", 0)  # can be negative for consumption
        new_quantity = item["quantity"] + delta

        if new_quantity <= 0:
            self.db.delete_food_item(args["id"])
            # Return the full info before deletion if you want
            return {"success": True, "data": item, "message": f"Item {args['id']} removed from pantry"}
        
        self.db.update_food_item(args["id"], quantity=new_quantity)
        # Return full item info
        updated_item = self.db.get_food_item_by_id(args["id"])
        return {"success": True, "data": updated_item}


    async def _delete_food_item(self, args: Dict[str, Any]):
        '''Deletes a food item from the database'''
        # Normalize ID
        args["id"] = normalize_food_id(args.get("id") or "")
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
        if tool_name == "get_all_food_items":
            items = self.db.get_all_food_items()
            return {"data": items, "success": True}
        return await self.tools[tool_name].call(arguments)


db = PantryDatabase()
pantry_server = PantryMCPServer(db)
print(f"MCP Server ready with {len(pantry_server.tools)} tools!")