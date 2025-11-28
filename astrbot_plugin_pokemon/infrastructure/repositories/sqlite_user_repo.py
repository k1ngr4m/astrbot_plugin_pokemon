import sqlite3
import threading
import dataclasses
from typing import Optional, List
from datetime import datetime

from ...core.models.pokemon_models import PokemonIVs, PokemonEVs, PokemonStats, PokemonMoves
from ...core.models.user_models import User, UserItems, UserItemInfo
from ...core.models.pokemon_models import UserPokemonInfo
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
        将数据库行安全地转换为 User 对象。
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

        user_data = {
            'user_id': row["user_id"],
            'nickname': row["nickname"],
            'level': row["level"],
            'exp': row["exp"],
            'coins': row["coins"],
            'init_selected': row["init_selected"],
            'created_at': parse_datetime(row["created_at"]),
        }

        # 如果数据库行包含其他可选字段，则添加
        if "last_adventure_time" in row_keys:
            user_data['last_adventure_time'] = row["last_adventure_time"]
        if "updated_at" in row_keys:
            user_data['updated_at'] = parse_datetime(row["updated_at"])
        if "isdel" in row_keys:
            user_data['isdel'] = row["isdel"]
        if "origin_id" in row_keys:
            user_data['origin_id'] = row["origin_id"]

        return User(**user_data)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return self._row_to_user(row)

    def add_pokemon_user(self, user: User) -> None:
        # 使用与 update 相同的动态方法，确保 add 也是完整的
        # 排除 created_at 和 updated_at 字段，以便使用数据库的默认 CURRENT_TIMESTAMP
        # 排除 isdel 字段，使用数据库默认值
        all_fields = [f.name for f in dataclasses.fields(User)]
        fields_to_exclude = {'created_at', 'updated_at', 'isdel'}
        fields = [f for f in all_fields if f not in fields_to_exclude]
        columns_clause = ", ".join(fields)
        placeholders_clause = ", ".join(["?"] * len(fields))
        values = [getattr(user, field) for field in fields]

        sql = f"INSERT INTO users ({columns_clause}) VALUES ({placeholders_clause})"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(values))
            conn.commit()


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

    def _row_to_user_pokemon(self, row: sqlite3.Row) -> UserPokemonInfo:
        """
        将数据库行转换为 UserPokemonInfo 对象
        """
        row_dict = dict(row)

        # 构造 PokemonStats 对象
        stats = PokemonStats(
            hp=row_dict['hp'],
            attack=row_dict['attack'],
            defense=row_dict['defense'],
            sp_attack=row_dict['sp_attack'],
            sp_defense=row_dict['sp_defense'],
            speed=row_dict['speed']
        )

        # 构造 PokemonIVs 对象
        ivs = PokemonIVs(
            hp_iv=row_dict['hp_iv'],
            attack_iv=row_dict['attack_iv'],
            defense_iv=row_dict['defense_iv'],
            sp_attack_iv=row_dict['sp_attack_iv'],
            sp_defense_iv=row_dict['sp_defense_iv'],
            speed_iv=row_dict['speed_iv']
        )

        # 构造 PokemonEVs 对象
        evs = PokemonEVs(
            hp_ev=row_dict['hp_ev'],
            attack_ev=row_dict['attack_ev'],
            defense_ev=row_dict['defense_ev'],
            sp_attack_ev=row_dict['sp_attack_ev'],
            sp_defense_ev=row_dict['sp_defense_ev'],
            speed_ev=row_dict['speed_ev']
        )

        moves = PokemonMoves(
            move1_id=row_dict['move1_id'],
            move2_id=row_dict['move2_id'],
            move3_id=row_dict['move3_id'],
            move4_id=row_dict['move4_id'],
        )
        # 获取宝可梦名称（优先使用昵称，否则使用物种名称）
        pokemon_name = row_dict['nickname'] or row_dict.get('species_name', 'Unknown')

        return UserPokemonInfo(
            id=row_dict['id'],
            species_id=row_dict['species_id'],
            name=pokemon_name,
            gender=row_dict['gender'],
            level=row_dict['level'],
            exp=row_dict['exp'],
            stats=stats,
            ivs=ivs,
            evs=evs,
            moves=moves,
            caught_time=row_dict['caught_time'],
        )

    def update_user_exp(self, level: int, exp: int, user_id: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET level = ?, exp = ?
                WHERE user_id = ?
            """, (level, exp, user_id))
            conn.commit()

    def has_user_checked_in_today(self, user_id: str, today: str) -> bool:
        """
        检查用户今日是否已签到
        Args:
            user_id: 用户ID
            today: 今日日期，格式为YYYY-MM-DD
        Returns:
            bool: 如果用户今天已签到则返回True，否则返回False
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM user_checkins
                WHERE user_id = ? AND checkin_date = ?
            """, (user_id, today))
            return cursor.fetchone() is not None

    def add_user_checkin(self, user_id: str, checkin_date: str, gold_reward: int, item_reward_id: int = 4, item_quantity: int = 1) -> None:
        """
        为用户添加签到记录
        Args:
            user_id: 用户ID
            checkin_date: 签到日期，格式为YYYY-MM-DD
            gold_reward: 金币奖励
            item_reward_id: 道具奖励ID
            item_quantity: 道具奖励数量
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_checkins (user_id, checkin_date, gold_reward, item_reward_id, item_quantity)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, checkin_date, gold_reward, item_reward_id, item_quantity))
            conn.commit()

    def update_user_coins(self, user_id: str, coins: int) -> None:
        """
        更新用户的金币数量
        Args:
            user_id: 用户ID
            coins: 新的金币数量
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET coins = ?
                WHERE user_id = ?
            """, (coins, user_id))
            conn.commit()

    def update_user_last_adventure_time(self, user_id: str, last_adventure_time: float) -> None:
        """
        更新用户的上次冒险时间
        Args:
            user_id: 用户ID
            last_adventure_time: 上次冒险时间戳
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET last_adventure_time = ?
                WHERE user_id = ?
            """, (last_adventure_time, user_id))
            conn.commit()