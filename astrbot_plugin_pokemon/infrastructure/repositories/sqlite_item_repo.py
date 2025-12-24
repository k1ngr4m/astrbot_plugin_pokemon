import sqlite3
import threading
from typing import Optional, Dict, Any, List

from .abstract_repository import AbstractItemRepository


class SqliteItemRepository(AbstractItemRepository):
    """冒险区域数据仓储的SQLite实现"""

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

    # ==========增==========
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

    # ==========查==========
    def get_item_name(self, item_id: int) -> Optional[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name_zh FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return row["name_zh"] if row else None

    def get_random_item(self) -> Optional[Dict[str, Any]]:
        """随机获取一个物品"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items ORDER BY RANDOM() LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_items(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """根据物品ID获取完整的物品信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
