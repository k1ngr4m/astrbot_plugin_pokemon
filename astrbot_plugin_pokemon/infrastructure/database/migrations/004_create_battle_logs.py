import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建项目所需的全部初始表和索引（SQLite版本）
    """
    logger.debug("正在执行 004_create_battle_logs: 创建战斗日志表...")

    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS battle_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                target_name TEXT NOT NULL,
                log_data TEXT NOT NULL, -- JSON stored as text
                result TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', '+8 hours'))
            )
        """)
