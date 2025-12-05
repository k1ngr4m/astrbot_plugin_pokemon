"""训练家数据仓储的SQLite实现"""

import sqlite3
import threading
from typing import Optional, List
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.trainer_models import Trainer, TrainerPokemon, TrainerEncounter, TrainerLocation, TrainerDetail
from .abstract_repository import AbstractTrainerRepository
from ...core.models.pokemon_models import PokemonSpecies

class SqliteTrainerRepository(AbstractTrainerRepository):
    """训练家数据仓储的SQLite实现"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection"):
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            self._local.connection = conn
        return self._local.connection

    # ========= 内部辅助方法 =========

    def _row_to_trainer(self, row: sqlite3.Row) -> Trainer:
        """将数据库行转换为Trainer对象"""
        return Trainer(
            id=row['id'],
            name=row['name'],
            trainer_class=row['trainer_class'],
            base_payout=row['base_payout'],
            description=row['description'],
            isdel=row['isdel']
        )

    def _row_to_trainer_pokemon(self, row: sqlite3.Row) -> TrainerPokemon:
        """将数据库行转换为TrainerPokemon对象"""
        return TrainerPokemon(
            id=row['id'],
            trainer_id=row['trainer_id'],
            pokemon_species_id=row['pokemon_species_id'],
            level=row['level'],
            position=row['position'],
            isdel=row['isdel']
        )

    def _row_to_trainer_encounter(self, row: sqlite3.Row) -> TrainerEncounter:
        """将数据库行转换为TrainerEncounter对象"""
        return TrainerEncounter(
            id=row['id'],
            user_id=row['user_id'],
            trainer_id=row['trainer_id'],
            encounter_time=row['encounter_time'],
            battle_result=row['battle_result'],
            isdel=row['isdel']
        )

    def _row_to_trainer_location(self, row: sqlite3.Row) -> TrainerLocation:
        """将数据库行转换为TrainerLocation对象"""
        return TrainerLocation(
            id=row['id'],
            trainer_id=row['trainer_id'],
            location_id=row['location_id'],
            encounter_rate=row['encounter_rate'],
            isdel=row['isdel']
        )

    # ========= 增 =========

    def create_trainer(self, trainer: Trainer) -> int:
        """创建训练家"""
        sql = """
        INSERT INTO trainers (name, trainer_class, base_payout, description)
        VALUES (?, ?, ?, ?)
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(sql, (trainer.name, trainer.trainer_class, trainer.base_payout, trainer.description))
            return cursor.lastrowid

    def create_trainers_batch(self, trainer_list: List[Trainer]) -> None:
        """批量创建训练家"""
        sql = """
        INSERT INTO trainers (name, trainer_class, base_payout, description)
        VALUES (?, ?, ?, ?)
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.executemany(sql, [(t.name, t.trainer_class, t.base_payout, t.description) for t in trainer_list])

    def create_trainer_pokemon(self, trainer_pokemon: TrainerPokemon) -> int:
        """创建训练家宝可梦"""
        sql = """
        INSERT INTO trainer_pokemon (trainer_id, pokemon_species_id, level, position)
        VALUES (?, ?, ?, ?)
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(sql, (trainer_pokemon.trainer_id, trainer_pokemon.pokemon_species_id,
                                trainer_pokemon.level, trainer_pokemon.position))
            return cursor.lastrowid

    def create_trainer_pokemons_batch(self, trainer_pokemon_list: List[TrainerPokemon]) -> None:
        """批量创建训练家宝可梦"""
        sql = """
        INSERT INTO trainer_pokemon (trainer_id, pokemon_species_id, level, position)
        VALUES (?, ?, ?, ?)
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.executemany(sql, [(tp.trainer_id, tp.pokemon_species_id, tp.level, tp.position) for tp in trainer_pokemon_list])

    def create_trainer_encounter(self, encounter: TrainerEncounter) -> int:
        """创建训练家遭遇记录"""
        sql = """
        INSERT INTO trainer_encounters (user_id, trainer_id, battle_result)
        VALUES (?, ?, ?)
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(sql, (encounter.user_id, encounter.trainer_id, encounter.battle_result))
            return cursor.lastrowid

    def create_location_trainers(self, location: TrainerLocation) -> int:
        """创建训练家位置记录"""
        sql = """
        INSERT INTO location_trainers (trainer_id, location_id, encounter_rate)
        VALUES (?, ?, ?)
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(sql, (location.trainer_id, location.location_id, location.encounter_rate))
            return cursor.lastrowid

    def create_location_trainers_batch(self, location_trainer_list: List[TrainerLocation]) -> None:
        """批量创建训练家位置记录"""
        sql = """
        INSERT INTO location_trainers (trainer_id, location_id, encounter_rate)
        VALUES (?, ?, ?)
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.executemany(sql, [(tl.trainer_id, tl.location_id, tl.encounter_rate) for tl in location_trainer_list])

    # ========= 改 =========
    def update_trainer_encounter(self, encounter_id: int, **kwargs) -> None:
        """更新训练家遭遇记录"""
        if not kwargs:
            return

        set_clauses = [f"{key} = ?" for key in kwargs.keys()]

        sql = f"""
            UPDATE trainer_encounters
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """

        params = list(kwargs.values()) + [encounter_id]
        conn = self._get_connection()
        with conn:
            conn.execute(sql, params)

    # ========= 查 =========

    def get_trainer_by_id(self, trainer_id: int) -> Optional[Trainer]:
        """根据ID获取训练家"""
        sql = "SELECT * FROM trainers WHERE id = ? AND isdel = 0"
        cursor = self._get_connection().execute(sql, (trainer_id,))
        row = cursor.fetchone()
        return self._row_to_trainer(row) if row else None


    def get_all_trainers(self) -> List[Trainer]:
        """获取所有训练家"""
        sql = "SELECT * FROM trainers WHERE isdel = 0 ORDER BY id"
        cursor = self._get_connection().execute(sql)
        return [self._row_to_trainer(row) for row in cursor.fetchall()]

    def get_trainer_pokemon_by_trainer_id(self, trainer_id: int) -> List[TrainerPokemon]:
        """获取训练家的所有宝可梦"""
        sql = """
        SELECT tp.*, ps.name_zh as species_name
        FROM trainer_pokemon tp
        LEFT JOIN pokemon_species ps ON tp.pokemon_species_id = ps.id
        WHERE tp.trainer_id = ? AND tp.isdel = 0
        ORDER BY tp.position
        """
        cursor = self._get_connection().execute(sql, (trainer_id,))
        return [self._row_to_trainer_pokemon(row) for row in cursor.fetchall()]

    def get_trainer_encounter_by_id(self, user_id: str, trainer_id: int) -> Optional[TrainerEncounter]:
        """获取特定用户与训练家的遭遇记录"""
        sql = "SELECT * FROM trainer_encounters WHERE user_id = ? AND trainer_id = ?"
        cursor = self._get_connection().execute(sql, (user_id, trainer_id))
        row = cursor.fetchone()
        return self._row_to_trainer_encounter(row) if row else None

    def get_trainers_at_location(self, location_id: int) -> List[TrainerLocation]:
        """获取特定位置的训练家"""
        sql = "SELECT * FROM location_trainers WHERE location_id = ? AND isdel = 0"
        cursor = self._get_connection().execute(sql, (location_id,))
        return [self._row_to_trainer_location(row) for row in cursor.fetchall()]

    def get_trainer_detail(self, trainer_id: int) -> Optional[TrainerDetail]:
        """获取训练家详细信息"""
        trainer = self.get_trainer_by_id(trainer_id)
        if not trainer:
            return None

        pokemon_list = self.get_trainer_pokemon_by_trainer_id(trainer_id)

        # 获取训练家出现的位置
        sql = "SELECT location_id FROM location_trainers WHERE trainer_id = ? AND isdel = 0"
        cursor = self._get_connection().execute(sql, (trainer_id,))
        location_ids = [row[0] for row in cursor.fetchall()]

        return TrainerDetail(trainer=trainer, pokemon_list=pokemon_list, location_ids=location_ids)

    def has_user_fought_trainer(self, user_id: str, trainer_id: int) -> bool:
        """检查用户是否已经与特定训练家战斗过"""
        encounter = self.get_trainer_encounter_by_id(user_id, trainer_id)
        return encounter is not None and encounter.battle_result is not None