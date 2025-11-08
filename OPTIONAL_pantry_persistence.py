"""
Optional: Simple file-based persistence for Pantry Agent
Add this to pantry_agent.py if you want data to persist between sessions
"""

import json
import os

class PantryAgentWithPersistence(PantryAgent):
    """Pantry Agent with local file persistence"""
    
    def __init__(self, name: str = "Pantry Manager", storage_file: str = "pantry_cache.json"):
        super().__init__(name=name, mcp_client=None)
        self.storage_file = storage_file
        self._load_from_file()
    
    def _load_from_file(self):
        """Load inventory from file if it exists"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    self.inventory_cache = json.load(f)
                print(f"✅ Loaded {len(self.inventory_cache)} items from {self.storage_file}")
            except Exception as e:
                print(f"⚠️  Could not load pantry: {e}")
    
    def _save_to_file(self):
        """Save inventory to file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.inventory_cache, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save pantry: {e}")
    
    def add_or_update_ingredient(self, *args, **kwargs):
        """Override to save after each update"""
        result = super().add_or_update_ingredient(*args, **kwargs)
        self._save_to_file()
        return result

# Usage in main_refactored.py:
# self.pantry = PantryAgentWithPersistence(storage_file="data/pantry_cache.json")
