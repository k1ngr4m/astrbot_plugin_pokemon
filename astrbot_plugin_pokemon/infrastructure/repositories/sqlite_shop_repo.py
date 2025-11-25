import sqlite3
import threading
from typing import Optional, List, Dict, Any

from .abstract_repository import AbstractShopRepository
from ...core.models.shop_models import Shop


class SqliteShopRepository(AbstractShopRepository):
    """商店数据仓储的SQLite实现"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            self._local.connection = conn
        return conn

    def add_item_template(self, item_data: Dict[str, Any]) -> None:
        # 添加物品模板
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           INSERT OR IGNORE INTO items
                               (id, name_en, name_zh, category_id, cost, description)
                           VALUES (:id, :name_en, :name_zh, :category_id, :cost, :description)
                           """, {**item_data})
            conn.commit()

    def add_shop_template(self, shop: Dict[str, Any]) -> None:
        """添加商店"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO shops
                (shop_code, name, description)
                VALUES (:shop_code, :name, :description)
            """, {**shop})
            conn.commit()

    def add_shop_item_template(self, shop_item: Dict[str, Any]) -> None:
        """添加商店商品"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shop_items 
                    (shop_id, item_id, price, stock, is_active)
                VALUES (:shop_id, :item_id, :price, :stock, :is_active)
            """, {**shop_item})
            conn.commit()

    def get_active_shops(self) -> List[Shop]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
                SELECT shop_id, item_id, price, stock, is_active
                FROM shop_items
                WHERE is_active = 1
            """)
        rows = cursor.fetchall()
        return [Shop(
            id=row["shop_id"],
            name=row["name"],
            description=row["description"],
            shop_type=row["shop_type"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        ) for row in rows]
    
    def get_shop_by_code(self, shop_code: str) -> Optional[Shop]:
        """根据商店代码获取商店信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM shops
                WHERE shop_code = ?
            """, (shop_code,))
            row = cursor.fetchone()
            if row:
                return Shop(
                    id=row["id"],
                    shop_code=row["shop_code"],
                    name=row["name"],
                    description=row["description"],
                )
            return None

    def get_shop_items_by_shop_id(self, shop_id: int) -> List[Dict[str, Any]]:
        """获取商店的所有商品"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.shop_id, s.id as shop_item_id, i.name_en, i.name_zh, i.category_id, i.description, i.rarity, s.price, s.stock, s.is_active
                FROM shop_items s 
                JOIN items i ON s.item_id = i.id
                WHERE s.shop_id = ?
            """, (shop_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def check_shop_exists_by_code(self, shop_code: str) -> bool:
        """检查商店是否存在"""
        shop = self.get_shop_by_code(shop_code)
        return shop is not None

    def get_a_shop_item_by_id(self, shop_item_id: int, shop_id: int) -> Optional[Dict[str, Any]]:
        """根据商店商品ID获取商店商品信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT si.id as shop_item_id, si.price, si.stock, i.id as item_id, i.name_en, i.name_zh, i.category_id, i.description
                FROM shop_items si
                JOIN items i ON si.item_id = i.id
                WHERE si.shop_id = ? AND i.id = ? AND si.is_active = 1
            """, (shop_id, shop_item_id))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def update_shop_item_stock(self, shop_item_id: int, stock: int) -> None:
        """更新商店商品库存"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE shop_items
                SET stock = ?
                WHERE id = ?
            """, (stock, shop_item_id))
            conn.commit()
