import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建项目所需的全部初始表和索引（SQLite版本）
    """
    logger.debug("正在执行 100_excute_gen_1: 启用第一世代...")

    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
        UPDATE pokemon_species
        SET isdel = 1
        WHERE generation_id != 1
    """)

    logger.debug("已执行 100_excute_gen_1: 启用第一世代...")
