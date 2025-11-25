import sqlite3
import threading
from typing import Optional

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

    def get_item_name(self, item_id: int) -> Optional[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name_zh FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return row["name_zh"] if row else None
