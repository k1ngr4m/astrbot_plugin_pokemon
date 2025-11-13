import sqlite3
from astrbot.api import logger

def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建每日签到记录表
    """
    logger.debug("正在执行 002_add_checkin_records: 创建签到记录表...")

    # 创建签到记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            checkin_date TEXT NOT NULL,  -- 签到日期，格式为YYYY-MM-DD
            gold_reward INTEGER NOT NULL,  -- 金币奖励
            item_reward_id INTEGER DEFAULT 1,  -- 获得的道具ID，默认为普通精灵球
            item_quantity INTEGER DEFAULT 1,  -- 道具数量
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_reward_id) REFERENCES items(id),
            UNIQUE(user_id, checkin_date)  -- 确保每个用户每天只能签到一次
        );
    """)

    # 为签到表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_checkins_user_id ON user_checkins(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_checkins_date ON user_checkins(checkin_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_checkins_user_date ON user_checkins(user_id, checkin_date)")

    logger.info("✅ 签到记录表创建完成")