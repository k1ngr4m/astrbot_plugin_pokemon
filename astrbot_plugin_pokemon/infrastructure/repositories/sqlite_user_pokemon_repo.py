import sqlite3
import threading
import dataclasses
from typing import Optional, List, Any, Dict
from datetime import datetime

from ...core.models.pokemon_models import PokemonIVs, PokemonEVs, PokemonStats, PokemonMoves, WildPokemonEncounterLog
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
            nature_id=row_dict['nature_id'],
        )


    # =========增=========
    def create_user_pokemon(self, user_id: str, pokemon: UserPokemonInfo) -> int:
        """
        创建用户宝可梦记录，使用模板数据完善实例
        Args:
            user_id: 用户ID
            species_id: 宝可梦种族ID
            nickname: 宝可梦昵称（可选）
        Returns:
            新创建的宝可梦实例ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = """
            INSERT INTO user_pokemon (
                user_id, species_id, nickname, level, exp, gender,
                hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv,
                hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev,
                hp, attack, defense, sp_attack, sp_defense, speed,
                move1_id, move2_id, move3_id, move4_id, shortcode, nature_id
            )
            VALUES (?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """

            species_id = pokemon.species_id
            nickname = pokemon.name
            level = pokemon.level
            exp = pokemon.exp
            gender = pokemon.gender

            ivs: PokemonIVs = pokemon.ivs
            hp_iv = ivs.hp_iv
            attack_iv = ivs.attack_iv
            defense_iv = ivs.defense_iv
            sp_attack_iv = ivs.sp_attack_iv
            sp_defense_iv = ivs.sp_defense_iv
            speed_iv = ivs.speed_iv

            evs: PokemonEVs = pokemon.evs
            hp_ev = evs.hp_ev
            attack_ev = evs.attack_ev
            defense_ev = evs.defense_ev
            sp_attack_ev = evs.sp_attack_ev
            sp_defense_ev = evs.sp_defense_ev
            speed_ev = evs.speed_ev

            stats: PokemonStats = pokemon.stats
            hp = stats.hp
            attack = stats.attack
            defense = stats.defense
            sp_attack = stats.sp_attack
            sp_defense = stats.sp_defense
            speed = stats.speed

            moves: PokemonMoves = pokemon.moves
            move1_id = moves.move1_id
            move2_id = moves.move2_id
            move3_id = moves.move3_id
            move4_id = moves.move4_id
            nature_id = pokemon.nature_id
            # 获取新记录的ID（先插入然后获取ID用于生成短码）
            cursor.execute(sql, (
                user_id, species_id, nickname, level, exp, gender,
                hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv,
                hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev,
                hp, attack, defense, sp_attack, sp_defense, speed,
                move1_id, move2_id, move3_id, move4_id, f"P{0:04d}", nature_id
            ))
            new_id = cursor.lastrowid
            conn.commit()

            # 更新记录的shortcode字段
            shortcode = f"P{new_id:04d}"
            update_shortcode_sql = "UPDATE user_pokemon SET shortcode = ? WHERE id = ?"
            cursor.execute(update_shortcode_sql, (shortcode, new_id))
            conn.commit()

        return new_id

    def add_user_encountered_wild_pokemon(self, user_id: str, wild_pokemon_id: int, location_id: int, encounter_rate: float) -> None:
        """添加野生宝可梦遇到记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO wild_pokemon_encounter_log
                (user_id, wild_pokemon_id, location_id, encounter_time,
                 encounter_rate)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id, wild_pokemon_id, location_id, datetime.now(),
                encounter_rate
            ))
            conn.commit()

    # =========改=========
    def update_user_pokemon_exp(self, level: int, exp: int, pokemon_id: int, user_id: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_pokemon
                SET level = ?, exp = ?
                WHERE id = ? AND user_id = ?
            """, (level, exp, pokemon_id, user_id))
            conn.commit()

    def update_pokemon_attributes(self, attributes: Dict[str, int], pokemon_id: int, user_id: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_pokemon
                SET hp = :hp, attack = :attack, defense = :defense, sp_attack = :sp_attack, sp_defense = :sp_defense, speed = :speed
                WHERE id = :id AND user_id = :user_id
            """, {**attributes, 'id': pokemon_id, 'user_id': user_id})
            conn.commit()

    def update_encounter_log(self, log_id: int, is_captured: int = None,
                            is_battled: int = None, battle_result: str = None, isdel: int = None) -> None:
        """更新野生宝可梦遇到记录（如捕捉或战斗结果）"""
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
            return  # 没有需要更新的字段
        else:
            updates.append("isdel = ?")
            params.append(1)

        params.append(log_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = f"UPDATE wild_pokemon_encounter_log SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            conn.commit()

    def update_pokemon_moves(self, moves: PokemonMoves, pokemon_id: int, user_id: str) -> None:
        """更新宝可梦的技能"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_pokemon
                SET move1_id = ?, move2_id = ?, move3_id = ?, move4_id = ?
                WHERE id = ? AND user_id = ?
            """, (
                moves.move1_id, moves.move2_id, moves.move3_id, moves.move4_id,
                pokemon_id, user_id
            ))
            conn.commit()

    def update_user_pokemon_after_evolution(self, user_id: str, pokemon_id: int, pokemon_info: UserPokemonInfo) -> None:
        """更新用户宝可梦"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_pokemon
                SET species_id = ?, nickname = ?,
                    hp = ?, attack = ?, defense = ?, sp_attack = ?, sp_defense = ?, speed = ?
                WHERE id = ? AND user_id = ?
            """, (
                pokemon_info.species_id, pokemon_info.name,
                pokemon_info.stats.hp, pokemon_info.stats.attack, pokemon_info.stats.defense,
                pokemon_info.stats.sp_attack, pokemon_info.stats.sp_defense, pokemon_info.stats.speed,
                pokemon_id, user_id
            ))
            conn.commit()

    def update_user_pokemon_ev(self, ev: Dict[str, int], pokemon_id: int, user_id: str) -> None:
        """更新用户宝可梦ev值"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_pokemon
                SET hp_ev = ?, attack_ev = ?, defense_ev = ?, sp_attack_ev = ?, sp_defense_ev = ?, speed_ev = ?
                WHERE id = ? AND user_id = ?
            """, (
                ev['hp_ev'], ev['attack_ev'], ev['defense_ev'], ev['sp_attack_ev'], ev['sp_defense_ev'], ev['speed_ev'],
                pokemon_id, user_id
            ))
            conn.commit()

    # =========查=========
    def get_user_pokemon(self, user_id: str) -> List[UserPokemonInfo]:
        """
        获取用户的所有宝可梦
        Args:
            user_id: 用户ID
        Returns:
            用户宝可梦列表
        """
        sql = """
        SELECT up.*, ps.name_zh as species_name, ps.name_en as species_en_name
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
                result.append(self._row_to_user_pokemon(row))
            return result

    def get_user_pokemon_by_id(self, user_id: str, pokemon_id: int) -> Optional[UserPokemonInfo]:
        """
        通过ID获取用户的宝可梦实例
        Args:
            pokemon_id: 宝可梦实例ID
        Returns:
            宝可梦实例信息（如果存在）
        """
        sql = """
        SELECT up.*, ps.name_zh as species_name, ps.name_en as species_en_name
        FROM user_pokemon up
        JOIN pokemon_species ps ON up.species_id = ps.id
        WHERE up.id = ? AND up.user_id = ?
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (pokemon_id, user_id))
            row = cursor.fetchone()
            return self._row_to_user_pokemon(row) if row else None

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
                WHERE log.user_id = ? AND w.isdel = 0
            """, (user_id,))
            seen_ids = {row[0] for row in cursor.fetchall()}

            # 这里的seen应该包含caught (捕捉了肯定算遇见了)
            seen_ids.update(caught_ids)

            return {
                "caught": caught_ids,
                "seen": seen_ids
            }

    def get_user_encountered_wild_pokemon(self, user_id: str) -> Optional[WildPokemonEncounterLog]:
        """
        获取用户当前遇到的野生宝可梦
        Args:
            user_id (str): 用户ID
        Returns:
            Optional[PokemonDetail]: 野生宝可梦的详细信息，如果不存在则返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wild_pokemon_encounter_log
                WHERE user_id = ? AND isdel = 0
                ORDER BY encounter_time DESC
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            return WildPokemonEncounterLog(**dict(row)) if row else None

    def get_user_encounters(self, user_id: str, limit: int = 50, offset: int = 0) -> List[WildPokemonEncounterLog]:
        """获取用户遇到的所有野生宝可梦记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wild_pokemon_encounter_log
                WHERE user_id = ?
                ORDER BY encounter_time DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
            rows = cursor.fetchall()
            return [WildPokemonEncounterLog(**dict(row)) for row in rows]

    def get_latest_encounters(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最新的遇到记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wild_pokemon_encounter_log
                WHERE user_id = ?
                ORDER BY encounter_time DESC
                LIMIT ?
            """, (user_id, limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]