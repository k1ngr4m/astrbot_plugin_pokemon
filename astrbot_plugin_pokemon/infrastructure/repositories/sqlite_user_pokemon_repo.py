import sqlite3
import threading
from typing import Optional, List, Any, Dict
from datetime import datetime

# 保持原有导入
from ...core.models.pokemon_models import PokemonIVs, PokemonEVs, PokemonStats, PokemonMoves, WildPokemonEncounterLog
from ...core.models.pokemon_models import UserPokemonInfo
from .abstract_repository import AbstractUserPokemonRepository


class SqliteUserPokemonRepository(AbstractUserPokemonRepository):
    """用户宝可梦数据仓储的SQLite实现"""

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

    # ========= 内部辅助方法 (结构优化) =========

    def _extract_stats(self, row: dict) -> PokemonStats:
        return PokemonStats(
            hp=row['hp'], attack=row['attack'], defense=row['defense'],
            sp_attack=row['sp_attack'], sp_defense=row['sp_defense'], speed=row['speed']
        )

    def _extract_ivs(self, row: dict) -> PokemonIVs:
        return PokemonIVs(
            hp_iv=row['hp_iv'], attack_iv=row['attack_iv'], defense_iv=row['defense_iv'],
            sp_attack_iv=row['sp_attack_iv'], sp_defense_iv=row['sp_defense_iv'], speed_iv=row['speed_iv']
        )

    def _extract_evs(self, row: dict) -> PokemonEVs:
        return PokemonEVs(
            hp_ev=row['hp_ev'], attack_ev=row['attack_ev'], defense_ev=row['defense_ev'],
            sp_attack_ev=row['sp_attack_ev'], sp_defense_ev=row['sp_defense_ev'], speed_ev=row['speed_ev']
        )

    def _extract_moves(self, row: dict) -> PokemonMoves:
        return PokemonMoves(
            move1_id=row['move1_id'], move2_id=row['move2_id'],
            move3_id=row['move3_id'], move4_id=row['move4_id']
        )

    def _row_to_user_pokemon(self, row: sqlite3.Row) -> UserPokemonInfo:
        """代码更加清晰的映射函数"""
        row_dict = dict(row)
        return UserPokemonInfo(
            id=row_dict['id'],
            species_id=row_dict['species_id'],
            name=row_dict['nickname'] or row_dict.get('species_name', 'Unknown'),
            gender=row_dict['gender'],
            level=row_dict['level'],
            exp=row_dict['exp'],
            stats=self._extract_stats(row_dict),
            ivs=self._extract_ivs(row_dict),
            evs=self._extract_evs(row_dict),
            moves=self._extract_moves(row_dict),
            caught_time=row_dict['caught_time'],
            nature_id=row_dict['nature_id'],
        )

    # =========增=========
    def create_user_pokemon(self, user_id: str, pokemon: UserPokemonInfo) -> int:
        """创建用户宝可梦记录 (原子操作)"""
        sql = """
              INSERT INTO user_pokemon (user_id, species_id, nickname, level, exp, gender, \
                                        hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv, \
                                        hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev, \
                                        hp, attack, defense, sp_attack, sp_defense, speed, \
                                        move1_id, move2_id, move3_id, move4_id, nature_id)
              VALUES (:user_id, :species_id, :nickname, :level, :exp, :gender, \
                      :hp_iv, :attack_iv, :defense_iv, :sp_attack_iv, :sp_defense_iv, :speed_iv, \
                      :hp_ev, :attack_ev, :defense_ev, :sp_attack_ev, :sp_defense_ev, :speed_ev, \
                      :hp, :attack, :defense, :sp_attack, :sp_defense, :speed, \
                      :move1_id, :move2_id, :move3_id, :move4_id, :nature_id) \
              """

        # 展平参数字典，使用命名占位符防止位置错误
        params = {
            "user_id": user_id, "species_id": pokemon.species_id, "nickname": pokemon.name,
            "level": pokemon.level, "exp": pokemon.exp, "gender": pokemon.gender,
            "nature_id": pokemon.nature_id,  # 占位符，稍后更新
            # IVs
            "hp_iv": pokemon.ivs.hp_iv, "attack_iv": pokemon.ivs.attack_iv, "defense_iv": pokemon.ivs.defense_iv,
            "sp_attack_iv": pokemon.ivs.sp_attack_iv, "sp_defense_iv": pokemon.ivs.sp_defense_iv,
            "speed_iv": pokemon.ivs.speed_iv,
            # EVs
            "hp_ev": pokemon.evs.hp_ev, "attack_ev": pokemon.evs.attack_ev, "defense_ev": pokemon.evs.defense_ev,
            "sp_attack_ev": pokemon.evs.sp_attack_ev, "sp_defense_ev": pokemon.evs.sp_defense_ev,
            "speed_ev": pokemon.evs.speed_ev,
            # Stats
            "hp": pokemon.stats.hp, "attack": pokemon.stats.attack, "defense": pokemon.stats.defense,
            "sp_attack": pokemon.stats.sp_attack, "sp_defense": pokemon.stats.sp_defense, "speed": pokemon.stats.speed,
            # Moves
            "move1_id": pokemon.moves.move1_id, "move2_id": pokemon.moves.move2_id,
            "move3_id": pokemon.moves.move3_id, "move4_id": pokemon.moves.move4_id,
        }

        conn = self._get_connection()
        with conn:  # 开启事务
            cursor = conn.cursor()
            cursor.execute(sql, params)
            new_id = cursor.lastrowid

        return new_id

    def add_user_encountered_wild_pokemon(self, user_id: str, wild_pokemon_id: int, location_id: int,
                                          encounter_rate: float) -> None:
        """添加野生宝可梦遇到记录"""
        conn = self._get_connection()
        with conn:
            conn.execute("""
                         INSERT INTO wild_pokemon_encounter_log
                             (user_id, wild_pokemon_id, location_id, encounter_time, encounter_rate)
                         VALUES (?, ?, ?, ?, ?)
                         """, (user_id, wild_pokemon_id, location_id, datetime.now(), encounter_rate))

    # =========改=========
    def update_encounter_log(self, log_id: int, is_captured: int = None,
                             is_battled: int = None, battle_result: str = None, isdel: int = None) -> None:
        """更新野生宝可梦遇到记录"""
        updates = []
        params = []

        if is_captured is not None:
            updates.append("is_captured = ?")
            params.append(is_captured)
        if is_battled is not None:
            updates.append("is_battled = ?")
            params.append(is_battled)
        if battle_result is not None:
            updates.append("battle_result = ?")
            params.append(battle_result)
        if isdel is not None:
            updates.append("isdel = ?")
            params.append(isdel)

        if not updates:
            return

        # 只要有状态更新，默认将记录标记为已处理(isdel=1)并更新时间
        # 除非显式传入了isdel参数（虽然当前逻辑似乎会覆盖显式传入的isdel，保持原逻辑行为，但做去重处理）
        if "isdel = ?" not in updates:
            updates.append("isdel = ?")
            params.append(1)

        updates.append("updated_at = datetime('now', '+8 hours')")
        params.append(log_id)

        conn = self._get_connection()
        with conn:
            sql = f"UPDATE wild_pokemon_encounter_log SET {', '.join(updates)} WHERE id = ?"
            conn.execute(sql, params)

    def _update_user_pokemon_fields(self, user_id: str, pokemon_id: int, **kwargs) -> None:
        """
        通用更新函数：动态更新 user_pokemon 表的指定字段
        """
        if not kwargs:
            return

        # 1. 动态构建 SET 子句 (例如: "level = :level, exp = :exp")
        set_clauses = [f"{key} = :{key}" for key in kwargs.keys()]

        # 2. 总是更新 updated_at
        set_clauses.append("updated_at = datetime('now', '+8 hours')")

        sql = f"""
            UPDATE user_pokemon
            SET {', '.join(set_clauses)}
            WHERE id = :id AND user_id = :user_id
        """

        # 3. 准备参数字典
        params = kwargs.copy()
        params['id'] = pokemon_id
        params['user_id'] = user_id

        # 4. 执行
        conn = self._get_connection()
        with conn:
            conn.execute(sql, params)

    # =========查=========
    def get_user_pokemon(self, user_id: str) -> List[UserPokemonInfo]:
        sql = """
              SELECT up.*, ps.name_zh as species_name, ps.name_en as species_en_name
              FROM user_pokemon up
                       JOIN pokemon_species ps ON up.species_id = ps.id
              WHERE up.user_id = ?
              ORDER BY up.id \
              """
        cursor = self._get_connection().execute(sql, (user_id,))
        return [self._row_to_user_pokemon(row) for row in cursor.fetchall()]

    def get_user_pokemon_by_id(self, user_id: str, pokemon_id: int) -> Optional[UserPokemonInfo]:
        sql = """
              SELECT up.*, ps.name_zh as species_name, ps.name_en as species_en_name
              FROM user_pokemon up
                       JOIN pokemon_species ps ON up.species_id = ps.id
              WHERE up.id = ? \
                AND up.user_id = ? \
              """
        cursor = self._get_connection().execute(sql, (pokemon_id, user_id))
        row = cursor.fetchone()
        return self._row_to_user_pokemon(row) if row else None

    def get_user_pokedex_ids(self, user_id: str) -> dict[str, Any]:
        """优化：使用 UNION 一次性查询"""
        conn = self._get_connection()

        # 1. 仅仅查询已捕捉的 IDs
        cursor = conn.execute("SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = ? AND isdel = 0",
                              (user_id,))
        caught_ids = {row[0] for row in cursor.fetchall()}

        # 2. 查询“遇到过”的 IDs (包含已捕捉的和在野外遇到的)
        # SQL逻辑：(用户拥有的) UNION (遇到记录关联的野怪种族)
        sql_seen = """
                   SELECT species_id \
                   FROM user_pokemon \
                   WHERE user_id = ?
                   UNION
                   SELECT w.species_id
                   FROM wild_pokemon_encounter_log log
                            JOIN wild_pokemon w ON log.wild_pokemon_id = w.id
                   WHERE log.user_id = ? \
                     AND w.isdel = 0 \
                   """
        cursor = conn.execute(sql_seen, (user_id, user_id))
        seen_ids = {row[0] for row in cursor.fetchall()}

        return {"caught": caught_ids, "seen": seen_ids}

    def get_user_encountered_wild_pokemon(self, user_id: str) -> Optional[WildPokemonEncounterLog]:
        conn = self._get_connection()
        cursor = conn.execute("""
                              SELECT *
                              FROM wild_pokemon_encounter_log
                              WHERE user_id = ?
                                AND isdel = 0
                              ORDER BY encounter_time DESC
                              LIMIT 1
                              """, (user_id,))
        row = cursor.fetchone()
        return WildPokemonEncounterLog(**dict(row)) if row else None

    def get_user_encounters(self, user_id: str, limit: int = 50, offset: int = 0) -> List[WildPokemonEncounterLog]:
        conn = self._get_connection()
        cursor = conn.execute("""
                              SELECT *
                              FROM wild_pokemon_encounter_log
                              WHERE user_id = ?
                              ORDER BY encounter_time DESC
                              LIMIT ? OFFSET ?
                              """, (user_id, limit, offset))
        return [WildPokemonEncounterLog(**dict(row)) for row in cursor.fetchall()]

    def get_latest_encounters(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("""
                              SELECT *
                              FROM wild_pokemon_encounter_log
                              WHERE user_id = ?
                              ORDER BY encounter_time DESC
                              LIMIT ?
                              """, (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]