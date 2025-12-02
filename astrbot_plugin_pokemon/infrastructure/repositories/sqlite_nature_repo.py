import sqlite3
import threading
from typing import Optional, List, Dict, Any

from .abstract_repository import AbstractNatureRepository


class SqliteNatureRepository(AbstractNatureRepository):
    """性格数据仓储的SQLite实现"""

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
    def add_nature_template(self, nature_data: Dict[str, Any]) -> None:
        """添加性格模板"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           INSERT OR IGNORE INTO natures
                               (id, name_en, name_zh, decreased_stat_id, increased_stat_id,
                                hates_flavor_id, likes_flavor_id, game_index)
                           VALUES (:id, :name_en, :name_zh, :decreased_stat_id, :increased_stat_id,
                                   :hates_flavor_id, :likes_flavor_id, :game_index)
                           """, {**nature_data})
            conn.commit()

    def add_nature_templates_batch(self, nature_data_list: List[Dict[str, Any]]) -> None:
        """批量添加性格模板"""
        if not nature_data_list:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                               INSERT OR IGNORE INTO natures
                                   (id, name_en, name_zh, decreased_stat_id, increased_stat_id,
                                    hates_flavor_id, likes_flavor_id, game_index)
                               VALUES (:id, :name_en, :name_zh, :decreased_stat_id, :increased_stat_id,
                                       :hates_flavor_id, :likes_flavor_id, :game_index)
                               """, nature_data_list)
            conn.commit()

    def add_nature_stat_template(self, nature_stat_data: Dict[str, Any]) -> None:
        """添加性格属性模板"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           INSERT OR IGNORE INTO nature_stats
                               (nature_id, pokeathlon_stat_id, max_change)
                           VALUES (:nature_id, :pokeathlon_stat_id, :max_change)
                           """, {**nature_stat_data})
            conn.commit()

    def add_nature_stat_templates_batch(self, nature_stat_data_list: List[Dict[str, Any]]) -> None:
        """批量添加性格属性模板"""
        if not nature_stat_data_list:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                               INSERT OR IGNORE INTO nature_stats
                                   (nature_id, pokeathlon_stat_id, max_change)
                               VALUES (:nature_id, :pokeathlon_stat_id, :max_change)
                               """, nature_stat_data_list)
            conn.commit()

    # ==========查==========
    def get_nature_by_id(self, nature_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取性格"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT * FROM natures
                           WHERE id = ? AND isdel = 0
                           """, (nature_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_natures(self) -> List[Dict[str, Any]]:
        """获取所有性格"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT * FROM natures
                           WHERE isdel = 0
                           ORDER BY id
                           """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_nature_stats_by_nature_id(self, nature_id: int) -> List[Dict[str, Any]]:
        """根据性格ID获取性格属性"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT * FROM nature_stats
                           WHERE nature_id = ? AND isdel = 0
                           """, (nature_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]