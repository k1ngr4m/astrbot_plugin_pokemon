"""
创建宝可梦特性关联表
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
            pokemon_id INTEGER NOT NULL,
            ability_id INTEGER NOT NULL,
            is_hidden INTEGER NOT NULL DEFAULT 0,  -- 是否为隐藏特性
            slot INTEGER NOT NULL,  -- 特性槽位 (1, 2, 3 - 3表示隐藏特性)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            isdel INTEGER DEFAULT 0,
            FOREIGN KEY (pokemon_id) REFERENCES pokemon_species (id),
            FOREIGN KEY (ability_id) REFERENCES abilities (id),
            UNIQUE(pokemon_id, slot)  -- 限制每个宝可梦的槽位唯一
        )
    """)

    # 创建索引以提高查询性能
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_abilities_pokemon_id ON pokemon_abilities(pokemon_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_abilities_ability_id ON pokemon_abilities(ability_id)")

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