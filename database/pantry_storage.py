import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
import os
# ============================================================================
# DATABASE LAYER
# ============================================================================

class PantryDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.expanduser("~/.leftovr")
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "pantry.db")

        self.db_path = db_path
        self._initialize()

        print(f"Connected to pantry database at: {self.db_path}")


    def _initialize(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS food_items (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    quantity INTEGER,
                    expire_date TEXT
                )
            """)
            conn.commit()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # <-- Add this line
        return conn


    # ------------------------------
    # CREATE
    # ------------------------------
    def add_food_item(self, id: str, name: str, quantity: int, expire_date: str):
        existing = self.get_food_item_by_id(id)
        if existing:
            # Increment quantity instead of overwrite
            quantity += existing["quantity"]
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO food_items (id, name, quantity, expire_date)
                VALUES (?, ?, ?, ?)
            ''', (id, name, quantity, expire_date))
            conn.commit()
    # ------------------------------
    # READ
    # ------------------------------
    def get_all_food_items(self):
        """Retrieve all food items."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM food_items ORDER BY expire_date ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_food_item_by_id(self, id: str):
        """Retrieve a single food item by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM food_items WHERE id = ?", (id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_expiring_soon(self, days: int = 7):
        """Retrieve food items expiring within the next `days` days."""
        threshold_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM food_items WHERE expire_date <= ? ORDER BY expire_date ASC",
                (threshold_date,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ------------------------------
    # UPDATE
    # ------------------------------
    def update_food_item(self, id: str, name: str = None, quantity: int = None, expire_date: str = None):
        """Update food item attributes."""
        with self.get_connection() as conn:
            # Build dynamic query based on provided values
            updates = []
            params = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if quantity is not None:
                updates.append("quantity = ?")
                params.append(quantity)
            if expire_date is not None:
                updates.append("expire_date = ?")
                params.append(expire_date)
            params.append(id)

            if updates:
                query = f"UPDATE food_items SET {', '.join(updates)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()

    # ------------------------------
    # DELETE
    # ------------------------------
    def delete_food_item(self, id: str):
        """Delete a food item by ID."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM food_items WHERE id = ?", (id,))
            conn.commit()


