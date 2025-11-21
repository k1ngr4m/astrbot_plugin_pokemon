import sqlite3
from astrbot.api import logger


def up(cursor: sqlite3.Cursor):
    """
    应用此迁移：创建项目所需的全部初始表和索引（SQLite版本）
    """
    logger.debug("正在执行 003_initial_shop_table: 创建所有商店表...")

    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. 创建 shops 表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            shop_type TEXT NOT NULL DEFAULT 'normal' CHECK (shop_type IN ('normal','premium','limited')),
            is_active INTEGER DEFAULT 1 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            isdel TINYINT(10) DEFAULT 0         -- 是否已删除
        )
        """
    )

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
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            isdel TINYINT(10) DEFAULT 0,         -- 是否已删除
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
            UNIQUE(shop_id, item_id)                  -- 确保商店内同一道具只出现一次
        );
    """)

    # 为商店表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shops_id ON shops(id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shops_type ON shops(shop_type)")

    # 为商店商品表创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shop_items_shop_id ON shop_items(shop_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shop_items_item_id ON shop_items(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shop_items_active ON shop_items(is_active)")