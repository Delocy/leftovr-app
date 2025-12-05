#!/usr/bin/env python3
"""
Validation script to check what's in the pantry.
Offers two modes:
1. MCP mode (via PantryAgent) - recommended
2. Direct DB mode (for debugging) - shows raw database contents
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.pantry_agent import PantryAgent

# Path to the pantry database
DB_PATH = os.path.expanduser("~/.leftovr/pantry.db")


def validate_via_mcp():
    """Check pantry contents via MCP protocol (recommended)"""

    print("=" * 60)
    print("🔍 PANTRY VALIDATION (via MCP Protocol)")
    print("=" * 60)

    # Use PantryAgent (MCP client)
    agent = PantryAgent()

    # Get all items via MCP
    items = agent.get_inventory()

    if items:
        print(f"\n📦 INVENTORY ({len(items)} items):")
        print()
        for item in items:
            id_val = item.get('id', 'N/A')
            name = item.get('name', 'N/A')
            qty = item.get('quantity', 0)
            expire = item.get('expire_date', 'N/A')

            # Calculate days until expiry
            try:
                expire_date = datetime.strptime(expire, "%Y-%m-%d")
                days_left = (expire_date - datetime.now()).days
                if days_left < 0:
                    expiry_status = f"❌ EXPIRED {abs(days_left)} days ago"
                elif days_left <= 3:
                    expiry_status = f"⚠️  Expires in {days_left} days"
                elif days_left <= 7:
                    expiry_status = f"⏰ Expires in {days_left} days"
                else:
                    expiry_status = f"✅ Expires in {days_left} days"
            except:
                expiry_status = f"📅 {expire}"

            print(f"  • {name}")
            print(f"    ID: {id_val}")
            print(f"    Quantity: {qty}")
            print(f"    {expiry_status}")
            print()
    else:
        print("\n📦 INVENTORY: Empty")
        print()
        print("💡 Try adding items by running the Streamlit app and saying:")
        print("   'I have garlic and tomatoes'")

    # Check for expiring items via MCP
    print("-" * 60)
    expiring = agent.get_expiring_soon(days_threshold=3)

    if expiring:
        print(f"\n⚠️  EXPIRING SOON ({len(expiring)} items within 3 days):")
        for item in expiring:
            name = item.get('name', 'N/A')
            expire = item.get('expire_date', 'N/A')
            print(f"  • {name} - {expire}")
    else:
        print("\n✅ No items expiring within 3 days")

    print()
    print("=" * 60)


def validate_direct_db():
    """Check database directly (for debugging only)"""

    print("=" * 60)
    print("🔍 PANTRY DATABASE VALIDATION (Direct DB - Debug Mode)")
    print("=" * 60)
    print("⚠️  Note: This bypasses MCP protocol for debugging purposes")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return

    print(f"✅ Database found at: {DB_PATH}")
    print()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check schema
    print("📋 TABLE SCHEMA:")
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='food_items'")
    schema = cursor.fetchone()
    if schema:
        print(schema[0])
    else:
        print("❌ No 'food_items' table found!")
        return

    print("\n" + "-" * 60)

    # Check all items
    cursor.execute("SELECT * FROM food_items ORDER BY expire_date ASC")
    items = cursor.fetchall()

    if items:
        print(f"\n📦 RAW DATABASE CONTENTS ({len(items)} items):")
        print()
        for item in items:
            item_dict = dict(item)
            id_val = item_dict.get('id', 'N/A')
            name = item_dict.get('name', 'N/A')
            qty = item_dict.get('quantity', 0)
            expire = item_dict.get('expire_date', 'N/A')

            print(f"  • {name}")
            print(f"    ID: {id_val}")
            print(f"    Quantity: {qty}")
            print(f"    Expire Date: {expire}")
            print()
    else:
        print("\n📦 DATABASE: Empty")

    conn.close()
    print("=" * 60)


if __name__ == "__main__":
    import sys

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        print("Running in DIRECT DB mode (debug only)")
        validate_direct_db()
    else:
        print("Running in MCP mode (recommended)")
        print("Use --direct flag for raw database access (debug only)\n")
        validate_via_mcp()

