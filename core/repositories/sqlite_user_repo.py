import sqlite3
import threading
import dataclasses
from typing import Optional, List, Dict, Any
from datetime import datetime

from astrbot.api import logger
from ..domain.models import User
from .abstract_repository import AbstractUserRepository

class SqliteUserRepository(AbstractUserRepository):
    """用户数据仓储的SQLite实现"""

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

    def _row_to_user(self, row: sqlite3.Row) -> Optional[User]:
        """
                [已修正] 将数据库行安全地转换为 User 对象。
                现在可以正确读取所有新旧字段。
                """
        if not row:
            return None

        def parse_datetime(dt_val):
            if isinstance(dt_val, datetime):
                return dt_val
            if isinstance(dt_val, str):
                try:
                    return datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
                except ValueError:
                    try:
                        return datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        try:
                            return datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            return None
            return None

            # 使用 .keys() 检查字段是否存在，确保向后兼容性
        row_keys = row.keys()

        return User(
            user_id=row["user_id"],
            nickname=row["nickname"],
            coins=row["coins"],
            level=row["level"],
            exp=row["exp"],
            init_selected = row["init_selected"],
            created_at=parse_datetime(row["created_at"]),
        )

    def get_by_id(self, user_id: str) -> Optional[User]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return self._row_to_user(row)

    def check_exists(self, user_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None

    def add(self, user: User) -> None:
        # 使用与 update 相同的动态方法，确保 add 也是完整的
        fields = [f.name for f in dataclasses.fields(User)]
        columns_clause = ", ".join(fields)
        placeholders_clause = ", ".join(["?"] * len(fields))
        values = [getattr(user, field) for field in fields]

        sql = f"INSERT INTO users ({columns_clause}) VALUES ({placeholders_clause})"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(values))
            conn.commit()

    def create_user_pokemon(self, user_id: str, species_id: int, nickname: Optional[str] = None) -> int:
        """
        创建用户宝可梦记录
        Args:
            user_id: 用户ID
            species_id: 宝可梦种族ID
            nickname: 宝可梦昵称（可选）
        Returns:
            新创建的宝可梦实例ID
        """
        # 获取宝可梦基础数据
        base_sql = """
        SELECT base_hp, base_attack, base_defense, base_sp_attack, base_sp_defense, base_speed
        FROM pokemon_species WHERE id = ?
        """

        sql = """
        INSERT INTO user_pokemon (
            user_id, species_id, nickname, level, exp, gender,
            hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv,
            hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev,
            current_hp, is_shiny, moves, caught_time
        )
        VALUES (?, ?, ?, 1, 0, 'N',
            0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0,
            ?, 0, '[]', CURRENT_TIMESTAMP
        )
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 先获取基础HP值
            cursor.execute(base_sql, (species_id,))
            base_row = cursor.fetchone()
            base_hp = base_row[0] if base_row else 0

            # 创建宝可梦记录
            cursor.execute(sql, (user_id, species_id, nickname, base_hp))
            conn.commit()
            return cursor.lastrowid

    def update_init_select(self, user_id: str, pokemon_id: int) -> None:
        """
        更新用户的初始选择状态
        Args:
            user_id: 用户ID
            pokemon_id: 选择的宝可梦ID
        """
        sql = "UPDATE users SET init_selected = ? WHERE user_id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (pokemon_id, user_id))
            conn.commit()

    def get_user_pokemon(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的所有宝可梦
        Args:
            user_id: 用户ID
        Returns:
            用户宝可梦列表
        """
        sql = """
        SELECT up.*, ps.name_cn as species_name, ps.name_en as species_en_name
        FROM user_pokemon up
        JOIN pokemon_species ps ON up.species_id = ps.id
        WHERE up.user_id = ?
        ORDER BY up.id
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

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