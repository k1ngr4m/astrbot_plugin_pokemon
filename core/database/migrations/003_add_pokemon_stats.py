import sqlite3
from astrbot.api import logger

def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：为user_pokemon表添加实际属性值字段
    """
    logger.debug("正在执行 003_add_pokemon_stats: 添加实际属性值字段...")

    # 添加实际属性值字段到user_pokemon表
    try:
        # HP已经在表中，但我们需要确保它被正确使用
        cursor.execute("ALTER TABLE user_pokemon ADD COLUMN attack INTEGER DEFAULT 0")
        logger.info("✅ 成功添加attack字段到user_pokemon表")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("ℹ️  attack字段已存在，跳过添加")
        else:
            logger.error(f"❌ 添加attack字段时出错: {e}")
            raise

    try:
        cursor.execute("ALTER TABLE user_pokemon ADD COLUMN defense INTEGER DEFAULT 0")
        logger.info("✅ 成功添加defense字段到user_pokemon表")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("ℹ️  defense字段已存在，跳过添加")
        else:
            logger.error(f"❌ 添加defense字段时出错: {e}")
            raise

    try:
        cursor.execute("ALTER TABLE user_pokemon ADD COLUMN sp_attack INTEGER DEFAULT 0")
        logger.info("✅ 成功添加sp_attack字段到user_pokemon表")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("ℹ️  sp_attack字段已存在，跳过添加")
        else:
            logger.error(f"❌ 添加sp_attack字段时出错: {e}")
            raise

    try:
        cursor.execute("ALTER TABLE user_pokemon ADD COLUMN sp_defense INTEGER DEFAULT 0")
        logger.info("✅ 成功添加sp_defense字段到user_pokemon表")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("ℹ️  sp_defense字段已存在，跳过添加")
        else:
            logger.error(f"❌ 添加sp_defense字段时出错: {e}")
            raise

    try:
        cursor.execute("ALTER TABLE user_pokemon ADD COLUMN speed INTEGER DEFAULT 0")
        logger.info("✅ 成功添加speed字段到user_pokemon表")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("ℹ️  speed字段已存在，跳过添加")
        else:
            logger.error(f"❌ 添加speed字段时出错: {e}")
            raise

    # 为新添加的字段创建索引以提高查询性能
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_attack ON user_pokemon(attack)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_defense ON user_pokemon(defense)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_speed ON user_pokemon(speed)")
        logger.info("✅ 成功创建属性值索引")
    except sqlite3.Error as e:
        logger.error(f"❌ 创建属性值索引时出错: {e}")

def down(cursor: sqlite3.Cursor):
    """
    回滚此迁移：注意SQLite不支持直接删除列
    """
    logger.debug("正在回滚 003_add_pokemon_stats: 注意SQLite不支持直接删除列")
    logger.warning("⚠️  SQLite不支持直接删除列，属性值字段将保留但可以忽略")