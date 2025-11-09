#!/usr/bin/env python3
# ============================================================================
# PANTRY MCP SERVER (Proper Implementation with JSON-RPC)
# ============================================================================
#
# This module provides a proper MCP (Model Context Protocol) server for pantry operations.
#
# Purpose:
#   - Exposes pantry database operations as MCP tools via JSON-RPC protocol
#   - Can be used by external MCP clients (Claude Desktop, custom clients, etc.)
#   - Runs as a standalone process communicating via stdio
#
# Architecture:
#   External MCP Client → [stdio/JSON-RPC] → MCP Server → PantryDatabase (SQLite)
#
# Usage:
#   python mcp/server.py
#
# Or as a module:
#   python -m mcp.server
#
# ============================================================================

import json
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.pantry_storage import PantryDatabase
import inflect

# Setup logging to stderr (stdout is used for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pantry-mcp-server")

# Inflect engine for pluralization
p = inflect.engine()

# Initialize database (server owns the database)
db = PantryDatabase()


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


# ============================================================================
# TOOL HANDLERS
# ============================================================================

def handle_list_tools() -> Dict[str, Any]:
    """List all available MCP tools"""
    return {
        "tools": [
            {
                "name": "get_all_food_items",
                "description": "Get all food items in the pantry with quantity and expiration date",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_expiring_soon",
                "description": "Get food items expiring within a given number of days",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to check (default: 7)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_food_item",
                "description": "Get a specific food item by its ID or name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Food item ID or name"
                        }
                    },
                    "required": ["id"]
                }
            },
            {
                "name": "add_food_item",
                "description": "Add a new food item to the pantry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the food item"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Quantity to add"
                        },
                        "expire_date": {
                            "type": "string",
                            "description": "Expiration date in YYYY-MM-DD format (optional, defaults to 14 days from now)"
                        }
                    },
                    "required": ["name", "quantity"]
                }
            },
            {
                "name": "update_food_item",
                "description": "Update quantity or expiration date for a food item. Supports absolute and delta modes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Food item ID or name"
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the food item (optional)"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "New quantity value"
                        },
                        "expire_date": {
                            "type": "string",
                            "description": "New expiration date in YYYY-MM-DD format (optional)"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["absolute", "delta"],
                            "description": "Update mode: 'absolute' sets exact quantity, 'delta' adds/subtracts (default: absolute)"
                        }
                    },
                    "required": ["id"]
                }
            },
            {
                "name": "delete_food_item",
                "description": "Delete a food item from the pantry by ID or name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Food item ID or name to delete"
                        }
                    },
                    "required": ["id"]
                }
            }
        ]
    }


