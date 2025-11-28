import sqlite3
import threading
import dataclasses
from typing import Optional, List, Any
from datetime import datetime

from ...core.models.pokemon_models import PokemonIVs, PokemonEVs, PokemonStats, PokemonMoves
from ...core.models.user_models import User, UserItems, UserItemInfo
from ...core.models.pokemon_models import UserPokemonInfo
from .abstract_repository import AbstractUserPokemonRepository


class SqliteUserPokemonRepository(AbstractUserPokemonRepository):
    """用户宝可梦数据仓储的SQLite实现"""

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

    def get_user_pokedex_ids(self, user_id: str) -> dict[str,Any]:
        """
        获取用户的图鉴开启状态
        返回: {'caught': {id1, id2...}, 'seen': {id3, id4...}}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. 查询已捕捉的种族ID (user_pokemon 表)
            cursor.execute("""
                SELECT DISTINCT species_id FROM user_pokemon
                WHERE user_id = ? AND isdel = 0
            """, (user_id,))
            caught_ids = {row[0] for row in cursor.fetchall()}

            # 2. 查询已遇到的种族ID (wild_pokemon_encounter_log 表)
            # wild_pokemon_encounter_log 关联 wild_pokemon 表获取 species_id
            cursor.execute("""
                SELECT DISTINCT w.species_id
                FROM wild_pokemon_encounter_log log
                JOIN wild_pokemon w ON log.wild_pokemon_id = w.id
                WHERE log.user_id = ? AND log.isdel = 0 AND w.isdel = 0
            """, (user_id,))
            seen_ids = {row[0] for row in cursor.fetchall()}

            # 这里的seen应该包含caught (捕捉了肯定算遇见了)
            seen_ids.update(caught_ids)

            return {
                "caught": caught_ids,
                "seen": seen_ids
            }