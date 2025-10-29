import sqlite3
from astrbot.api import logger

def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建项目所需的全部初始表和索引（SQLite版本）
    """
    logger.debug("正在执行 001_initial_setup: 创建所有初始表...")

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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- 玩家创建时间
        );
    """)

    # --- 2. 宝可梦种族定义（图鉴） ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_species (
            id INTEGER PRIMARY KEY,               -- 种族ID
            name_en TEXT NOT NULL,                -- 英文名
            name_cn TEXT,                         -- 中文名
            generation INTEGER,                   -- 世代编号
            base_hp INTEGER,
            base_attack INTEGER,
            base_defense INTEGER,
            base_sp_attack INTEGER,
            base_sp_defense INTEGER,
            base_speed INTEGER,
            height REAL,                          -- 身高（米）
            weight REAL,                          -- 体重（千克）
            description TEXT                      -- 图鉴描述
        );
    """)

    # --- 3. 宝可梦属性类型 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 属性ID
            name TEXT NOT NULL                   -- 属性名称
        );
    """)

    # --- 4. 种族与属性对应关系 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_species_types (
            species_id INTEGER NOT NULL,          -- 种族ID
            type_id INTEGER NOT NULL,             -- 属性ID
            PRIMARY KEY (species_id, type_id),
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (type_id) REFERENCES pokemon_types(id)
        );
    """)

    # --- 5. 玩家拥有的宝可梦 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 宝可梦实例ID
            user_id TEXT NOT NULL,                -- 所属玩家
            species_id INTEGER NOT NULL,          -- 种族ID
            nickname TEXT,                        -- 昵称
            level INTEGER DEFAULT 1,              -- 等级
            exp INTEGER DEFAULT 0,                -- 经验
            gender TEXT CHECK(gender IN ('M','F','N')) DEFAULT 'N', -- 性别
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
            current_hp INTEGER DEFAULT 0,
            is_shiny INTEGER DEFAULT 0,           -- 是否异色（0/1）
            moves TEXT,                           -- 技能列表（JSON字符串）
            caught_time TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id)
        );
    """)

    # --- 6. 宝可梦技能定义 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_moves (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 技能ID
            name TEXT NOT NULL,                   -- 技能名称
            type_id INTEGER,                      -- 技能属性
            category TEXT CHECK(category IN ('Physical','Special','Status')) NOT NULL,
            power INTEGER,
            accuracy INTEGER,
            pp INTEGER,
            description TEXT,
            FOREIGN KEY (type_id) REFERENCES pokemon_types(id)
        );
    """)

    # --- 7. 宝可梦进化关系 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_evolution (
            from_species_id INTEGER NOT NULL,     -- 进化前种族
            to_species_id INTEGER NOT NULL,       -- 进化后种族
            method TEXT CHECK(method IN ('LevelUp','Item','Trade','Happiness','Other')) NOT NULL,
            condition_value TEXT,                 -- 条件值
            PRIMARY KEY (from_species_id, to_species_id),
            FOREIGN KEY (from_species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (to_species_id) REFERENCES pokemon_species(id)
        );
    """)

    # --- 8. 道具系统 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 道具ID
            name TEXT NOT NULL,                   -- 名称
            rarity INTEGER NOT NULL DEFAULT 1,
            price INTEGER NOT NULL DEFAULT 0,
            type TEXT CHECK(type IN ('Healing','Pokeball','Battle','Evolution','Misc')) NOT NULL,
            description TEXT                      -- 道具说明
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_items (
            user_id TEXT NOT NULL,                -- 玩家ID
            item_id INTEGER NOT NULL,             -- 道具ID
            quantity INTEGER DEFAULT 0,           -- 数量
            PRIMARY KEY (user_id, item_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_id) REFERENCES items(id)
        );
    """)

    # --- 9. 玩家队伍配置 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_team (
            user_id TEXT PRIMARY KEY,             -- 玩家ID
            team TEXT,                            -- 队伍配置（JSON字符串）
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)

    # --- 10. 战斗记录 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS battle_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 战斗记录ID
            user1_id TEXT,                        -- 玩家1
            user2_id TEXT,                        -- 玩家2
            winner_id TEXT,                       -- 胜者
            battle_type TEXT CHECK(battle_type IN ('PvE','PvP','Gym','Raid')) DEFAULT 'PvE',
            battle_log TEXT,                      -- 战斗日志（JSON或文本）
            start_time TEXT,                      -- 开始时间
            end_time TEXT,                        -- 结束时间
            FOREIGN KEY (user1_id) REFERENCES users(user_id),
            FOREIGN KEY (user2_id) REFERENCES users(user_id)
        );
    """)

    logger.info("✅ 数据库初始结构创建完成 (SQLite)")