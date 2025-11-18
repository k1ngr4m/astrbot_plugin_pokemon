import json
import random
import sqlite3
import threading
import dataclasses
from typing import Optional, List, Dict, Any
from datetime import datetime

from astrbot.api import logger
from .abstract_repository import AbstractTeamRepository
from ..domain.user_models import UserTeam


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

    def get_user_team(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的队伍配置
        Args:
            user_id: 用户ID
        Returns:
            队伍配置的字典，如果不存在或格式错误则返回空字典
        """
        sql = "SELECT team FROM user_team WHERE user_id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()

            if not row:
                return {}

            try:
                # 将 JSON 字符串反序列化为字典
                return json.loads(row["team"])
            except (json.JSONDecodeError, TypeError) as e:
                # 处理 JSON 格式错误或字段为空的情况
                print(f"解析队伍配置失败：{e}")
                return {}

    def update_user_team(self, user_id: str, team_data: UserTeam) -> None:
        """
        更新用户的队伍配置
        Args:
            user_id: 用户ID
            team_data: 队伍配置的JSON字符串
        """
        # 将队伍配置序列化为 JSON 字符串
        team_json = json.dumps(dataclasses.asdict(team_data), ensure_ascii=False)
        sql = """
        INSERT OR REPLACE INTO user_team (user_id, team)
        VALUES (?, ?)
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id, team_json))
            conn.commit()