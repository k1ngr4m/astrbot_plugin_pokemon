import sqlite3
import threading
from typing import Optional, List, Dict, Any

from data.plugins.astrbot_plugin_fishing.core.domain.models import ShopItem
from .abstract_repository import AbstractUserRepository, AbstractShopRepository
from ..domain.models import Shop


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
                SELECT shop_id, item_id, price, stock, is_active
                FROM shop_items
                WHERE shop_id = ?
            """, (shop_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def check_shop_exists_by_code(self, shop_code: str) -> bool:
        """检查商店是否存在"""
        shop = self.get_shop_by_code(shop_code)
        return shop is not None