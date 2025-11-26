import json
import sqlite3
import threading
import dataclasses

from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.user_models import UserTeam
from .abstract_repository import AbstractTeamRepository
from ...core.models.user_models import UserTeam


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

    def get_user_team(self, user_id: str) -> UserTeam | None:
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
                return None

            try:
                team_data = json.loads(row["team"])

                # 判断数据格式：如果是列表格式（新的格式）[2,3,4,5]
                if isinstance(team_data, list):
                    return UserTeam(
                        user_id=user_id,
                        team_pokemon_ids=team_data
                    )
                # 如果是字典格式（旧的格式）{"user_id": "xxx", "team_pokemon_ids": [2, 3, 4, 5]}
                elif isinstance(team_data, dict) and 'team_pokemon_ids' in team_data:
                    # 更新数据库格式为新格式
                    self.update_user_team(user_id, UserTeam(
                        user_id=user_id,
                        team_pokemon_ids=team_data.get('team_pokemon_ids', [])
                    ))
                    return UserTeam(
                        user_id=user_id,
                        team_pokemon_ids=team_data.get('team_pokemon_ids', [])
                    )
                else:
                    return UserTeam(
                        user_id=user_id,
                        team_pokemon_ids=[]
                    )
            except (json.JSONDecodeError, TypeError) as e:
                # 处理 JSON 格式错误或字段为空的情况
                print(f"解析队伍配置失败：{e}")
                return UserTeam(
                    user_id=user_id,
                    team_pokemon_ids=[]
                )

    def update_user_team(self, user_id: str, team_data: UserTeam) -> None:
        """
        更新用户的队伍配置
        Args:
            user_id: 用户ID
            team_data: 队伍配置的JSON字符串
        """
        # 只存储team_pokemon_ids列表
        team_json = json.dumps(team_data.team_pokemon_ids if team_data.team_pokemon_ids else [], ensure_ascii=False)
        sql = """
        INSERT OR REPLACE INTO user_team (user_id, team)
        VALUES (?, ?)
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id, team_json))
            conn.commit()