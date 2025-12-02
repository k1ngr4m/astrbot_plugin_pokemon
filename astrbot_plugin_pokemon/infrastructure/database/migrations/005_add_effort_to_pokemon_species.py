import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：为 pokemon_species 表添加 effort 字段
    """
    logger.debug("正在执行添加 effort 字段到 pokemon_species 表的迁移...")

    # 检查列是否已存在
    cursor.execute("PRAGMA table_info(pokemon_species)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'effort' not in columns:
        # 为 pokemon_species 表添加 effort 字段
        cursor.execute("""
            ALTER TABLE pokemon_species
            ADD COLUMN effort TEXT DEFAULT '[]';
        """)
        logger.info("✅ 成功为 pokemon_species 表添加 effort 字段")
        cursor.execute("DELETE FROM pokemon_species")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'pokemon_species';")
    else:
        logger.info("⚠️ pokemon_species 表中 effort 字段已存在，跳过添加")



def down(cursor: sqlite3.Cursor):
    """
    回滚此迁移：移除 pokemon_species 表中的 effort 字段
    注意：SQLite 不支持直接删除列，所以这个操作是示意性的
    """
    logger.warning("⚠️ SQLite 不支持直接删除列，如需回滚请手动处理或重建表")