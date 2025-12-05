#!/usr/bin/env python3
"""
Simplified Pantry Agent - Direct Database Access (No MCP)

This version bypasses the MCP server and works directly with SQLite
for easier testing and development.
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import inflect

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.pantry_storage import PantryDatabase

# Load environment variables
load_dotenv()

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


class PantryAgent:
    """
    Simplified Pantry Agent - Direct database access (no MCP server needed)
    
    This agent directly manages the SQLite database for easier testing.
    Perfect for development and when MCP server is not needed.
    """

    def __init__(self, name: str = "Pantry Manager"):
        self.name = name
        self.db = PantryDatabase()
        self._connected = True
        print(f"✅ Pantry Agent initialized (Direct DB mode)")

    async def ensure_connected(self):
        """Compatibility method - already connected to DB"""
        if not self._connected:
            self.db = PantryDatabase()
            self._connected = True
        return True

    async def disconnect(self):
        """Compatibility method for cleanup"""
        self._connected = False

    def get_inventory(self) -> List[Dict[str, Any]]:
        """
        Get all items in the pantry.
        
        Returns:
            List of dicts with keys: id, name, quantity, expire_date
        """
        items = self.db.get_all_food_items()
        # Normalize field names for compatibility
        return [
            {
                "ingredient_name": item.get("name", ""),
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 0),
                "expire_date": item.get("expire_date", "")
            }
            for item in items
        ]

    def get_expiring_soon(self, days_threshold: int = 3) -> List[Dict[str, Any]]:
        """
        Get items expiring within specified days.
        
        Args:
            days_threshold: Number of days to look ahead
            
        Returns:
            List of items expiring soon
        """
        items = self.db.get_expiring_soon(days=days_threshold)
        return [
            {
                "ingredient_name": item.get("name", ""),
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 0),
                "expire_date": item.get("expire_date", "")
            }
            for item in items
        ]

    def add_or_update_ingredient(
        self,
        ingredient_name: str,
        quantity: int,
        unit: str = "units",
        expire_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add or update an ingredient in the pantry.
        
        Args:
            ingredient_name: Name of the ingredient
            quantity: Quantity to add
            unit: Unit of measurement (currently not stored, for future)
            expire_date: Expiration date in YYYY-MM-DD format
            
        Returns:
            Dict with the added/updated item info
        """
        # Normalize the ingredient name to create ID
        ingredient_id = normalize_food_id(ingredient_name)
        
        # Use 30 days from now if no expiration date provided
        if not expire_date:
            expire_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Add to database
        self.db.add_food_item(
            id=ingredient_id,
            name=ingredient_name,
            quantity=quantity,
            expire_date=expire_date
        )
        
        return {
            "id": ingredient_id,
            "name": ingredient_name,
            "quantity": quantity,
            "expire_date": expire_date
        }

    def remove_ingredient(self, ingredient_id: str) -> Dict[str, Any]:
        """
        Remove an ingredient from the pantry.
        
        Args:
            ingredient_id: ID of the ingredient to remove
            
        Returns:
            Result dict with success status
        """
        # Delete from database
        self.db.delete_food_item(ingredient_id)
        
        return {
            "success": True,
            "message": f"Removed {ingredient_id} from pantry"
        }

    def update_quantity(
        self,
        ingredient_id: str,
        new_quantity: int
    ) -> Dict[str, Any]:
        """
        Update the quantity of an ingredient.
        
        Args:
            ingredient_id: ID of the ingredient
            new_quantity: New quantity value
            
        Returns:
            Updated item info
        """
        self.db.update_food_item(ingredient_id, quantity=new_quantity)
        
        item = self.db.get_food_item_by_id(ingredient_id)
        if item:
            return {
                "id": item["id"],
                "name": item["name"],
                "quantity": item["quantity"],
                "expire_date": item["expire_date"]
            }
        return {"success": False, "message": "Item not found"}

    async def handle_query(self, user_message: str) -> Dict[str, Any]:
        """
        Simplified handler for natural language pantry queries.
        
        For testing purposes, this just parses basic add/remove commands.
        
        Args:
            user_message: Natural language query
            
        Returns:
            Response dict with items or error
        """
        message_lower = user_message.lower()
        
        # Simple parsing for testing
        if "add" in message_lower or "have" in message_lower:
            # Extract items (very simple parsing for demo)
            words = user_message.split()
            items_added = []
            
            # Look for numbers followed by words
            i = 0
            while i < len(words):
                word = words[i]
                if word.isdigit():
                    quantity = int(word)
                    if i + 1 < len(words):
                        item_name = words[i + 1].strip(',.')
                        result = self.add_or_update_ingredient(
                            ingredient_name=item_name,
                            quantity=quantity
                        )
                        items_added.append(result)
                        i += 2
                        continue
                i += 1
            
            if items_added:
                return {
                    "items": [
                        {"name": item["name"], "quantity": item["quantity"]}
                        for item in items_added
                    ]
                }
        
        # Get inventory by default
        inventory = self.get_inventory()
        return {"items": inventory}

    def clear_pantry(self):
        """Clear all items from pantry (for testing)"""
        self.db.clear_all_food_items()
        return {"success": True, "message": "Pantry cleared"}


# For testing
if __name__ == '__main__':
    print("Testing Simplified Pantry Agent (Direct DB)")
    
    agent = PantryAgent()
    
    # Test 1: Add items
    print("\n1. Adding items...")
    agent.add_or_update_ingredient("chicken", 2, "lbs", "2025-12-15")
    agent.add_or_update_ingredient("rice", 1, "kg", "2026-01-01")
    agent.add_or_update_ingredient("tomatoes", 5, "units", "2025-12-08")
    
    # Test 2: Get inventory
    print("\n2. Current inventory:")
    inventory = agent.get_inventory()
    for item in inventory:
        print(f"   - {item['name']}: {item['quantity']} (expires: {item['expire_date']})")
    
    # Test 3: Get expiring soon
    print("\n3. Items expiring soon:")
    expiring = agent.get_expiring_soon(days_threshold=5)
    for item in expiring:
        print(f"   ⚠️  {item['name']}: {item['quantity']} (expires: {item['expire_date']})")
    
    # Test 4: Remove item
    print("\n4. Removing chicken...")
    agent.remove_ingredient("chicken")
    
    print("\n5. Final inventory:")
    inventory = agent.get_inventory()
    for item in inventory:
        print(f"   - {item['name']}: {item['quantity']}")
    
    print("\n✅ All tests passed!")
