from sqlite3 import Cursor

def up(cursor: Cursor):
    """添加收藏功能到用户宝可梦表"""
    # 检查列是否存在
    cursor.execute("PRAGMA table_info(user_pokemon)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'is_favorite' not in columns:
        # 添加收藏字段
        cursor.execute("ALTER TABLE user_pokemon ADD COLUMN is_favorite INTEGER DEFAULT 0")