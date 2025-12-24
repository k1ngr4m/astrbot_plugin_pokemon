from sqlite3 import Cursor

def up(cursor: Cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pokemon_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pokemon_id INTEGER NOT NULL,
        version_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        rarity INTEGER NOT NULL,
        isdel INTEGER DEFAULT 0
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_items_pokemon_id ON pokemon_items (pokemon_id)")

def down(cursor: Cursor):
    cursor.execute("DROP TABLE IF EXISTS pokemon_items")
