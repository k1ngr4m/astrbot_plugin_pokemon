import sqlite3
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

from data.plugins.astrbot_plugin_pokemon.core.domain.pokemon_models import WildPokemonInfo
# 导入抽象基类和领域模型
from .abstract_repository import AbstractPokemonRepository
from ..domain.adventure_models import LocationInfo
from ..domain.pokemon_models import PokemonSpecies, PokemonBaseStats, PokemonDetail, WildPokemonInfo, \
    WildPokemonEncounterLog, PokemonIVs, PokemonEVs, PokemonStats


class SqlitePokemonRepository(AbstractPokemonRepository):
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

    def _row_to_pokemon(self, row: sqlite3.Row) -> Optional[PokemonSpecies]:
        if not row:
            return None

        # 将数据库字段转换为PokemonTemplate所需的格式
        row_dict = dict(row)
        row_dict.pop('created_at', None)
        row_dict.pop('updated_at', None)
        row_dict.pop('isdel', None)
        # 从字典中提取基础属性值并创建PokemonBaseStats对象
        base_stats = PokemonBaseStats(
            base_hp=row_dict.pop('base_hp'),
            base_attack=row_dict.pop('base_attack'),
            base_defense=row_dict.pop('base_defense'),
            base_sp_attack=row_dict.pop('base_sp_attack'),
            base_sp_defense=row_dict.pop('base_sp_defense'),
            base_speed=row_dict.pop('base_speed')
        )

        # 使用剩余的字段创建PokemonTemplate对象
        return PokemonSpecies(
            base_stats=base_stats,
            **row_dict
        )

    def _row_to_wild_pokemon(self, row: sqlite3.Row) -> WildPokemonInfo | None:
        if not row:
            return None

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
        row_dict = dict(row)

        row_dict.pop('created_at', None)
        row_dict.pop('updated_at', None)
        row_dict.pop('isdel', None)

        return WildPokemonInfo(
            id=row_dict['id'],
            species_id=row_dict['species_id'],
            name=row_dict['name'],
            gender=row_dict['gender'],
            level=row_dict['level'],
            exp=row_dict['exp'],
            stats=stats,
            ivs=ivs,
            evs=evs,
            moves=None
        )

    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[PokemonSpecies]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pokemon_species WHERE id = ?", (pokemon_id,))
            return self._row_to_pokemon(cursor.fetchone())

    def get_all_pokemon(self) -> List[PokemonSpecies]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pokemon_species ORDER BY id DESC")
            return [self._row_to_pokemon(row) for row in cursor.fetchall()]

    def add_pokemon_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_species
                (id, name_en, name_zh, generation_id, base_hp, base_attack,
                 base_defense, base_sp_attack, base_sp_defense, base_speed,
                height, weight, base_experience, gender_rate, capture_rate, 
                 growth_rate_id, description, orders)
                VALUES (:id, :name_en, :name_zh, :generation_id, :base_hp,
                        :base_attack, :base_defense, :base_sp_attack,
                        :base_sp_defense, :base_speed, :height, :weight,
                        :base_experience, :gender_rate, :capture_rate, 
                        :growth_rate_id, :description, :orders)
            """, {**data})
            conn.commit()

    def add_pokemon_type_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_types
                (name_en, name_zh)
                VALUES (:name_en, :name_zh)
            """, {
                'name_en': data.get('name_en', data.get('name', '')),
                'name_zh': data.get('name_zh', data.get('name', ''))
            })
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
                (pre_species_id, evolved_species_id, evolution_trigger_id, trigger_item_id,
                 minimum_level, gender_id, held_item_id, time_of_day, known_move_id,
                 minimum_happiness, minimum_beauty, minimum_affection,
                 relative_physical_stats, party_species_id, trade_species_id,
                 needs_overworld_rain)
                VALUES (:pre_species_id, :evolved_species_id, :evolution_trigger_id, :trigger_item_id,
                        :minimum_level, :gender_id, :held_item_id, :time_of_day, :known_move_id,
                        :minimum_happiness, :minimum_beauty, :minimum_affection,
                        :relative_physical_stats, :party_species_id, :trade_species_id,
                        :needs_overworld_rain)
            """, {
                'pre_species_id': data.get('from_species_id', data.get('pre_species_id')),
                'evolved_species_id': data.get('to_species_id', data.get('evolved_species_id')),
                'evolution_trigger_id': data.get('evolution_trigger_id', data.get('method', 0)),
                'trigger_item_id': data.get('trigger_item_id', data.get('condition_value', 0)),
                'minimum_level': data.get('minimum_level', data.get('level', 0)),
                'gender_id': data.get('gender_id', 0),
                'location_id': data.get('location_id', 0),
                'held_item_id': data.get('held_item_id', 0),
                'time_of_day': data.get('time_of_day', ''),
                'known_move_id': data.get('known_move_id', 0),
                'known_move_type_id': data.get('known_move_type_id', 0),
                'minimum_happiness': data.get('minimum_happiness', 0),
                'minimum_beauty': data.get('minimum_beauty', 0),
                'minimum_affection': data.get('minimum_affection', 0),
                'relative_physical_stats': data.get('relative_physical_stats', 0),
                'party_species_id': data.get('party_species_id', 0),
                'party_type_id': data.get('party_type_id', 0),
                'trade_species_id': data.get('trade_species_id', 0),
                'needs_overworld_rain': data.get('needs_overworld_rain', 0),
                'turn_upside_down': data.get('turn_upside_down', 0),
                'region_id': data.get('region_id', 0),
                'base_form_id': data.get('base_form_id', 0)
            })
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

    def get_pokemon_types(self, species_id: int) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.name_zh FROM pokemon_types t
                JOIN pokemon_species_types st ON t.id = st.type_id
                WHERE st.species_id = ?
            """, (species_id,))
            return [row[0] for row in cursor.fetchall()]

    def update_pokemon_exp(self, level: int, exp: int, pokemon_id: int, user_id: str) -> None:
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

    def get_user_pokemon_encounter_count(self, user_id: str, wild_pokemon_id: int) -> int:
        """获取用户遇到的某个特定物种的次数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM wild_pokemon_encounter_log
                WHERE user_id = ? AND wild_pokemon_id = ?
            """, (user_id, wild_pokemon_id))
            row = cursor.fetchone()
            return row['count'] if row else 0

    def get_user_total_encounters(self, user_id: str) -> int:
        """统计用户的总遇到次数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM wild_pokemon_encounter_log
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return row['count'] if row else 0

    def get_latest_encounters(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最新的遇到记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wild_pokemon_encounter_log
                ORDER BY encounter_time DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_user_encountered_wild_pokemon(self, user_id: str) -> Optional[WildPokemonEncounterLog]:
        """
        获取用户当前遇到的野生宝可梦
        Args:
            user_id (str): 用户ID
        Returns:
            Optional[PokemonDetail]: 野生宝可梦的详细信息，如果不存在则返回None
        """
        import json
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

    def get_base_exp(self, pokemon_id: int) -> int:
        """获取宝可梦的基础经验值"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT base_experience FROM pokemon_species
                WHERE id = ?
            """, (pokemon_id,))
            row = cursor.fetchone()
            return row['base_experience'] if row else 0

    def get_wild_pokemon_by_id(self, wild_pokemon_id: int) -> Optional[Dict[str, Any]]:
        """根据野生宝可梦ID获取野生宝可梦信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wild_pokemon
                WHERE id = ? AND isdel = 0
            """, (wild_pokemon_id,))
            row = cursor.fetchone()
            return self._row_to_wild_pokemon(row) if row else None

    def add_wild_pokemon(self, pokemon: WildPokemonInfo) -> int:
        """添加野生宝可梦"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = """
            INSERT INTO wild_pokemon (
                species_id, name, level, exp, gender,
                hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv,
                hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev,
                hp, attack, defense, sp_attack, sp_defense, speed,
                move1_id, move2_id, move3_id, move4_id
            )
            VALUES (?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?
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

            move1_id = None
            move2_id = None
            move3_id = None
            move4_id = None

            cursor.execute(sql, (
                species_id, nickname, level, exp, gender,
                hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv,
                hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev,
                hp, attack, defense, sp_attack, sp_defense, speed,
                move1_id, move2_id, move3_id, move4_id
            ))
            new_id = cursor.lastrowid
            conn.commit()
            return new_id