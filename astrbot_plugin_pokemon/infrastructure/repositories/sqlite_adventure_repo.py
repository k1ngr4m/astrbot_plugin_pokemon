import sqlite3
import threading
from typing import Optional, List, Dict, Any
from ...core.models.adventure_models import LocationPokemon, LocationTemplate, GymInfo, UserBadge, UserGymState
from .abstract_repository import AbstractAdventureRepository


class SqliteAdventureRepository(AbstractAdventureRepository):
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

    def get_all_locations(self) -> List[LocationTemplate]:
        """获取所有冒险区域"""
        sql = "SELECT * FROM locations ORDER BY id"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [LocationTemplate(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                min_level=row["min_level"],
                max_level=row["max_level"]
            ) for row in rows]



    def get_location_by_id(self, location_id: int) -> Optional[LocationTemplate]:
        """根据区域ID获取冒险区域"""
        sql = "SELECT * FROM locations WHERE id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (location_id,))
            row = cursor.fetchone()
            if row:
                return LocationTemplate(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    min_level=row["min_level"],
                    max_level=row["max_level"]
                )
            return None

    def get_location_pokemon_by_location_id(self, location_id: int) -> List[LocationPokemon]:
        """根据区域ID获取该区域的宝可梦列表"""
        sql = """
        SELECT ap.*, ps.name_zh as pokemon_name
        FROM location_pokemon ap
        JOIN pokemon_species ps ON ap.pokemon_species_id = ps.id
        WHERE ap.location_id = ?
        ORDER BY ap.encounter_rate DESC
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (location_id,))
            rows = cursor.fetchall()
            return [LocationPokemon(
                id=row["id"],
                location_id=row["location_id"],
                pokemon_species_id=row["pokemon_species_id"],
                encounter_rate=row["encounter_rate"],
                min_level=row["min_level"],
                max_level=row["max_level"]
            ) for row in rows]

    def add_location_template(self, data: Dict[str, Any]) -> None:
        """添加新的冒险区域"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO locations 
                    (id, name, description, min_level, max_level)
                VALUES (:id, :name, :description, :min_level, :max_level)
            """, {**data})
            conn.commit()

    def add_location_pokemon_template(self, data: Dict[str, Any]) -> None:
        """添加地点宝可梦关联"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO location_pokemon 
                    (id, location_id, pokemon_species_id, encounter_rate, min_level, max_level)
                VALUES (:id, :location_id, :pokemon_species_id, :encounter_rate, :min_level, :max_level)
            """, {**data})
            conn.commit()

    def get_gym_by_location(self, location_id: int) -> Optional[GymInfo]:
        """根据区域ID获取冒险区域"""
        sql = "SELECT * FROM gyms WHERE location_id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (location_id,))
            row = cursor.fetchone()
            if row:
                # 解析精英ID列表
                elite_ids = []
                if row["elite_trainer_ids"]:
                    elite_ids = [int(x) for x in row["elite_trainer_ids"].split('|') if x]
                
                return GymInfo(
                    id=row["id"],
                    location_id=row["location_id"],
                    name=row["name"],
                    description=row["description"],
                    elite_trainer_ids=elite_ids,
                    boss_trainer_id=row["boss_trainer_id"],
                    required_level=row["required_level"],
                    unlock_location_id=row["unlock_location_id"],
                    reward_item_id=row["reward_item_id"]
                )
            return None

    def add_gym_template(self, data: Dict[str, Any]) -> None:
        """添加道馆模板"""
        # data中的elite_trainer_ids可能是list或str，需处理
        gym_data = data.copy()
        if isinstance(gym_data.get('elite_trainer_ids'), list):
            gym_data['elite_trainer_ids'] = "|".join(map(str, gym_data['elite_trainer_ids']))
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO gyms 
                    (id, location_id, name, description, elite_trainer_ids, boss_trainer_id, required_level, unlock_location_id, reward_item_id)
                VALUES (:id, :location_id, :name, :description, :elite_trainer_ids, :boss_trainer_id, :required_level, :unlock_location_id, :reward_item_id)
            """, gym_data)
            conn.commit()

    # ==========徽章管理==========
    def add_user_badge(self, user_id: str, gym_id: int, badge_id: int) -> None:
        import time
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO user_badges (user_id, gym_id, badge_id, obtained_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, gym_id, badge_id, int(time.time())))
            conn.commit()

    def get_user_badges(self, user_id: str) -> List[UserBadge]:
        sql = "SELECT * FROM user_badges WHERE user_id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            return [UserBadge(
                user_id=row["user_id"],
                gym_id=row["gym_id"],
                badge_id=row["badge_id"],
                obtained_at=row["obtained_at"]
            ) for row in rows]

    def has_badge(self, user_id: str, badge_id: int) -> bool:
        sql = "SELECT 1 FROM user_badges WHERE user_id = ? AND badge_id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id, badge_id))
            return cursor.fetchone() is not None

    # ==========道馆状态管理==========
    def save_gym_state(self, state: UserGymState) -> None:
        import time
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_gym_state (user_id, gym_id, current_stage, is_active, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (state.user_id, state.gym_id, state.current_stage, 1 if state.is_active else 0, int(time.time())))
            conn.commit()

    def get_gym_state(self, user_id: str) -> Optional[UserGymState]:
        sql = "SELECT * FROM user_gym_state WHERE user_id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()
            if row:
                return UserGymState(
                    user_id=row["user_id"],
                    gym_id=row["gym_id"],
                    current_stage=row["current_stage"],
                    is_active=bool(row["is_active"]),
                    last_updated=row["last_updated"]
                )
            return None

    def delete_gym_state(self, user_id: str) -> None:
        sql = "DELETE FROM user_gym_state WHERE user_id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            conn.commit()