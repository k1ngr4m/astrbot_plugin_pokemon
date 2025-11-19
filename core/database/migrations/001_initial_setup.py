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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, -- 玩家创建时间
            init_selected TINYINT(1) DEFAULT 0, -- 是否已选择初始宝可梦
            last_adventure_time REAL DEFAULT NULL,
            origin_id TEXT DEFAULT NULL          -- 原始玩家ID
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
            attack INTEGER DEFAULT 0,             -- 实际攻击值
            defense INTEGER DEFAULT 0,            -- 实际防御值
            sp_attack INTEGER DEFAULT 0,          -- 实际特攻值
            sp_defense INTEGER DEFAULT 0,         -- 实际特防值
            speed INTEGER DEFAULT 0,              -- 实际速度值
            is_shiny INTEGER DEFAULT 0,           -- 是否异色（0/1）
            moves TEXT,                           -- 技能列表（JSON字符串）
            caught_time TEXT DEFAULT CURRENT_TIMESTAMP,
            shortcode TEXT,                       -- 短码ID（格式为P+4位数字）
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id)
        );
    """)

    # 为user_pokemon表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_shortcode ON user_pokemon(shortcode)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_user_id ON user_pokemon(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_species_id ON user_pokemon(species_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_attack ON user_pokemon(attack)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_defense ON user_pokemon(defense)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_speed ON user_pokemon(speed)")

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
        CREATE TABLE IF NOT EXISTS pokemon_evolutions (
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
            shortcode TEXT,                       -- 短码
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

    # ==========================================================================
    # 新增：11. 宝可梦种族-技能学习关系表（核心新增表）
    # ==========================================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_species_moves (
            species_id INTEGER NOT NULL,          -- 宝可梦种族ID
            move_id INTEGER NOT NULL,             -- 技能ID
            learn_method TEXT CHECK(learn_method IN ('LevelUp','EggMove','TM','HM','Tutor','Initial')) NOT NULL,
            learn_value TEXT NOT NULL,            -- 学习条件（等级/道具编号/无）
            PRIMARY KEY (species_id, move_id, learn_method), -- 复合唯一键
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id) ON DELETE CASCADE,
            FOREIGN KEY (move_id) REFERENCES pokemon_moves(id) ON DELETE CASCADE
        );
    """)

    # 为其他表创建必要索引
    try:
        # users表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_nickname ON users(nickname)")

        # pokemon_species表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_name ON pokemon_species(name_cn, name_en)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_generation ON pokemon_species(generation)")

        # pokemon_moves表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_moves_name ON pokemon_moves(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_moves_type_id ON pokemon_moves(type_id)")

        # user_items表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_items_user_id ON user_items(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_items_item_id ON user_items(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_items_shortcode ON user_items(shortcode)")

        # user_pokemon属性值索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_attack ON user_pokemon(attack)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_defense ON user_pokemon(defense)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_speed ON user_pokemon(speed)")

        # pokemon_species_moves表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_moves_species_id ON pokemon_species_moves(species_id)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_moves_move_id ON pokemon_species_moves(move_id)")

        # battle_records表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_records_user1_id ON battle_records(user1_id)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_records_user2_id ON battle_records(user2_id)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_records_winner_id ON battle_records(winner_id)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battle_records_battle_type ON battle_records(battle_type)")

        # pokemon_species_types表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_types_species_id ON pokemon_species_types(species_id)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_types_type_id ON pokemon_species_types(type_id)")

        # pokemon_evolutions表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_evolutions_from_species_id ON pokemon_evolutions(from_species_id)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_evolutions_to_species_id ON pokemon_evolutions(to_species_id)")

        # items表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON items(type)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_rarity ON items(rarity)")
    except sqlite3.Error as e:
        logger.error(f"❌ 创建其他索引时出错: {e}")

    # --- 11. 冒险区域 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adventure_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 区域ID
            area_code TEXT UNIQUE NOT NULL,       -- 区域短码（A开头的三位数，如A001）
            area_name TEXT NOT NULL,              -- 区域名称
            description TEXT,                     -- 区域描述
            min_level INTEGER DEFAULT 1,          -- 最低推荐等级
            max_level INTEGER DEFAULT 100,        -- 最高推荐等级
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # --- 12. 区域宝可梦关联表 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS area_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER NOT NULL,             -- 区域ID
            pokemon_species_id INTEGER NOT NULL,  -- 宝可梦种族ID
            encounter_rate REAL DEFAULT 10.0,     -- 遇见概率（百分比）
            min_level INTEGER DEFAULT 1,          -- 最低等级
            max_level INTEGER DEFAULT 10,         -- 最高等级
            FOREIGN KEY (area_id) REFERENCES adventure_areas(id) ON DELETE CASCADE,
            FOREIGN KEY (pokemon_species_id) REFERENCES pokemon_species(id) ON DELETE CASCADE,
            UNIQUE(area_id, pokemon_species_id)
        );
    """)

    # 为冒险区域相关表创建索引
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_adventure_areas_code ON adventure_areas(area_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_area_pokemon_area_id ON area_pokemon(area_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_area_pokemon_species_id ON area_pokemon(pokemon_species_id)")
    except sqlite3.Error as e:
        logger.error(f"❌ 创建冒险区域相关索引时出错: {e}")


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

    # --- 1. 商店表 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,     -- 商店ID
            shop_code TEXT UNIQUE NOT NULL,           -- 商店短码（S开头后跟3位数字，如S001）
            name TEXT NOT NULL,                       -- 商店名称
            description TEXT,                         -- 商店描述
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # --- 2. 商店商品表 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,     -- 商品ID
            shop_id INTEGER NOT NULL,                 -- 商店ID
            item_id INTEGER NOT NULL,                 -- 道具ID
            price INTEGER NOT NULL DEFAULT 0,         -- 价格
            stock INTEGER NOT NULL DEFAULT -1,        -- 库存（-1表示无限库存）
            is_active INTEGER NOT NULL DEFAULT 1,     -- 是否上架（0/1）
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
            UNIQUE(shop_id, item_id)                  -- 确保商店内同一道具只出现一次
        );
    """)

    # 为商店表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shops_code ON shops(shop_code)")

    # 为商店商品表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shop_items_shop_id ON shop_items(shop_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shop_items_item_id ON shop_items(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shop_items_active ON shop_items(is_active)")

    logger.info("✅ 商店系统表创建完成")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wild_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            species_id INTEGER NOT NULL,             -- 野生宝可梦物种ID
            name TEXT NOT NULL,                       -- 野生宝可梦名称
            gender TEXT NOT NULL,                     -- 野生宝可梦性别
            level INTEGER NOT NULL,                   -- 野生宝可梦等级
            exp INTEGER NOT NULL DEFAULT 0,           -- 野生宝可梦经验值
            is_shiny INTEGER DEFAULT 0,               -- 是否为异色宝可梦 (0=普通, 1=异色)
            stats TEXT,                               -- 野生宝可梦属性 (JSON格式)
            ivs TEXT,                                 -- 野生宝可梦IV (JSON格式)
            evs TEXT,                                 -- 野生宝可梦EV (JSON格式)
            moves TEXT,                               -- 野生宝可梦招式 (JSON格式)
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id) ON DELETE CASCADE,
            UNIQUE(species_id)
        );
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wild_pokemon_encounter_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,                    -- 遇到宝可梦的用户ID
            pokemon_species_id INTEGER NOT NULL,           -- 遇到的野生宝可梦ID
            pokemon_name TEXT NOT NULL,                           -- 遇到的野生宝可梦名称
            pokemon_level INTEGER NOT NULL,                           -- 野生宝可梦等级
            pokemon_info TEXT,                           -- 野生宝可梦详细信息 (JSON格式)
            area_code TEXT NOT NULL,                        -- 遇到的区域编码
            area_name TEXT NOT NULL,                           -- 遇到的区域名称
            encounter_time TEXT DEFAULT CURRENT_TIMESTAMP, -- 遇到时间
            is_captured INTEGER DEFAULT 0,            -- 是否被捕捉 (0=未捕捉, 1=已捕捉)
            is_battled INTEGER DEFAULT 0,             -- 是否进行了战斗 (0=未战斗, 1=已战斗)
            battle_result TEXT,                       -- 战斗结果 (win/lose/escaped)
            is_shiny INTEGER DEFAULT 0,               -- 是否为异色宝可梦 (0=普通, 1=异色)
            encounter_rate REAL,                      -- 遇到概率
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            isdel INTEGER DEFAULT 0,                 -- 是否删除 (0=未删除, 1=已删除)
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (pokemon_species_id) REFERENCES wild_pokemon(species_id) ON DELETE CASCADE,
            FOREIGN KEY (area_code) REFERENCES adventure_areas(area_code) ON DELETE CASCADE,
            UNIQUE(user_id, pokemon_species_id, area_code, encounter_time)
        );
    """)

    # 为野生宝可梦遇到日志表创建索引
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_encounter_user_id ON wild_pokemon_encounter_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_encounter_time ON wild_pokemon_encounter_log(encounter_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_encounter_is_captured ON wild_pokemon_encounter_log(is_captured)")
    except sqlite3.Error as e:
        logger.error(f"❌ 创建野生宝可梦遇到日志索引时出错: {e}")

    logger.info("✅ 数据库初始结构创建完成 (SQLite)")
