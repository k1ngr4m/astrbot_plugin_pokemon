import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：为用户宝可梦表添加友好度字段
    """
    logger.debug("正在执行 007_add_happiness_to_user_pokemon: 为用户宝可梦表添加友好度字段...")

    # 检查是否已经存在 happiness 字段
    cursor.execute("PRAGMA table_info(user_pokemon)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'happiness' not in columns:
        # 为 user_pokemon 表添加 happiness 字段
        cursor.execute("""
            ALTER TABLE user_pokemon
            ADD COLUMN happiness INTEGER DEFAULT 70
        """)
        logger.info("✅ 已为 user_pokemon 表添加 happiness 字段")
    else:
        logger.info("⚠️  user_pokemon 表已存在 happiness 字段，跳过")

    # 检查是否已经存在 current_hp 和 current_pp1-4 字段
    if 'current_hp' not in columns:
        cursor.execute("""
            ALTER TABLE user_pokemon
            ADD COLUMN current_hp INTEGER DEFAULT 0
        """)
        logger.info("✅ 已为 user_pokemon 表添加 current_hp 字段")

    if 'current_pp1' not in columns:
        cursor.execute("""
            ALTER TABLE user_pokemon
            ADD COLUMN current_pp1 INTEGER DEFAULT 0
        """)
        cursor.execute("""
            ALTER TABLE user_pokemon
            ADD COLUMN current_pp2 INTEGER DEFAULT 0
        """)
        cursor.execute("""
            ALTER TABLE user_pokemon
            ADD COLUMN current_pp3 INTEGER DEFAULT 0
        """)
        cursor.execute("""
            ALTER TABLE user_pokemon
            ADD COLUMN current_pp4 INTEGER DEFAULT 0
        """)
        logger.info("✅ 已为 user_pokemon 表添加 current_pp1-4 字段")

    logger.info("✅ 007_add_happiness_to_user_pokemon完成")


def down(cursor: sqlite3.Cursor):
    """
    回滚此迁移
    """
    logger.debug("正在执行 007_add_happiness_to_user_pokemon: 回滚数据库更改...")

    # 删除新增的字段（SQLite不直接支持删除列，这里只是记录操作）
    # 在真实的环境中，我们需要更复杂的操作来删除列
    logger.warning("⚠️  SQLite 不支持直接删除列，如需回滚请手动处理")

    logger.info("✅ 007_add_happiness_to_user_pokemon回滚完成")