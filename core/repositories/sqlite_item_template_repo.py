import sqlite3
import threading
from typing import Optional, List, Dict, Any

# 导入抽象基类和领域模型
from .abstract_repository import AbstractItemTemplateRepository
from ..domain.models import Pokemon

class SqliteItemTemplateRepository(AbstractItemTemplateRepository):
    """物品模板仓储的SQLite实现"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        """获取一个线程安全的数据库连接。"""
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return conn

    def _row_to_pokemon(self, row: sqlite3.Row) -> Optional[Pokemon]:
        if not row:
            return None
        return Pokemon(**row)

    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[Pokemon]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pokemon_species WHERE id = ?", (pokemon_id,))
            return self._row_to_pokemon(cursor.fetchone())

    def get_all_pokemon(self) -> List[Pokemon]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pokemon_species ORDER BY id DESC")
            return [self._row_to_pokemon(row) for row in cursor.fetchall()]


    def add_pokemon_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_species
                (id, name_en, name_cn, generation, base_hp, base_attack,
                 base_defense, base_sp_attack, base_sp_defense, base_speed,
                height, weight, description)
                VALUES (:id, :name_en, :name_cn, :generation, :base_hp,
                        :base_attack, :base_defense, :base_sp_attack,
                        :base_sp_defense, :base_speed, :height, :weight,
                        :description)
            """, {**data})
            conn.commit()

    def add_pokemon_type_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_types
                (name)
                VALUES (:name)
            """, {**data})
            conn.commit()

    def add_pokemon_species_type_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_species_types
                (species_id, type_id)
                VALUES (:species_id, :type_id)
            """, {**data})
            conn.commit()

    def add_pokemon_evolution_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_evolutions
                (from_species_id, to_species_id, method, condition_value)
                VALUES (:from_species_id, :to_species_id, :method, :condition_value)
            """, {**data})
            conn.commit()

    def add_item_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO items
                (id, name, rarity, price, type, description)
                VALUES (:id, :name, :rarity, :price, :type, :description)
            """, {**data})
            conn.commit()

    def add_pokemon_move_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_moves
                (id, name, type_id, category, power, accuracy, pp, description)
                VALUES (:id, :name, :type_id, :category, :power, :accuracy, :pp, :description)
            """, {**data})
            conn.commit()

    def add_pokemon_species_move_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_species_moves
                (species_id, move_id, learn_method, learn_value)
                VALUES (:species_id, :move_id, :learn_method, :learn_value)
            """, {**data})
            conn.commit()
