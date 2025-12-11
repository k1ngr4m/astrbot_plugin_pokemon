import sqlite3
from astrbot.api import logger

def up(cursor: sqlite3.Cursor):
    # 1. move_flag_map
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS move_flag_map (
        move_id INTEGER NOT NULL,
        move_flag_id INTEGER NOT NULL,
        PRIMARY KEY (move_id, move_flag_id),
        FOREIGN KEY (move_id) REFERENCES moves(id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_move_flag_map_move_id ON move_flag_map(move_id)")

    # 2. move_meta
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS move_meta (
        move_id INTEGER PRIMARY KEY,
        meta_category_id INTEGER NOT NULL,
        meta_ailment_id INTEGER NOT NULL,
        min_hits INTEGER,
        max_hits INTEGER,
        min_turns INTEGER,
        max_turns INTEGER,
        drain INTEGER NOT NULL DEFAULT 0,
        healing INTEGER NOT NULL DEFAULT 0,
        crit_rate INTEGER NOT NULL DEFAULT 0,
        ailment_chance INTEGER NOT NULL DEFAULT 0,
        flinch_chance INTEGER NOT NULL DEFAULT 0,
        stat_chance INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (move_id) REFERENCES moves(id)
    )
    """)

    # 3. move_meta_stat_changes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS move_meta_stat_changes (
        move_id INTEGER NOT NULL,
        stat_id INTEGER NOT NULL,
        change INTEGER NOT NULL,
        PRIMARY KEY (move_id, stat_id),
        FOREIGN KEY (move_id) REFERENCES moves(id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_move_meta_stat_changes_move_id ON move_meta_stat_changes(move_id)")

    logger.info("Created move_flag_map, move_meta, and move_meta_stat_changes tables.")