def handle_get_all_food_items(args: dict) -> dict:
    """Get all food items in the database"""
    try:
        items = db.get_all_food_items()
        return {
            "success": True,
            "data": items,
            "count": len(items)
        }
    except Exception as e:
        logger.error(f"Error getting all food items: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


def handle_get_expiring_soon(args: dict) -> dict:
    """Get food items expiring within the specified number of days"""
    try:
        days = args.get("days", 7)
        items = db.get_expiring_soon(days)
        return {
            "success": True,
            "data": items,
            "count": len(items),
            "days_threshold": days
        }
    except Exception as e:
        logger.error(f"Error getting expiring items: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


def handle_get_food_item(args: dict) -> dict:
    """Get a specific food item by ID"""
    try:
        # Normalize ID
        item_id = normalize_food_id(args.get("id") or "")
        if not item_id:
            return {
                "success": False,
                "error": "Item ID is required"
            }

        item = db.get_food_item_by_id(item_id)
        if item:
            return {
                "success": True,
                "data": item
            }
        else:
            return {
                "success": False,
                "error": f"Item '{item_id}' not found",
                "data": None
            }
    except Exception as e:
        logger.error(f"Error getting food item: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def handle_add_food_item(args: dict) -> dict:
    """Add a new food item to the database"""
    try:
        # Validate required fields
        if not args.get("name"):
            return {
                "success": False,
                "error": "Item name is required"
            }

        if not args.get("quantity") or args.get("quantity") <= 0:
            return {
                "success": False,
                "error": "Valid quantity is required"
            }

        # Ensure ID is normalized
        item_id = normalize_food_id(args.get("name", ""))

        # Default expiry date if not provided
        expire_date = args.get("expire_date")
        if not expire_date:
            expire_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

        # Add to database
        db.add_food_item(
            item_id,
            args["name"],
            args["quantity"],
            expire_date
        )

        # Return the added item
        added_item = db.get_food_item_by_id(item_id)
        return {
            "success": True,
            "action": "added",
            "data": added_item
        }
    except Exception as e:
        logger.error(f"Error adding food item: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def handle_update_food_item(args: dict) -> dict:
    """
    Update food item. Supports two modes:
    - absolute mode: Set quantity to exact value (mode='absolute' or default)
    - delta mode: Add/subtract from current quantity (mode='delta')
    """
    try:
        # Normalize ID
        item_id = normalize_food_id(args.get("id") or "")
        if not item_id:
            return {
                "success": False,
                "error": "Item ID is required"
            }

        item = db.get_food_item_by_id(item_id)
        if not item:
            return {
                "success": False,
                "error": f"Item '{item_id}' not found"
            }

        # Determine update mode
        mode = args.get("mode", "absolute")  # default: absolute
        quantity_change = args.get("quantity")

        if quantity_change is None and args.get("name") is None and args.get("expire_date") is None:
            return {
                "success": False,
                "error": "No fields to update"
            }

        # Calculate new quantity
        if quantity_change is not None:
            if mode == "delta":
                new_quantity = item["quantity"] + quantity_change
            else:  # absolute mode
                new_quantity = quantity_change

            # If quantity drops to 0 or below, delete the item
            if new_quantity <= 0:
                db.delete_food_item(item_id)
                return {
                    "success": True,
                    "action": "deleted",
                    "data": item,
                    "message": f"Item '{item_id}' removed (quantity reached 0)"
                }

            # Update quantity
            db.update_food_item(
                item_id,
                name=args.get("name"),
                quantity=new_quantity,
                expire_date=args.get("expire_date")
            )
        else:
            # Only updating name or expire_date
            db.update_food_item(
                item_id,
                name=args.get("name"),
                expire_date=args.get("expire_date")
            )

        # Return updated item
        updated_item = db.get_food_item_by_id(item_id)
        return {
            "success": True,
            "action": "updated",
            "data": updated_item
        }
    except Exception as e:
        logger.error(f"Error updating food item: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def handle_delete_food_item(args: dict) -> dict:
    """Delete a food item from the database"""
    try:
        # Normalize ID
        item_id = normalize_food_id(args.get("id") or "")
        if not item_id:
            return {
                "success": False,
                "error": "Item ID is required"
            }

        # Check if item exists before deleting
        item = db.get_food_item_by_id(item_id)
        if not item:
            return {
                "success": False,
                "error": f"Item '{item_id}' not found"
            }

        # Delete the item
        db.delete_food_item(item_id)
        return {
            "success": True,
            "action": "deleted",
            "data": item,
            "message": f"Item '{item_id}' deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting food item: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# JSON-RPC PROTOCOL HANDLER
# ============================================================================

def handle_rpc_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle JSON-RPC request and route to appropriate tool handler

    Args:
        request: JSON-RPC request object

    Returns:
        JSON-RPC response object
    """
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    try:
        # Handle tool listing
        if method == "tools/list":
            result = handle_list_tools()
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        # Handle tool calls
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            # Route to appropriate handler
            if tool_name == "get_all_food_items":
                result = handle_get_all_food_items(arguments)
            elif tool_name == "get_expiring_soon":
                result = handle_get_expiring_soon(arguments)
            elif tool_name == "get_food_item":
                result = handle_get_food_item(arguments)
            elif tool_name == "add_food_item":
                result = handle_add_food_item(arguments)
            elif tool_name == "update_food_item":
                result = handle_update_food_item(arguments)
            elif tool_name == "delete_food_item":
                result = handle_delete_food_item(arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        # Unknown method
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    except Exception as e:
        logger.error(f"Error handling request: {str(e)}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }


# ============================================================================
# MAIN SERVER LOOP
# ============================================================================

def run_server():
    """
    Main server loop - reads JSON-RPC requests from stdin and writes responses to stdout
    """
    logger.info("🚀 Starting Pantry MCP Server...")
    logger.info(f"📦 Database initialized at: {db.db_path}")
    logger.info("📡 Listening for JSON-RPC messages via stdio...")

    try:
        while True:
            # Read line from stdin
            line = sys.stdin.readline()
            if not line:
                logger.info("👋 EOF received, shutting down...")
                break

            line = line.strip()
            if not line:
                continue

            try:
                # Parse JSON-RPC request
                request = json.loads(line)
                logger.debug(f"Received request: {request}")

                # Handle request
                response = handle_rpc_request(request)

                # Send response to stdout
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                logger.debug(f"Sent response: {response}")

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

    except KeyboardInterrupt:
        logger.info("👋 Keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Server error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    """
    Run this module directly to start the MCP server.

    Usage:
        python mcp/server.py

    Or as a module:
        python -m mcp.server

    The server communicates via JSON-RPC over stdio for MCP protocol compliance.
    """
    run_server()
