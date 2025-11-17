import random
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

        user_data = {
            'user_id': row["user_id"],
            'nickname': row["nickname"],
            'coins': row["coins"],
            'level': row["level"],
            'exp': row["exp"],
            'init_selected': row["init_selected"],
            'created_at': parse_datetime(row["created_at"]),
        }

        # 如果数据库行包含 last_adventure_time 字段，则添加
        if "last_adventure_time" in row_keys:
            user_data['last_adventure_time'] = row["last_adventure_time"]

        return User(**user_data)

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

    def add_user(self, user: User) -> None:
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
        创建用户宝可梦记录，使用模板数据完善实例
        Args:
            user_id: 用户ID
            species_id: 宝可梦种族ID
            nickname: 宝可梦昵称（可选）
        Returns:
            新创建的宝可梦实例ID
        """
        sql = """
        INSERT INTO user_pokemon (
            user_id, species_id, nickname, level, exp, gender,
            hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv,
            hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev,
            current_hp, attack, defense, sp_attack, sp_defense, speed,
            is_shiny, moves, caught_time, shortcode
        )
        VALUES (?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, CURRENT_TIMESTAMP, ?
        )
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 先获取基础数据
            cursor.execute(base_sql, (species_id,))
            base_row = cursor.fetchone()

            if base_row:
                base_hp, base_attack, base_defense, base_sp_attack, base_sp_defense, base_speed = base_row
                # 计算初始HP值，等级为1
                # 宝可梦的HP计算公式：int((种族值*2 + 个体值 + 努力值/4) * 等级/100) + 等级 + 10
                base_calc = int((base_hp * 2 + hp_iv + hp_ev // 4) * level / 100) + level + 10
                # 确保HP至少为基础值的一半（向下取整后至少为1）
                min_hp = max(1, base_hp // 2)
                current_hp = max(min_hp, base_calc)

                # 计算其他属性值（非HP属性使用不同的计算公式）
                # 非HP属性计算公式：int(((种族值*2 + 个体值 + 努力值/4) * 等级/100) + 5) * 性情修正
                # 对于1级宝可梦，没有性情修正，所以公式为：int(((种族值*2 + 个体值) * 1/100) + 5)
                calculated_attack = int((base_attack * 2 + attack_iv + attack_ev // 4) * level / 100) + 5
                calculated_defense = int((base_defense * 2 + defense_iv + defense_ev // 4) * level / 100) + 5
                calculated_sp_attack = int((base_sp_attack * 2 + sp_attack_iv + sp_attack_ev // 4) * level / 100) + 5
                calculated_sp_defense = int((base_sp_defense * 2 + sp_defense_iv + sp_defense_ev // 4) * level / 100) + 5
                calculated_speed = int((base_speed * 2 + speed_iv + speed_ev // 4) * level / 100) + 5
            else:
                base_hp = 0
                current_hp = 0
                calculated_attack = 0
                calculated_defense = 0
                calculated_sp_attack = 0
                calculated_sp_defense = 0
                calculated_speed = 0

            # 获取新记录的ID（先插入然后获取ID用于生成短码）
            cursor.execute(sql, (
                user_id, species_id, nickname, level, exp, gender,
                hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv,
                hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev,
                current_hp, calculated_attack, calculated_defense, calculated_sp_attack, calculated_sp_defense, calculated_speed,
                is_shiny, moves, f"P{0:04d}"
            ))
            new_id = cursor.lastrowid
            conn.commit()

            # 更新记录的shortcode字段
            shortcode = f"P{new_id:04d}"
            update_shortcode_sql = "UPDATE user_pokemon SET shortcode = ? WHERE id = ?"
            cursor.execute(update_shortcode_sql, (shortcode, new_id))
            conn.commit()

            return new_id

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
            result = []
            for row in rows:
                row_dict = dict(row)
                # 添加短码ID，如果数据库中没有则生成默认值
                if not row_dict.get('shortcode'):
                    row_dict['shortcode'] = f"P{row_dict['id']:04d}"
                result.append(row_dict)
            return result

    def get_user_pokemon_by_id(self, pokemon_id: str) -> Optional[Dict[str, Any]]:
        """
        通过ID获取用户的宝可梦实例（支持短码ID和数字ID）
        Args:
            pokemon_id: 宝可梦实例ID（可以是P开头的短码或数字）
        Returns:
            宝可梦实例信息（如果存在）
        """
        # 如果ID以P开头，使用短码查询
        if pokemon_id.startswith('P') and pokemon_id[1:].isdigit():
            return self.get_user_pokemon_by_shortcode(pokemon_id)
        # 否则尝试作为数字ID查询
        elif pokemon_id.isdigit():
            pokemon_numeric_id = int(pokemon_id)
            return self.get_user_pokemon_by_numeric_id(pokemon_numeric_id)
        else:
            return None

    def get_user_pokemon_by_numeric_id(self, pokemon_numeric_id: int) -> Optional[Dict[str, Any]]:
        """
        通过数字ID获取用户的宝可梦实例
        Args:
            pokemon_numeric_id: 宝可梦实例数字ID
        Returns:
            宝可梦实例信息（如果存在）
        """
        sql = """
        SELECT up.*, ps.name_cn as species_name, ps.name_en as species_en_name
        FROM user_pokemon up
        JOIN pokemon_species ps ON up.species_id = ps.id
        WHERE up.id = ?
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (pokemon_numeric_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_pokemon_by_shortcode(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """
        通过短码获取用户的宝可梦实例
        Args:
            shortcode: 宝可梦短码ID（格式如P001）
        Returns:
            宝可梦实例信息（如果存在）
        """
        sql = """
        SELECT up.*, ps.name_cn as species_name, ps.name_en as species_en_name
        FROM user_pokemon up
        JOIN pokemon_species ps ON up.species_id = ps.id
        WHERE up.shortcode = ?
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (shortcode,))
            row = cursor.fetchone()
            return dict(row) if row else None

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

    def add_user_checkin(self, user_id: str, checkin_date: str, gold_reward: int, item_reward_id: int = 1, item_quantity: int = 1) -> None:
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

    def get_user_items(self, user_id: str) -> list:
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
            SELECT ui.item_id, ui.quantity, i.name, i.type, i.description, i.rarity
            FROM user_items ui
            JOIN items i ON ui.item_id = i.id
            WHERE ui.user_id = ?
            ORDER BY i.type, i.rarity DESC, i.name
            """
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()

            user_items = []
            for row in rows:
                user_items.append({
                    "item_id": row[0],
                    "quantity": row[1],
                    "name": row[2],
                    "type": row[3],
                    "description": row[4],
                    "rarity": row[5]
                })

            return user_items

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