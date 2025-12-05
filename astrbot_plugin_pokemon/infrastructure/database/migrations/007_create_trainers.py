"""训练家相关数据库表创建"""
import sqlite3
from astrbot.api import logger

def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建 natures 表和 nature_stats 表
    """
    logger.debug("正在执行 007_create_trainers: 创建训练家相关表...")

    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 创建训练家表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trainers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trainer_class TEXT NOT NULL,  -- 训练家职业 (如: 短裤小子, 捕虫少年, 道馆馆主等)
            base_payout INTEGER DEFAULT 0, -- 基础赏金
            description TEXT,
            isdel INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            updated_at DATETIME DEFAULT (datetime('now', '+8 hours'))
        )
    """)

    # 创建训练家宝可梦表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trainer_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER NOT NULL,
            pokemon_species_id INTEGER NOT NULL,
            level INTEGER DEFAULT 1,
            position INTEGER DEFAULT 0, -- 在队伍中的位置 (0-2)
            isdel INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            updated_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE CASCADE,
            FOREIGN KEY (pokemon_species_id) REFERENCES pokemon_species(id)
        )
    """)

    # 创建玩家与训练家遭遇记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trainer_encounters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            trainer_id INTEGER NOT NULL,
            encounter_time DATETIME DEFAULT (datetime('now', '+8 hours')),
            battle_result TEXT, -- 'win', 'lose', 'not_fought'
            isdel INTEGER DEFAULT 0,
            FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE CASCADE
        )
    """)

    # 创建训练家位置表 (训练家在哪些区域出现)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trainer_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainer_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            encounter_rate REAL DEFAULT 0.1, -- 遭遇概率
            isdel INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            updated_at DATETIME DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE CASCADE,
            FOREIGN KEY (location_id) REFERENCES locations(id)
        )
    """)

    # 创建索引以提高查询性能
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trainers_class ON trainers(trainer_class)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trainers_encounters_user ON trainer_encounters(user_id, trainer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trainer_locations_trainer ON trainer_locations(trainer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trainer_locations_location ON trainer_locations(location_id)")


    logger.info("训练家相关数据库表创建完成！")