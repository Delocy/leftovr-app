"""
Simplified Pantry Agent - Direct Database Access
This is a temporary wrapper that uses direct database access instead of MCP.
"""

from database.pantry_storage import PantryDatabase
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import inflect

p = inflect.engine()


class SimplePantryAgent:
    """
    Simplified pantry agent that uses direct database access.
    Temporarily replaces PantryAgent until MCP is re-enabled.
    """
    
    def __init__(self, name: str = "Pantry Manager"):
        self.name = name
        self.db = PantryDatabase()
        print(f"✅ {name} initialized with direct database access")
    
    def normalize_food_id(self, name: str) -> str:
        """Normalize a food name for deterministic IDs"""
        if not name:
            return ""
        singular = p.singular_noun(name)
        singular_name = singular if singular else name
        return singular_name.lower().strip().replace(' ', '-')
    
    def add_or_update_ingredient(self, name: str, quantity: int, unit: str = "", expire_date: Optional[str] = None) -> Dict[str, Any]:
        """Add or update an ingredient in the pantry"""
        try:
            # Normalize the ID
            food_id = self.normalize_food_id(name)
            
            # Set default expiration if not provided
            if not expire_date:
                # Default to 7 days from now
                expire_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            
            # Add to database
            self.db.add_food_item(
                id=food_id,
                name=name,
                quantity=quantity,
                expire_date=expire_date
            )
            
            return {
                "success": True,
                "message": f"Added/updated {quantity} {unit} {name}",
                "item": {
                    "id": food_id,
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "expire_date": expire_date
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error adding ingredient: {str(e)}"
            }
    
    def get_inventory(self) -> List[Dict[str, Any]]:
        """Get all items in the pantry"""
        try:
            items = self.db.list_all_food_items()
            return [dict(item) for item in items]
        except Exception as e:
            print(f"Error getting inventory: {e}")
            return []
    
    def remove_ingredient(self, name: str, quantity: Optional[int] = None) -> Dict[str, Any]:
        """Remove an ingredient from the pantry"""
        try:
            food_id = self.normalize_food_id(name)
            
            if quantity is None:
                # Remove completely
                self.db.remove_food_item(food_id)
                return {
                    "success": True,
                    "message": f"Removed {name} from pantry"
                }
            else:
                # Decrease quantity
                item = self.db.get_food_item_by_id(food_id)
                if not item:
                    return {
                        "success": False,
                        "message": f"{name} not found in pantry"
                    }
                
                new_quantity = item["quantity"] - quantity
                if new_quantity <= 0:
                    self.db.remove_food_item(food_id)
                    return {
                        "success": True,
                        "message": f"Removed all {name} from pantry"
                    }
                else:
                    self.db.add_food_item(
                        id=food_id,
                        name=name,
                        quantity=new_quantity,
                        expire_date=item["expire_date"]
                    )
                    return {
                        "success": True,
                        "message": f"Decreased {name} quantity to {new_quantity}"
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error removing ingredient: {str(e)}"
            }
    
    def get_expiring_items(self, days: int = 3) -> List[Dict[str, Any]]:
        """Get items expiring within specified days"""
        try:
            items = self.db.list_expiring_items(days=days)
            return [dict(item) for item in items]
        except Exception as e:
            print(f"Error getting expiring items: {e}")
            return []
    
    def clear_pantry(self) -> Dict[str, Any]:
        """Clear all items from the pantry"""
        try:
            self.db.clear_all_food_items()
            return {
                "success": True,
                "message": "Pantry cleared successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error clearing pantry: {str(e)}"
            }
    
    def get_item_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific item by name"""
        try:
            food_id = self.normalize_food_id(name)
            item = self.db.get_food_item_by_id(food_id)
            return dict(item) if item else None
        except Exception as e:
            print(f"Error getting item: {e}")
            return None
