import sqlite3

from astrbot.api import logger

def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建项目所需的全部初始表和索引。
    """
    logger.debug("正在执行 001_initial_setup: 创建所有初始表...")

    # --- 1. 玩家信息表 ---
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT COMMENT '玩家唯一ID' PRIMARY KEY , 
                nickname TEXT COMMENT '玩家昵称', 
                level INTEGER COMMENT '玩家等级'  DEFAULT 1, 
                exp BIGINT COMMENT '玩家经验值' DEFAULT 0, 
                coins INTEGER COMMENT '玩家金币' DEFAULT 200, 
                created_at DATETIME COMMENT '玩家创建时间' DEFAULT CURRENT_TIMESTAMP 
            )
        """)

    # --- 2. 宝可梦种族定义（图鉴） ---
    cursor.execute("""
        CREATE TABLE pokemon_species (
            id INT PRIMARY KEY AUTO_INCREMENT COMMENT '种族ID，对应图鉴编号',
            name_en VARCHAR(50) NOT NULL COMMENT '宝可梦英文名',
            name_cn VARCHAR(50) COMMENT '宝可梦中文名',
            generation INT COMMENT '世代编号',
            base_hp INT COMMENT '基础HP',
            base_attack INT COMMENT '基础攻击',
            base_defense INT COMMENT '基础防御',
            base_sp_attack INT COMMENT '基础特攻',
            base_sp_defense INT COMMENT '基础特防',
            base_speed INT COMMENT '基础速度',
            height DECIMAL(4,2) COMMENT '身高（米）',
            weight DECIMAL(5,2) COMMENT '体重（千克）',
            description TEXT COMMENT '图鉴描述'
        )
    """)

    # --- 3. 宝可梦属性类型 ---
    cursor.execute("""
        CREATE TABLE pokemon_types (
            id INT PRIMARY KEY AUTO_INCREMENT COMMENT '属性ID',
            name VARCHAR(30) NOT NULL COMMENT '属性名称'
        )
    """)

    # --- 4. 种族与属性对应关系 ---
    cursor.execute("""
        CREATE TABLE pokemon_species_types (
            species_id INT COMMENT '宝可梦种族ID',
            type_id INT COMMENT '属性ID',
            PRIMARY KEY (species_id, type_id),
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (type_id) REFERENCES pokemon_types(id)
        )
    """)

    # --- 5. 玩家拥有的宝可梦 ---
    cursor.execute("""
        CREATE TABLE user_pokemon (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '玩家宝可梦实例ID',
            user_id BIGINT NOT NULL COMMENT '所属玩家ID',
            species_id INT NOT NULL COMMENT '种族ID',
            nickname VARCHAR(50) COMMENT '昵称，可自定义',
            level INT DEFAULT 1 COMMENT '当前等级',
            exp BIGINT DEFAULT 0 COMMENT '当前经验值',
            gender ENUM('M','F','N') DEFAULT 'N' COMMENT '性别：雄M/雌F/无N',  -- ENUM默认值用字符串
            hp_iv INT DEFAULT 0 COMMENT 'HP个体值',
            attack_iv INT DEFAULT 0 COMMENT '攻击个体值',
            defense_iv INT DEFAULT 0 COMMENT '防御个体值',
            sp_attack_iv INT DEFAULT 0 COMMENT '特攻个体值',
            sp_defense_iv INT DEFAULT 0 COMMENT '特防个体值',
            speed_iv INT DEFAULT 0 COMMENT '速度个体值',
            hp_ev INT DEFAULT 0 COMMENT 'HP努力值',
            attack_ev INT DEFAULT 0 COMMENT '攻击努力值',
            defense_ev INT DEFAULT 0 COMMENT '防御努力值',
            sp_attack_ev INT DEFAULT 0 COMMENT '特攻努力值',
            sp_defense_ev INT DEFAULT 0 COMMENT '特防努力值',
            speed_ev INT DEFAULT 0 COMMENT '速度努力值',
            current_hp INT DEFAULT 0 COMMENT '当前血量',
            is_shiny TINYINT(1) DEFAULT 0 COMMENT '是否异色（闪光）宝可梦',  -- 用TINYINT替代BOOLEAN
            moves JSON COMMENT '技能列表（最多4个，存储技能名数组）',
            caught_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '捕获时间',
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (species_id) REFERENCES pokemon_species(id)
        );
    """)

    # --- 6. 宝可梦技能定义 ---
    cursor.execute("""
        CREATE TABLE pokemon_moves (
            id INT PRIMARY KEY AUTO_INCREMENT COMMENT '技能ID',
            name VARCHAR(50) NOT NULL COMMENT '技能名称',
            type_id INT COMMENT '技能属性类型ID',
            category ENUM('Physical','Special','Status') NOT NULL COMMENT '技能类别：物理/特殊/变化',
            power INT COMMENT '威力',
            accuracy INT COMMENT '命中率',
            pp INT COMMENT '可使用次数PP',
            description TEXT COMMENT '技能描述',
            FOREIGN KEY (type_id) REFERENCES pokemon_types(id)
        )
    """)

    # --- 7. 玩家宝可梦进化关系 ---
    cursor.execute("""
        CREATE TABLE pokemon_evolution (
            from_species_id INT COMMENT '进化前种族ID',
            to_species_id INT COMMENT '进化后种族ID',
            method ENUM('LevelUp','Item','Trade','Happiness','Other') NOT NULL COMMENT '进化方式',
            condition_value VARCHAR(50) COMMENT '条件值（等级或道具名等）',
            PRIMARY KEY (from_species_id, to_species_id),
            FOREIGN KEY (from_species_id) REFERENCES pokemon_species(id),
            FOREIGN KEY (to_species_id) REFERENCES pokemon_species(id)
        )
    """)

    # --- 8. 道具系统 ---
    cursor.execute("""
        CREATE TABLE items (    
            id INT PRIMARY KEY AUTO_INCREMENT COMMENT '道具ID',
            name VARCHAR(50) NOT NULL COMMENT '道具名称',
            type ENUM('Healing','Pokeball','Battle','Evolution','Misc') NOT NULL COMMENT '道具类型',
            description TEXT COMMENT '道具说明'
        )
    """)

    cursor.execute("""
        CREATE TABLE user_items (
            user_id BIGINT COMMENT '玩家ID',
            item_id INT COMMENT '道具ID',
            quantity INT DEFAULT 0 COMMENT '持有数量',
            PRIMARY KEY (user_id, item_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_id) REFERENCES items(id)
        )
    """)

    # --- 9. 玩家队伍配置 ---
    cursor.execute("""
        CREATE TABLE user_team (
            user_id BIGINT PRIMARY KEY COMMENT '玩家ID',
            team JSON COMMENT '队伍配置（6个宝可梦实例ID的数组）',
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # --- 10. 玩家战斗记录 ---
    cursor.execute("""
        CREATE TABLE battle_records (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '战斗记录ID',
            user1_id BIGINT COMMENT '玩家1 ID',
            user2_id BIGINT COMMENT '玩家2 ID（可能为NPC）',
            winner_id BIGINT COMMENT '获胜者ID',
            battle_type ENUM('PvE','PvP','Gym','Raid') DEFAULT 'PvE' COMMENT '战斗类型',
            battle_log TEXT COMMENT '战斗日志或记录详情（JSON或文本）',
            start_time DATETIME COMMENT '战斗开始时间',
            end_time DATETIME COMMENT '战斗结束时间',
            FOREIGN KEY (user1_id) REFERENCES users(user_id),
            FOREIGN KEY (user2_id) REFERENCES users(user_id)
        )
    """)
