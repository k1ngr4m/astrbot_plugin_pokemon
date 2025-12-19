import sqlite3
import threading
from typing import Optional, List, Dict, Any

from .abstract_repository import AbstractPokemonAbilityRelationRepository
from ...core.models.pokemon_models import PokemonAbilityRelation


class SqlitePokemonAbilityRelationRepository(AbstractPokemonAbilityRelationRepository):
    """宝可梦特性关联仓储的SQLite实现"""

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

    def add_pokemon_ability_relation_template(self, relation_data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_abilities
                (pokemon_id, ability_id, is_hidden, slot)
                VALUES (:pokemon_id, :ability_id, :is_hidden, :slot)
            """, {**relation_data})
            conn.commit()

    def add_pokemon_ability_relation_templates_batch(self, relation_data_list: List[Dict[str, Any]]) -> None:
        if not relation_data_list:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO pokemon_abilities
                (pokemon_id, ability_id, is_hidden, slot)
                VALUES (:pokemon_id, :ability_id, :is_hidden, :slot)
            """, relation_data_list)
            conn.commit()

    def get_abilities_by_pokemon_id(self, pokemon_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pokemon_abilities
                WHERE pokemon_id = ? AND isdel = 0
                ORDER BY slot ASC
            """, (pokemon_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_ability_relation_by_pokemon_and_ability_id(self, pokemon_id: int, ability_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pokemon_abilities
                WHERE pokemon_id = ? AND ability_id = ? AND isdel = 0
            """, (pokemon_id, ability_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_pokemon_ability_relations(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pokemon_abilities
                WHERE isdel = 0
                ORDER BY pokemon_id ASC, slot ASC
            """)
            return [dict(row) for row in cursor.fetchall()]