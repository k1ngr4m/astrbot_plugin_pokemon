import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建 natures 表和 nature_stats 表
    """
    logger.debug("正在执行 006_add_natures_and_nature_stats_tables: 创建性格相关表...")

    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON;")

    # --- 1. 性格表 (natures) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS natures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_en TEXT NOT NULL,                    -- 性格英文名
            name_zh TEXT NOT NULL,                    -- 性格中文名
            decreased_stat_id INTEGER,                -- 降低的属性ID
            increased_stat_id INTEGER,                -- 提升的属性ID
            hates_flavor_id INTEGER,                  -- 讨厌的口味ID
            likes_flavor_id INTEGER,                  -- 喜欢的口味ID
            game_index INTEGER,                       -- 游戏内索引
            isdel TINYINT(10) DEFAULT 0               -- 是否已删除
        );
    """)

    # natures 表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_natures_name ON natures(name_en, name_zh)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_natures_stat_ids ON natures(decreased_stat_id, increased_stat_id)")

    # --- 2. 性格统计数据表 (nature_stats) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nature_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nature_id INTEGER NOT NULL,               -- 性格ID，外键关联 natures.id
            pokeathlon_stat_id INTEGER NOT NULL,      -- 奥运属性ID
            max_change INTEGER NOT NULL,              -- 最大变化值
            isdel TINYINT(10) DEFAULT 0,              -- 是否已删除
            FOREIGN KEY (nature_id) REFERENCES natures(id) ON DELETE CASCADE
        );
    """)

    # nature_stats 表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nature_stats_nature_id ON nature_stats(nature_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nature_stats_pokeathlon_stat_id ON nature_stats(pokeathlon_stat_id)")

    logger.info("✅ 006_add_natures_and_nature_stats_tables 完成")