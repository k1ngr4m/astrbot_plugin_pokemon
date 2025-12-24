from sqlite3 import Cursor

def up(cursor: Cursor):
    # Add held_item_id to wild_pokemon
    cursor.execute("PRAGMA table_info(wild_pokemon)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'held_item_id' not in columns:
        cursor.execute("ALTER TABLE wild_pokemon ADD COLUMN held_item_id INTEGER DEFAULT 0")

    # Add held_item_id to user_pokemon
    cursor.execute("PRAGMA table_info(user_pokemon)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'held_item_id' not in columns:
        cursor.execute("ALTER TABLE user_pokemon ADD COLUMN held_item_id INTEGER DEFAULT 0")

def down(cursor: Cursor):
    # SQLite doesn't support DROP COLUMN easily in older versions, 
    # but for completeness we'd typically recreate the table. 
    # For this system, we might skip complex down migrations or just leave column.
    pass
