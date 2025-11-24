import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建项目所需的全部初始表和索引（SQLite版本）
    """
    logger.debug("正在执行 001_initial_pokemon_table: 创建宝可梦初始表...")

    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON;")

    # --- 1. 宝可梦种族定义（图鉴） ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_species (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 种族ID
            name_en TEXT NOT NULL,                -- 英文名
            name_zh TEXT,                         -- 中文名
            generation_id INTEGER,                   -- 世代编号
            base_hp INTEGER,
            base_attack INTEGER,
            base_defense INTEGER,
            base_sp_attack INTEGER,
            base_sp_defense INTEGER,
            base_speed INTEGER,
            height REAL,                          -- 身高（米）
            weight REAL,                          -- 体重（千克）
            base_experience INTEGER,
            gender_rate INTEGER,
            capture_rate INTEGER,
            growth_rate_id INTEGER,
            description TEXT,                      -- 图鉴描述
            orders INTEGER,
            isdel TINYINT(10) DEFAULT 0            -- 是否已删除
        );
    """)

    # pokemon_species表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_name ON pokemon_species(name_zh, name_en)")

    # --- 2. 宝可梦属性类型 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 属性ID
            name_en TEXT NOT NULL,                   -- 属性名称（英文）
            name_zh TEXT                         -- 属性名称（中文）,
            isdel TINYINT(10) DEFAULT 0            -- 是否已删除
        );
    """)

    # --- 3. 宝可梦技能定义（不完全，有点复杂，先放着） ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_moves (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 技能ID
            name TEXT NOT NULL,                   -- 技能名称
            type_id INTEGER,                      -- 技能属性
            category TEXT CHECK(category IN ('Physical','Special','Status')) NOT NULL,
            power INTEGER,
            accuracy INTEGER,
            pp INTEGER,
            description TEXT,                     -- 技能描述
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            FOREIGN KEY (type_id) REFERENCES pokemon_types(id)
        );
    """)

    # pokemon_moves表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_moves_name ON pokemon_moves(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_moves_type_id ON pokemon_moves(type_id)")

    # --- 4. 道具系统 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 道具ID
            name_en TEXT NOT NULL,                   -- 道具英文名称
            name_zh TEXT,                           -- 道具中文名称
            category_id INTEGER NOT NULL DEFAULT 1,
            cost INTEGER NOT NULL DEFAULT 0,
            description TEXT,                      -- 道具说明
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0         -- 是否已删除
        );
    """)

    # items表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name_en, name_zh)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category_id ON items(category_id)")

    # --- 5. 宝可梦种族与属性对应关系 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_species_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 关联ID
            species_id INTEGER NOT NULL,          -- 种族ID
            type_id INTEGER NOT NULL,             -- 属性ID            
            isdel TINYINT(10) DEFAULT 0,            -- 是否已删除
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (type_id) REFERENCES pokemon_types(id)
        );
    """)

    # pokemon_species_types表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_types_species_id ON pokemon_species_types(species_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_types_type_id ON pokemon_species_types(type_id)")

    # --- 6. 宝可梦种族进化关系 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_evolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 进化记录ID
            pre_species_id INTEGER,                           -- 进化前宝可梦ID，外键关联pokemon_species.id
            evolved_species_id INTEGER NOT NULL,              -- 进化后宝可梦ID，外键关联pokemon_species.id
            evolution_trigger_id INTEGER,                     -- 进化触发类型ID
            trigger_item_id INTEGER,                          -- 触发物品ID，外键关联items.id
            minimum_level INTEGER DEFAULT 0,                  -- 最低等级要求
            gender_id INTEGER,                                -- 性别要求ID
            held_item_id INTEGER,                             -- 携带物品要求ID，外键关联items.id
            time_of_day TEXT,                                 -- 时间要求（白天、夜晚等）
            known_move_id INTEGER,                            -- 已学会技能要求ID，外键关联moves.id
            minimum_happiness INTEGER DEFAULT 0,              -- 最低友好度要求
            minimum_beauty INTEGER DEFAULT 0,                 -- 最低美丽度要求
            minimum_affection INTEGER DEFAULT 0,              -- 最低亲密度要求
            relative_physical_stats INTEGER,                  -- 攻防对比要求（-1:攻击<防御, 0:攻击=防御, 1:攻击>防御）
            party_species_id INTEGER,                         -- 队伍中宝可梦要求ID，外键关联pokemon_species.id
            trade_species_id INTEGER,                         -- 交换对象宝可梦ID，外键关联pokemon_species.id
            needs_overworld_rain INTEGER DEFAULT 0,           -- 是否需要野外雨天（0=否，1=是）
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            FOREIGN KEY (evolved_species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (pre_species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (trigger_item_id) REFERENCES items(id),
            FOREIGN KEY (held_item_id) REFERENCES items(id),
            FOREIGN KEY (known_move_id) REFERENCES pokemon_moves(id),
            FOREIGN KEY (party_species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (trade_species_id) REFERENCES pokemon_species(id)
        );
    """)

    cursor.execute("""CREATE INDEX idx_pokemon_evolution_pre_species_id ON pokemon_evolutions(pre_species_id);""")
    cursor.execute("""CREATE INDEX idx_pokemon_evolution_evolved_species_id ON pokemon_evolutions(evolved_species_id);""")
    cursor.execute("""CREATE INDEX idx_pokemon_evolution_evolution_trigger_id ON pokemon_evolutions(evolution_trigger_id);""")

    # 7. 宝可梦种族-技能学习关系表（待重构）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_species_moves (
            species_id INTEGER NOT NULL,          -- 宝可梦种族ID
            move_id INTEGER NOT NULL,             -- 技能ID
            learn_method TEXT CHECK(learn_method IN ('LevelUp','EggMove','TM','HM','Tutor','Initial')) NOT NULL,
            learn_value TEXT NOT NULL,            -- 学习条件（等级/道具编号/无）
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            PRIMARY KEY (species_id, move_id, learn_method), -- 复合唯一键
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id) ON DELETE CASCADE,
            FOREIGN KEY (move_id) REFERENCES pokemon_moves(id) ON DELETE CASCADE
        );
    """)

    # pokemon_species_moves表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_moves_species_id ON pokemon_species_moves(species_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_species_moves_move_id ON pokemon_species_moves(move_id)")

    # --- 8. 冒险地点 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 区域ID
            name TEXT NOT NULL,                   -- 区域名称
            description TEXT,                     -- 区域描述
            min_level INTEGER DEFAULT 1,          -- 最低推荐等级
            max_level INTEGER DEFAULT 100,        -- 最高推荐等级           
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0          -- 是否已删除
        );
    """)

    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name);""")

    # --- 9. 地点宝可梦关联表 ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,             -- 地点ID
            pokemon_species_id INTEGER NOT NULL,  -- 宝可梦种族ID
            encounter_rate REAL DEFAULT 10.0,     -- 遇见概率（百分比）
            min_level INTEGER DEFAULT 1,          -- 最低等级
            max_level INTEGER DEFAULT 10,         -- 最高等级
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
            FOREIGN KEY (pokemon_species_id) REFERENCES pokemon_species(id) ON DELETE CASCADE        );
    """)

    # 为地点宝可梦关联表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_location_location_id ON location_pokemon(location_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_location_species_id ON location_pokemon(pokemon_species_id)")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wild_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            species_id INTEGER NOT NULL,             -- 野生宝可梦物种ID
            name TEXT NOT NULL,                       -- 野生宝可梦名称
            gender TEXT NOT NULL,                     -- 野生宝可梦性别
            level INTEGER NOT NULL,                   -- 野生宝可梦等级
            exp INTEGER NOT NULL DEFAULT 0,           -- 野生宝可梦经验值
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
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id) ON DELETE CASCADE
        );
    """)
    # 为野生宝可梦表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_species_id ON wild_pokemon(species_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_gender ON wild_pokemon(gender)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_level ON wild_pokemon(level)")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wild_pokemon_encounter_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,                    -- 遇到宝可梦的用户ID
            wild_pokemon_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,                        -- 遇到的区域ID
            encounter_time TEXT DEFAULT (datetime('now', '+8 hours')), -- 遇到时间
            is_captured INTEGER DEFAULT 0,            -- 是否被捕捉 (0=未捕捉, 1=已捕捉)
            is_battled INTEGER DEFAULT 0,             -- 是否进行了战斗 (0=未战斗, 1=已战斗)
            battle_result TEXT,                       -- 战斗结果 (win/lose/escaped)
            encounter_rate REAL,                      -- 遇到概率
            created_at TEXT DEFAULT (datetime('now', '+8 hours')),
            updated_at TEXT DEFAULT (datetime('now', '+8 hours')),
            isdel TINYINT(10) DEFAULT 0,                 -- 是否删除 (0=未删除, 1=已删除)
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (wild_pokemon_id) REFERENCES wild_pokemon(id) ON DELETE CASCADE,
            FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
            UNIQUE(user_id, wild_pokemon_id, location_id, encounter_time)
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_encounter_user_id ON wild_pokemon_encounter_log(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_encounter_time ON wild_pokemon_encounter_log(encounter_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wild_pokemon_encounter_is_captured ON wild_pokemon_encounter_log(is_captured)")


    logger.info("✅ 001_initial_pokemon_table完成")
