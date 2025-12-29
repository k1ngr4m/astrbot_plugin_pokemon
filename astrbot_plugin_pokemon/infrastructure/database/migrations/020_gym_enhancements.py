from sqlite3 import Cursor

def up(cursor: Cursor):
    # User Badges Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            gym_id INTEGER NOT NULL,
            badge_id INTEGER NOT NULL,
            obtained_at INTEGER,
            UNIQUE(user_id, gym_id)
        );
    """)
    
    # User Gym State Table
    # user_id is PK because a user can only be challenging one gym at a time (locked state)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_gym_state (
            user_id TEXT PRIMARY KEY,
            gym_id INTEGER NOT NULL,
            current_stage INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 0,
            last_updated INTEGER
        );
    """)

def down(cursor: Cursor):
    cursor.execute("DROP TABLE IF EXISTS user_badges;")
    cursor.execute("DROP TABLE IF EXISTS user_gym_state;")
