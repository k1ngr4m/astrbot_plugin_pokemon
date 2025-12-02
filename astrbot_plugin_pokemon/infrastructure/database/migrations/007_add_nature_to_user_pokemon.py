import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建 natures 表和 nature_stats 表
    """
    logger.debug("正在执行 006_add_natures_and_nature_stats_tables: 创建性格相关表...")

    """执行数据库迁移"""
    # 添加性格相关字段到user_pokemon表
    cursor.execute("""
    ALTER TABLE user_pokemon ADD COLUMN nature_id INTEGER DEFAULT 1;
    """)
    cursor.execute("""
    ALTER TABLE wild_pokemon ADD COLUMN nature_id INTEGER DEFAULT 1;
    """)
