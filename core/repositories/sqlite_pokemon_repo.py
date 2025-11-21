import sqlite3
import threading
from typing import Optional, List, Dict, Any

# 导入抽象基类和领域模型
from .abstract_repository import AbstractPokemonRepository
from ..domain.adventure_models import AreaInfo
from ..domain.pokemon_models import PokemonTemplate, PokemonBaseStats, PokemonDetail, WildPokemonInfo, \
    WildPokemonEncounterLog


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

    def _row_to_pokemon(self, row: sqlite3.Row) -> Optional[PokemonTemplate]:
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
        return PokemonTemplate(
            base_stats=base_stats,
            **row_dict
        )

    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[PokemonTemplate]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pokemon_species WHERE id = ?", (pokemon_id,))
            return self._row_to_pokemon(cursor.fetchone())

    def get_all_pokemon(self) -> List[PokemonTemplate]:
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

    def get_pokemon_types(self, species_id: int) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.name FROM pokemon_types t
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
                SET current_hp = :current_hp, attack = :attack, defense = :defense, sp_attack = :sp_attack, sp_defense = :sp_defense, speed = :speed
                WHERE id = :id AND user_id = :user_id
            """, {**attributes, 'id': pokemon_id, 'user_id': user_id})
            conn.commit()

    def add_user_encountered_wild_pokemon(self, user_id: str, wild_pokemon: WildPokemonInfo, area_info: AreaInfo, encounter_rate: float) -> None:
        """添加野生宝可梦遇到记录"""
        pokemon_species_id = wild_pokemon.species_id
        pokemon_name = wild_pokemon.name
        area_code = area_info.area_code
        area_name = area_info.area_name
        pokemon_level = wild_pokemon.level
        encounter_rate = encounter_rate
        import json
        pokemon_info = json.dumps(wild_pokemon.model_dump_json(), ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO wild_pokemon_encounter_log
                (user_id, pokemon_species_id, pokemon_name, pokemon_level, pokemon_info, 
                 area_code, area_name, encounter_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, pokemon_species_id, pokemon_name, pokemon_level, pokemon_info,
                area_code, area_name, encounter_rate
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

    def get_user_encounters(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
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
            return [dict(row) for row in rows]

    def get_user_pokemon_encounter_count(self, user_id: str, pokemon_species_id: int) -> int:
        """获取用户遇到的某个特定物种的次数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM wild_pokemon_encounter_log
                WHERE user_id = ? AND pokemon_species_id = ?
            """, (user_id, pokemon_species_id))
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
            if row is None:
                return None

            row_dict = dict(row)
            # 反序列化pokemon_info JSON字符串
            if row_dict.get('pokemon_info'):
                try:
                    pokemon_info_data = json.loads(row_dict['pokemon_info'])
                    # 从字典创建WildPokemonInfo对象
                    from ..domain.pokemon_models import PokemonStats, PokemonIVs, PokemonEVs
                    pokemon_info_obj = WildPokemonInfo(
                        species_id=pokemon_info_data['species_id'],
                        name=pokemon_info_data['name'],
                        gender=pokemon_info_data['gender'],
                        level=pokemon_info_data['level'],
                        exp=pokemon_info_data['exp'],
                        stats=PokemonStats(**pokemon_info_data['stats']),
                        ivs=PokemonIVs(**pokemon_info_data['ivs']),
                        evs=PokemonEVs(**pokemon_info_data['evs']),
                        moves=pokemon_info_data['moves']
                    )
                    row_dict['pokemon_info'] = pokemon_info_obj
                except (json.JSONDecodeError, KeyError):
                    # 如果解析失败，保持原始值
                    pass
            # 移除数据库字段
            row_dict.pop('created_at', None)
            row_dict.pop('updated_at', None)
            row_dict.pop('isdel', None)
            return WildPokemonEncounterLog(**row_dict)
