import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建用户图鉴捕获历史记录表
    """
    logger.debug("正在执行 010_add_pokedex_capture_history_table: 创建图鉴捕获历史表...")

    # 创建用户图鉴捕获历史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_pokedex_capture_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,                    -- 用户ID
            species_id INTEGER NOT NULL,              -- 宝可梦物种ID
            captured_at TEXT DEFAULT (datetime('now', '+8 hours')),  -- 首次捕获时间
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0,              -- 是否删除
            UNIQUE(user_id, species_id)               -- 确保同一用户对同一物种只记录一次
        );
    """)

    # 为用户图鉴捕获历史表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokedex_capture_user_id ON user_pokedex_capture_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokedex_capture_species_id ON user_pokedex_capture_history(species_id)")

    logger.info("✅ 010_add_pokedex_capture_history_table完成")

    logger.debug("正在执行 010_migrate_pokedex_history: 迁移历史数据到图鉴捕获历史表...")

    # 1. 从现有用户的宝可梦记录中迁移历史数据
    # 获取所有用户曾经拥有的宝可梦物种ID（去重）
    cursor.execute("""
                   SELECT DISTINCT user_id, species_id
                   FROM user_pokemon
                   WHERE isdel = 0
                   """)

    records = cursor.fetchall()
    if records:
        # 批量插入到图鉴历史表
        history_data = [(user_id, species_id) for user_id, species_id in records]
        cursor.executemany("""
                           INSERT OR IGNORE INTO user_pokedex_capture_history
                               (user_id, species_id)
                           VALUES (?, ?)
                           """, history_data)

        logger.info(f"✅ 已迁移 {len(records)} 条历史图鉴数据")

    # 2. 从野生宝可梦遭遇记录中迁移历史数据（如果宝可梦被捕捉过）
    cursor.execute("""
                   SELECT DISTINCT log.user_id, w.species_id
                   FROM wild_pokemon_encounter_log log
                            JOIN wild_pokemon w ON log.wild_pokemon_id = w.id
                   WHERE log.is_captured = 1
                     AND log.isdel = 0
                     AND w.isdel = 0
                   """)

    captured_records = cursor.fetchall()
    if captured_records:
        # 批量插入到图鉴历史表
        captured_history_data = [(user_id, species_id) for user_id, species_id in captured_records]
        cursor.executemany("""
                           INSERT OR IGNORE INTO user_pokedex_capture_history
                               (user_id, species_id)
                           VALUES (?, ?)
                           """, captured_history_data)

        logger.info(f"✅ 已从捕捉记录迁移 {len(captured_records)} 条历史图鉴数据")

    logger.info("✅ 010_migrate_pokedex_history完成")


def down(cursor: sqlite3.Cursor):
    """
    回滚此迁移：删除用户图鉴捕获历史记录表
    """
    logger.debug("正在回滚 007_add_pokedex_capture_history_table...")

    cursor.execute("DROP TABLE IF EXISTS user_pokedex_capture_history")

    logger.info("✅ 007_add_pokedex_capture_history_table回滚完成")