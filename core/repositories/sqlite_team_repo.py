import random
import sqlite3
import threading
import dataclasses
from typing import Optional, List, Dict, Any
from datetime import datetime

from astrbot.api import logger
from .abstract_repository import AbstractTeamRepository

class SqliteTeamRepository(AbstractTeamRepository):
    """队伍数据仓储的SQLite实现"""
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

    def get_user_team(self, user_id: str) -> Optional[str]:
        """
        获取用户的队伍配置
        Args:
            user_id: 用户ID
        Returns:
            队伍配置的JSON字符串，如果不存在则返回None
        """
        sql = "SELECT team FROM user_team WHERE user_id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()
            return row["team"] if row else None

    def update_user_team(self, user_id: str, team_data: str) -> None:
        """
        更新用户的队伍配置
        Args:
            user_id: 用户ID
            team_data: 队伍配置的JSON字符串
        """
        sql = """
        INSERT OR REPLACE INTO user_team (user_id, team)
        VALUES (?, ?)
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id, team_data))
            conn.commit()