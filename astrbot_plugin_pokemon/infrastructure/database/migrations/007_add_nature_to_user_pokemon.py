import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：为user_pokemon和wild_pokemon表添加性格字段
    """
    logger.debug("正在执行 007_add_nature_to_user_pokemon: 添加性格相关字段...")

    # 添加性格相关字段到user_pokemon表
    cursor.execute("""
    ALTER TABLE user_pokemon ADD COLUMN nature_id INTEGER DEFAULT 1;
    """)
    cursor.execute("""
    ALTER TABLE wild_pokemon ADD COLUMN nature_id INTEGER DEFAULT 1;
    """)
