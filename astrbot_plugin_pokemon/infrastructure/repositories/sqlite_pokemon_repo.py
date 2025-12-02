import sqlite3
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

# 导入抽象基类和领域模型
from .abstract_repository import AbstractPokemonRepository
from ...core.models.pokemon_models import PokemonSpecies, PokemonBaseStats, PokemonDetail, WildPokemonInfo, \
    WildPokemonEncounterLog, PokemonIVs, PokemonEVs, PokemonStats, PokemonMoves, PokemonEvolutionInfo


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

        # 构造 PokemonMoves 对象
        moves = PokemonMoves(
            move1_id=row_dict['move1_id'],
            move2_id=row_dict['move2_id'],
            move3_id=row_dict['move3_id'],
            move4_id=row_dict['move4_id']
        )

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
            moves=moves
        )

    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[PokemonSpecies]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pokemon_species WHERE id = ?", (pokemon_id,))
            return self._row_to_pokemon(cursor.fetchone())

    def get_all_pokemon(self) -> List[PokemonSpecies]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pokemon_species WHERE isdel = 0 ORDER BY id ASC")
            return [self._row_to_pokemon(row) for row in cursor.fetchall()]

    def get_all_pokemon_simple(self) -> List[PokemonSpecies]:
        """只获取 ID 和名称，用于图鉴等需要减少数据量的场景"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name_zh, name_en FROM pokemon_species WHERE isdel = 0 ORDER BY id ASC")
            rows = cursor.fetchall()
            result = []
            for row in rows:
                # 创建一个简化的 PokemonSpecies 对象，只包含 ID 和名称
                simple_species = PokemonSpecies(
                    id=row['id'],
                    name_zh=row['name_zh'],
                    name_en=row['name_en'],
                    generation_id=0,  # 简化对象，设置为0
                    base_stats=PokemonBaseStats(
                        base_hp=0,
                        base_attack=0,
                        base_defense=0,
                        base_sp_attack=0,
                        base_sp_defense=0,
                        base_speed=0
                    ),
                    height=0.0,
                    weight=0.0,
                    description=""
                )
                result.append(simple_species)
            return result

    def get_pokemon_by_name(self, name: str) -> Optional[PokemonSpecies]:
        """根据名称查找宝可梦，用于图鉴等功能"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pokemon_species
                WHERE (name_zh = ? OR name_en = ?) AND isdel = 0
            """, (name, name))
            row = cursor.fetchone()
            return self._row_to_pokemon(row)

    def get_pokemon_name_by_id(self, pokemon_id: int) -> Optional[str]:
        """根据ID获取宝可梦中文名，用于图鉴等功能"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name_zh FROM pokemon_species WHERE id = ? AND isdel = 0", (pokemon_id,))
            row = cursor.fetchone()
            return row['name_zh'] if row else None

    def add_pokemon_template(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pokemon_species
                (id, name_en, name_zh, generation_id, base_hp, base_attack,
                 base_defense, base_sp_attack, base_sp_defense, base_speed,
                height, weight, base_experience, gender_rate, capture_rate,
                 growth_rate_id, description, orders, effort)
                VALUES (:id, :name_en, :name_zh, :generation_id, :base_hp,
                        :base_attack, :base_defense, :base_sp_attack,
                        :base_sp_defense, :base_speed, :height, :weight,
                        :base_experience, :gender_rate, :capture_rate,
                        :growth_rate_id, :description, :orders, :effort)
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

    def get_pokemon_types(self, species_id: int) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.name_zh FROM pokemon_types t
                JOIN pokemon_species_types st ON t.id = st.type_id
                WHERE st.species_id = ?
            """, (species_id,))
            return [row[0] for row in cursor.fetchall()]

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

            moves: PokemonMoves = pokemon.moves
            move1_id = moves.move1_id
            move2_id = moves.move2_id
            move3_id = moves.move3_id
            move4_id = moves.move4_id

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

    def get_pokemon_capture_rate(self, pokemon_id: int) -> int:
        """获取宝可梦的捕捉率"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT capture_rate FROM pokemon_species
                WHERE id = ?
            """, (pokemon_id,))
            row = cursor.fetchone()
            return row['capture_rate'] if row else 0

    # 新增批量插入方法
    def add_pokemon_templates_batch(self, data_list: List[Dict[str, Any]]) -> None:
        if not data_list:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 使用 executemany 进行批量插入
            cursor.executemany("""
                               INSERT OR IGNORE INTO pokemon_species
                               (id, name_en, name_zh, generation_id, base_hp, base_attack,
                                base_defense, base_sp_attack, base_sp_defense, base_speed,
                                height, weight, base_experience, gender_rate, capture_rate,
                                growth_rate_id, description, orders, effort)
                               VALUES (:id, :name_en, :name_zh, :generation_id, :base_hp,
                                       :base_attack, :base_defense, :base_sp_attack,
                                       :base_sp_defense, :base_speed, :height, :weight,
                                       :base_experience, :gender_rate, :capture_rate,
                                       :growth_rate_id, :description, :orders, :effort)
                               """, data_list)
            conn.commit()

    # 同理，可以为 evolution, type 等添加 batch 方法
    def add_pokemon_evolutions_batch(self, data_list: List[Dict[str, Any]]) -> None:
        if not data_list:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                               INSERT OR IGNORE INTO pokemon_evolutions
                               (pre_species_id, evolved_species_id, evolution_trigger_id, trigger_item_id,
                                minimum_level, gender_id, held_item_id, time_of_day, known_move_id,
                                minimum_happiness, minimum_beauty, minimum_affection,
                                relative_physical_stats, party_species_id, trade_species_id,
                                needs_overworld_rain)
                               VALUES (:pre_species_id, :evolved_species_id, :evolution_trigger_id,
                                       :trigger_item_id,
                                       :minimum_level, :gender_id, :held_item_id, :time_of_day, :known_move_id,
                                       :minimum_happiness, :minimum_beauty, :minimum_affection,
                                       :relative_physical_stats, :party_species_id, :trade_species_id,
                                       :needs_overworld_rain)
                               """, data_list)
            conn.commit()

    def get_pokemon_evolutions(self, species_id: int, new_level: int) -> list[PokemonEvolutionInfo]:
        """
        获取指定物种的进化信息
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(                """
                SELECT * FROM pokemon_evolutions
                WHERE pre_species_id = ? AND minimum_level <= ? AND isdel = 0
                """, (species_id, new_level))
            rows = cursor.fetchall()
            return [PokemonEvolutionInfo(**dict(row)) for row in rows]
