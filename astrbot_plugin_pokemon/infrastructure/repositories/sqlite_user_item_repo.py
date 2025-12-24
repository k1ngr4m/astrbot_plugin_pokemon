import sqlite3
import threading
from typing import Optional

from .abstract_repository import AbstractUserItemRepository
from ...core.models.user_models import UserItems, UserItemInfo


class SqliteUserItemRepository(AbstractUserItemRepository):
    """用户物品数据仓储的SQLite实现"""

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

    def add_user_item(self, user_id: str, item_id: int, quantity: int) -> None:
        """
        为用户添加物品
        Args:
            user_id: 用户ID
            item_id: 物品ID
            quantity: 物品数量
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 检查用户是否已经有该物品
            cursor.execute("""
                SELECT quantity FROM user_items
                WHERE user_id = ? AND item_id = ?
            """, (user_id, item_id))
            row = cursor.fetchone()

            if row:
                # 如果已有该物品，更新数量
                new_quantity = row[0] + quantity
                cursor.execute("""
                    UPDATE user_items
                    SET quantity = ?
                    WHERE user_id = ? AND item_id = ?
                """, (new_quantity, user_id, item_id))
            else:
                # 如果没有该物品，插入新记录
                cursor.execute("""
                    INSERT INTO user_items (user_id, item_id, quantity)
                    VALUES (?, ?, ?)
                """, (user_id, item_id, quantity))
            conn.commit()

    def get_user_items(self, user_id: str) -> UserItems:
        """
        获取用户的所有物品
        Args:
            user_id: 用户ID
        Returns:
            用户物品列表，每个物品包含item_id, item_name, quantity等信息
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 查询用户物品及其详细信息
            sql = """
            SELECT ui.item_id, ui.quantity, i.name_en, i.name_zh, i.category_id, i.description
            FROM user_items ui
            JOIN items i ON ui.item_id = i.id
            WHERE ui.user_id = ? and ui.quantity > 0
            ORDER BY i.category_id DESC, i.name_zh
            """
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            items_list = []
            for row in rows:
                items_list.append(UserItemInfo(
                        item_id=row[0],
                        quantity=row[1],
                        name_en=row[2],
                        name_zh=row[3],
                        category_id=row[4],
                        description=row[5]
                ))
            user_items: UserItems = UserItems(
                user_id=user_id,
                items=items_list
            )
            return user_items

    def get_user_item_by_id(self, user_id: str, item_id: int) -> Optional[UserItemInfo]:
        """
        根据用户ID和物品ID获取用户物品信息
        Args:
            user_id: 用户ID
            item_id: 物品ID
        Returns:
            用户物品信息，如果不存在则返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 查询用户物品及其详细信息
            sql = """
            SELECT ui.item_id, ui.quantity, i.name_en, i.name_zh, i.category_id, i.description
            FROM user_items ui
            JOIN items i ON ui.item_id = i.id
            WHERE ui.user_id = ? AND ui.item_id = ? and ui.quantity > 0
            ORDER BY i.category_id DESC, i.name_zh
            """
            cursor.execute(sql, (user_id, item_id))
            row = cursor.fetchone()
            if row:
                return UserItemInfo(
                    item_id=row[0],
                    quantity=row[1],
                    name_en=row[2],
                    name_zh=row[3],
                    category_id=row[4],
                    description=row[5]
                )
            else:
                return None
