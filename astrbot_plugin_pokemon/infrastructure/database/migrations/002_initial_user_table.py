import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建项目所需的全部初始表和索引（SQLite版本）
    """
    logger.debug("正在执行 002_initial_user_table: 创建所有用户表...")

    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON;")

    # --- 1. 玩家信息表 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,           -- 玩家唯一ID
            nickname TEXT,                      -- 玩家昵称
            level INTEGER DEFAULT 1,            -- 玩家等级
            exp INTEGER DEFAULT 0,              -- 玩家经验值
            coins INTEGER DEFAULT 200,          -- 玩家金币
            init_selected TINYINT(1) DEFAULT 0, -- 是否已选择初始宝可梦
            last_adventure_time REAL DEFAULT NULL,
            origin_id TEXT DEFAULT NULL,          -- 原始玩家ID
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0      -- 是否已删除
        );
    """)
    # users表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_nickname ON users(nickname)")

    # --- 2. 玩家拥有的宝可梦 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 宝可梦实例ID
            user_id TEXT NOT NULL,                -- 所属玩家
            species_id INTEGER NOT NULL,          -- 种族ID
            nickname TEXT,                        -- 昵称
            level INTEGER DEFAULT 1,              -- 等级
            exp INTEGER DEFAULT 0,                -- 经验
            gender TEXT CHECK(gender IN ('M','F','N')) DEFAULT 'M', -- 性别
            hp INTEGER DEFAULT 0,
            attack INTEGER DEFAULT 0,             -- 实际攻击值
            defense INTEGER DEFAULT 0,            -- 实际防御值
            sp_attack INTEGER DEFAULT 0,          -- 实际特攻值
            sp_defense INTEGER DEFAULT 0,         -- 实际特防值
            speed INTEGER DEFAULT 0,              -- 实际速度值
            hp_iv INTEGER DEFAULT 0,
            attack_iv INTEGER DEFAULT 0,
            defense_iv INTEGER DEFAULT 0,
            sp_attack_iv INTEGER DEFAULT 0,
            sp_defense_iv INTEGER DEFAULT 0,
            speed_iv INTEGER DEFAULT 0,
            hp_ev INTEGER DEFAULT 0,
            attack_ev INTEGER DEFAULT 0,
            defense_ev INTEGER DEFAULT 0,
            sp_attack_ev INTEGER DEFAULT 0,
            sp_defense_ev INTEGER DEFAULT 0,
            speed_ev INTEGER DEFAULT 0,
            move1_id INTEGER,                           -- 技能1ID
            move2_id INTEGER,                           -- 技能2ID
            move3_id INTEGER,                           -- 技能3ID
            move4_id INTEGER,                           -- 技能4ID
            caught_time TEXT DEFAULT (datetime('now', '+8 hours')),
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (move1_id) REFERENCES pokemon_moves(id),
            FOREIGN KEY (move2_id) REFERENCES pokemon_moves(id),
            FOREIGN KEY (move3_id) REFERENCES pokemon_moves(id),
            FOREIGN KEY (move4_id) REFERENCES pokemon_moves(id)
        );
    """)

    # 为user_pokemon表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_nickname ON user_pokemon(nickname)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_user_id ON user_pokemon(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_species_id ON user_pokemon(species_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_attack ON user_pokemon(attack)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_defense ON user_pokemon(defense)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_speed ON user_pokemon(speed)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_gender ON user_pokemon(gender)")


    # --- 3. 玩家物品 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_items (
            user_id TEXT NOT NULL,                -- 玩家ID
            item_id INTEGER NOT NULL,             -- 道具ID
            quantity INTEGER DEFAULT 0,           -- 数量
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            PRIMARY KEY (user_id, item_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_id) REFERENCES items(id)
        );
    """)
    # user_items表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_items_user_id ON user_items(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_items_item_id ON user_items(item_id)")

    # --- 4. 玩家队伍配置 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_team (
            user_id TEXT PRIMARY KEY,             -- 玩家ID
            team TEXT,                            -- 队伍配置（JSON字符串）
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)

    # --- 5. 战斗记录 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_battle_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 战斗记录ID
            user1_id TEXT,                        -- 玩家1
            user2_id TEXT,                        -- 玩家2
            winner_id TEXT,                       -- 胜者
            battle_type TEXT CHECK(battle_type IN ('PvE','PvP','Gym','Raid')) DEFAULT 'PvE',
            battle_log TEXT,                      -- 战斗日志（JSON或文本）
            start_time TEXT,                      -- 开始时间
            end_time TEXT,                        -- 结束时间
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            FOREIGN KEY (user1_id) REFERENCES users(user_id),
            FOREIGN KEY (user2_id) REFERENCES users(user_id)
        );
    """)

    # battle_records表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_battle_records_user1_id ON user_battle_records(user1_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_battle_records_user2_id ON user_battle_records(user2_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_battle_records_winner_id ON user_battle_records(winner_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_battle_records_battle_type ON user_battle_records(battle_type)")

    # --- 6. 签到记录 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            checkin_date TEXT NOT NULL,  -- 签到日期，格式为YYYY-MM-DD
            gold_reward INTEGER NOT NULL,  -- 金币奖励
            item_reward_id INTEGER DEFAULT 1,  -- 获得的道具ID，默认为普通精灵球
            item_quantity INTEGER DEFAULT 1,  -- 道具数量
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_reward_id) REFERENCES items(id),
            UNIQUE(user_id, checkin_date)  -- 确保每个用户每天只能签到一次
        );
    """)

    # 为签到表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_checkins_user_id ON user_checkins(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_checkins_date ON user_checkins(checkin_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_checkins_user_date ON user_checkins(user_id, checkin_date)")

    logger.info("✅ 002_initial_user_table完成")
