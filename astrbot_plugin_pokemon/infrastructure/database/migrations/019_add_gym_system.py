from sqlite3 import Cursor

def up(cursor: Cursor):
    # Add max_unlocked_location_id to users
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'max_unlocked_location_id' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN max_unlocked_location_id INTEGER DEFAULT 1")

    # Create gyms table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gyms (
            id INTEGER PRIMARY KEY,
            location_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            elite_trainer_ids TEXT, -- pipe separated ids
            boss_trainer_id INTEGER,
            required_level INTEGER,
            unlock_location_id INTEGER,
            reward_item_id INTEGER
        )
    """)

def down(cursor: Cursor):
    pass
