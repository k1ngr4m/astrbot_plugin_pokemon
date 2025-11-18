import sqlite3
import threading
from csv import DictWriter
from typing import Optional, List, Dict, Any
from ..domain.adventure_models import AdventureArea, AreaPokemon
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

    def get_all_areas(self) -> List[AdventureArea]:
        """获取所有冒险区域"""
        sql = "SELECT * FROM adventure_areas ORDER BY area_code"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [AdventureArea(
                id=row["id"],
                area_code=row["area_code"],
                area_name=row["area_name"],
                description=row["description"],
                min_level=row["min_level"],
                max_level=row["max_level"]
            ) for row in rows]

    def get_area_by_code(self, area_code: str) -> Optional[AdventureArea]:
        """根据区域代码获取冒险区域"""
        sql = "SELECT * FROM adventure_areas WHERE area_code = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (area_code,))
            row = cursor.fetchone()
            if row:
                return AdventureArea(
                    id=row["id"],
                    area_code=row["area_code"],
                    area_name=row["name"],
                    description=row["description"],
                    min_level=row["min_level"],
                    max_level=row["max_level"]
                )
            return None

    def get_area_pokemon_by_area_id(self, area_id: int) -> List[AreaPokemon]:
        """根据区域ID获取该区域的宝可梦列表"""
        sql = """
        SELECT ap.*, ps.name_cn as pokemon_name
        FROM area_pokemon ap
        JOIN pokemon_species ps ON ap.pokemon_species_id = ps.id
        WHERE ap.area_id = ?
        ORDER BY ap.encounter_rate DESC
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (area_id,))
            rows = cursor.fetchall()
            return [AreaPokemon(
                id=row["id"],
                area_id=row["area_id"],
                pokemon_species_id=row["pokemon_species_id"],
                encounter_rate=row["encounter_rate"],
                min_level=row["min_level"],
                max_level=row["max_level"]
            ) for row in rows]

    def get_area_pokemon_by_area_code(self, area_code: str) -> List[AreaPokemon]:
        """根据区域代码获取该区域的宝可梦列表"""
        sql = """
        SELECT ap.*, ps.name_cn as pokemon_name
        FROM area_pokemon ap
        JOIN pokemon_species ps ON ap.pokemon_species_id = ps.id
        JOIN adventure_areas aa ON ap.area_id = aa.id
        WHERE aa.area_code = ?
        ORDER BY ap.encounter_rate DESC
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (area_code,))
            rows = cursor.fetchall()
            return [AreaPokemon(
                id=row["id"],
                area_id=row["area_id"],
                pokemon_species_id=row["pokemon_species_id"],
                encounter_rate=row["encounter_rate"],
                min_level=row["min_level"],
                max_level=row["max_level"]
            ) for row in rows]

    def add_area_template(self, data: Dict[str, Any]) -> None:
        """添加新的冒险区域"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO adventure_areas 
                    (area_code, name, description, min_level, max_level)
                VALUES (:area_code, :name, :description, :min_level, :max_level)
            """, {**data})
            conn.commit()

    def add_area_pokemon_template(self, data: Dict[str, Any]) -> None:
        """添加区域宝可梦关联"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO area_pokemon 
                    (area_id, pokemon_species_id, encounter_rate, min_level, max_level)
                VALUES (:area_id, :pokemon_species_id, :encounter_rate, :min_level, :max_level)
            """, {**data})
            conn.commit()