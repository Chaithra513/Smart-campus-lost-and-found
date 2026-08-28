"""
database.py
------------
Handles all SQLite database work for the project.

Keeping this in its own file means app.py never has to write raw SQL —
it just calls simple functions like insert_item(), get_filtered_items(),
update_item(), delete_item(), and set_resolved().

The database is a single file called lostfound.db. It is created
automatically (along with the "items" table) the first time you run
app.py — you never need to create it by hand.
"""

import sqlite3

DB_NAME = "lostfound.db"


def get_db_connection():
    """Open a connection to the SQLite database file."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create the 'items' table if it doesn't already exist, and make sure
    it has every column Stage 3 needs.

    Stage 3 adds one new column: is_resolved (marks an item as
    Resolved/Claimed). If you're upgrading from Stage 2, your existing
    lostfound.db won't have that column yet — the code below adds it
    automatically, without deleting any of your existing reports.
    """
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            description TEXT,
            location TEXT,
            date TEXT,
            status TEXT NOT NULL,
            contact TEXT,
            image TEXT,
            is_resolved INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()

    # Simple migration: if an older database already exists without the
    # is_resolved column, add it now.
    existing_columns = [row["name"] for row in conn.execute("PRAGMA table_info(items)")]
    if "is_resolved" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN is_resolved INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    conn.close()


def insert_item(item_name, description, location, date, status, contact, image):
    """Save one new lost/found report into the database."""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO items (item_name, description, location, date, status, contact, image)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (item_name, description, location, date, status, contact, image),
    )
    conn.commit()
    conn.close()


def get_filtered_items(keyword="", location="", status_filter=""):
    """
    Return reports for the Browse Items page, newest first, optionally
    narrowed down by:
      - keyword: matched against item_name and description
      - location: matched against location
      - status_filter: "lost", "found", or "" for both

    Passing empty strings for all three (the defaults) returns every item,
    which is exactly what a normal, unfiltered Browse page needs.
    """
    conn = get_db_connection()

    # "WHERE 1=1" is a simple trick that lets us safely add more
    # "AND ..." conditions below only when they're actually needed.
    query = "SELECT * FROM items WHERE 1=1"
    params = []

    if keyword:
        query += " AND (item_name LIKE ? OR description LIKE ?)"
        like_value = f"%{keyword}%"
        params.extend([like_value, like_value])

    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    if status_filter in ("lost", "found"):
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY id DESC"

    items = conn.execute(query, params).fetchall()
    conn.close()
    return items


def get_item_by_id(item_id):
    """Return a single item (used by the Edit page), or None if it doesn't exist."""
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return item


def update_item(item_id, item_name, description, location, date, status, contact, image=None):
    """
    Update an existing report.
    'image' is optional: if the user didn't upload a new one while editing,
    we leave the existing image in the database untouched.
    """
    conn = get_db_connection()
    if image:
        conn.execute(
            """
            UPDATE items
            SET item_name = ?, description = ?, location = ?, date = ?,
                status = ?, contact = ?, image = ?
            WHERE id = ?
            """,
            (item_name, description, location, date, status, contact, image, item_id),
        )
    else:
        conn.execute(
            """
            UPDATE items
            SET item_name = ?, description = ?, location = ?, date = ?,
                status = ?, contact = ?
            WHERE id = ?
            """,
            (item_name, description, location, date, status, contact, item_id),
        )
    conn.commit()
    conn.close()


def delete_item(item_id):
    """Permanently remove a report from the database."""
    conn = get_db_connection()
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def set_resolved(item_id, is_resolved):
    """Mark an item as Resolved/Claimed (True) or not (False)."""
    conn = get_db_connection()
    conn.execute(
        "UPDATE items SET is_resolved = ? WHERE id = ?",
        (1 if is_resolved else 0, item_id),
    )
    conn.commit()
    conn.close()
