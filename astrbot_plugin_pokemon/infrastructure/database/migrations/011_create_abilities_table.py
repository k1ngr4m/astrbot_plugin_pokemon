"""
创建宝可梦特性表
"""
from typing import Any
import sqlite3

def up(cursor) -> None:
    """
    创建pokemon_abilities表
    """
    # 创建表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_abilities (
            id INTEGER PRIMARY KEY,
            name_en TEXT NOT NULL,
            name_zh TEXT,
            generation_id INTEGER NOT NULL,
            is_main_series INTEGER NOT NULL DEFAULT 1,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            isdel INTEGER DEFAULT 0
        )
    """)

    # 创建更新updated_at时间戳的触发器
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_pokemon_abilities_updated_at
        AFTER UPDATE ON pokemon_abilities
        FOR EACH ROW
        BEGIN
            UPDATE pokemon_abilities
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
    """)

def down(cursor) -> None:
    """
    回滚迁移 - 删除pokemon_abilities表
    """
    cursor.execute("DROP TABLE IF EXISTS pokemon_abilities")
    cursor.execute("DROP TRIGGER IF EXISTS update_pokemon_abilities_updated_at")