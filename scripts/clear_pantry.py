#!/usr/bin/env python3
"""
Clear all items from the pantry database via MCP protocol.
All operations go through PantryAgent (MCP client) -> MCP Server -> Database.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.pantry_agent import PantryAgent

def clear_pantry():
    """Remove all items from the pantry via MCP protocol"""

    print("🗑️  CLEARING PANTRY DATABASE (via MCP)")
    print("=" * 60)

    # Use PantryAgent (MCP client) instead of direct database access
    agent = PantryAgent()

    # Get all current items via MCP
    items = agent.get_inventory()

    if not items:
        print("📦 Pantry is already empty!")
        return

    print(f"\n📦 Found {len(items)} items to remove:")
    for item in items:
        print(f"  • {item['quantity']}x {item['name']}")

    print("\n🗑️  Removing all items via MCP...")

    # Delete all items via MCP
    for item in items:
        result = agent.remove_ingredient(item['id'])
        if result.get('success'):
            print(f"  ✅ Removed: {item['name']}")
        else:
            print(f"  ❌ Failed to remove: {item['name']} - {result.get('error')}")

    # Verify it's empty via MCP
    remaining = agent.get_inventory()

    print("\n" + "=" * 60)
    if len(remaining) == 0:
        print("✅ Pantry cleared successfully!")
        print("📦 Current inventory: 0 items")
    else:
        print(f"⚠️  Warning: {len(remaining)} items still remain")

    print("=" * 60)

if __name__ == "__main__":
    clear_pantry()

