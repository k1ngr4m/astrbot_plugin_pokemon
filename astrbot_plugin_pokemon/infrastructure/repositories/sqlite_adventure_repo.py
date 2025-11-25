import sqlite3
import threading
from typing import Optional, List, Dict, Any
from ...core.models.adventure_models import LocationPokemon, LocationTemplate
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