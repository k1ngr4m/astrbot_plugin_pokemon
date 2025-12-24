import sqlite3
import threading
from typing import Optional, List, Any, Dict
from datetime import datetime

from .sqlite_move_repo import SqliteMoveRepository
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
            happiness=row_dict.get('happiness', 70),
            current_hp=row_dict.get('current_hp', 0),
            current_pp1=row_dict.get('current_pp1', 0),
            current_pp2=row_dict.get('current_pp2', 0),
            current_pp3=row_dict.get('current_pp3', 0),
            current_pp4=row_dict.get('current_pp4', 0),
            ability_id=row_dict.get('ability_id', 0),
            held_item_id=row_dict.get('held_item_id', 0),
            is_favorite=row_dict.get('is_favorite', 0),
        )

    # =========增=========
    def create_user_pokemon(self, user_id: str, pokemon: UserPokemonInfo) -> int:
        """创建用户宝可梦记录 (原子操作)"""
        sql = """
              INSERT INTO user_pokemon (user_id, species_id, nickname, level, exp, gender, \
                                        hp_iv, attack_iv, defense_iv, sp_attack_iv, sp_defense_iv, speed_iv, \
                                        hp_ev, attack_ev, defense_ev, sp_attack_ev, sp_defense_ev, speed_ev, \
                                        hp, attack, defense, sp_attack, sp_defense, speed, \
                                        move1_id, move2_id, move3_id, move4_id, nature_id, \
                                        happiness, current_hp, current_pp1, current_pp2, current_pp3, current_pp4, ability_id, held_item_id)
              VALUES (:user_id, :species_id, :nickname, :level, :exp, :gender, \
                      :hp_iv, :attack_iv, :defense_iv, :sp_attack_iv, :sp_defense_iv, :speed_iv, \
                      :hp_ev, :attack_ev, :defense_ev, :sp_attack_ev, :sp_defense_ev, :speed_ev, \
                      :hp, :attack, :defense, :sp_attack, :sp_defense, :speed, \
                      :move1_id, :move2_id, :move3_id, :move4_id, :nature_id, \
                      :happiness, :current_hp, :current_pp1, :current_pp2, :current_pp3, :current_pp4, :ability_id, :held_item_id) \
              """

        # 展平参数字典，使用命名占位符防止位置错误
        params = {
            "user_id": user_id, "species_id": pokemon.species_id, "nickname": pokemon.name,
            "level": pokemon.level, "exp": pokemon.exp, "gender": pokemon.gender,
            "nature_id": pokemon.nature_id,
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
            # 新增字段
            "happiness": pokemon.happiness,
            "current_hp": pokemon.stats.hp,  # 刚捕捉的宝可梦HP满
            "current_pp1": 0,  # PP会在创建后根据技能自动设置
            "current_pp2": 0,
            "current_pp3": 0,
            "current_pp4": 0,
            "ability_id": pokemon.ability_id,
            "held_item_id": pokemon.held_item_id,
        }

        # 在插入记录后，更新PP为技能的最大PP值
        conn = self._get_connection()
        with conn:  # 开启事务
            cursor = conn.cursor()
            cursor.execute(sql, params)
            new_id = cursor.lastrowid

            # 获取技能的最大PP值并更新current_pp字段
            moves = [pokemon.moves.move1_id, pokemon.moves.move2_id,
                     pokemon.moves.move3_id, pokemon.moves.move4_id]

            temp_repo = SqliteMoveRepository(self.db_path)
            current_pps = []
            for move_id in moves:
                if move_id:
                    move_info = temp_repo.get_move_by_id(move_id)
                    max_pp = move_info['pp'] if move_info else 0
                    current_pps.append(max_pp)
                else:
                    current_pps.append(0)

            # 更新PP值
            update_pp_sql = """
                UPDATE user_pokemon
                SET current_pp1 = ?, current_pp2 = ?, current_pp3 = ?, current_pp4 = ?,
                    updated_at = datetime('now', '+8 hours')
                WHERE id = ?
            """
            cursor.execute(update_pp_sql, (
                current_pps[0] if len(current_pps) > 0 else 0,
                current_pps[1] if len(current_pps) > 1 else 0,
                current_pps[2] if len(current_pps) > 2 else 0,
                current_pps[3] if len(current_pps) > 3 else 0,
                new_id
            ))

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

    def update_user_pokemon_happiness(self, user_id: str, pokemon_id: int, happiness: int) -> None:
        """更新用户宝可梦的友好度"""
        self._update_user_pokemon_fields(user_id, pokemon_id, happiness=happiness)

    def update_user_pokemon_current_hp(self, user_id: str, pokemon_id: int, current_hp: int) -> None:
        """更新用户宝可梦的当前HP"""
        self._update_user_pokemon_fields(user_id, pokemon_id, current_hp=current_hp)

    def update_user_pokemon_current_pp(self, user_id: str, pokemon_id: int, current_pp1: int = None,
                                       current_pp2: int = None, current_pp3: int = None, current_pp4: int = None) -> None:
        """更新用户宝可梦的当前PP"""
        updates = {}
        if current_pp1 is not None:
            updates['current_pp1'] = current_pp1
        if current_pp2 is not None:
            updates['current_pp2'] = current_pp2
        if current_pp3 is not None:
            updates['current_pp3'] = current_pp3
        if current_pp4 is not None:
            updates['current_pp4'] = current_pp4
        if updates:
            self._update_user_pokemon_fields(user_id, pokemon_id, **updates)

    def update_user_pokemon_full_heal(self, user_id: str, pokemon_id: int) -> None:
        """完全治愈宝可梦（恢复HP和PP）"""
        # 获取宝可梦信息以知道最大HP
        pokemon_info = self.get_user_pokemon_by_id(user_id, pokemon_id)
        if pokemon_info:
            # 恢复HP到最大值
            self.update_user_pokemon_current_hp(user_id, pokemon_id, pokemon_info.stats.hp)

            # 恢复PP到最大值（需要获取技能的PP）
            moves = [pokemon_info.moves.move1_id, pokemon_info.moves.move2_id,
                     pokemon_info.moves.move3_id, pokemon_info.moves.move4_id]

            # 使用一个临时实例来获取技能PP
            temp_repo = SqliteMoveRepository(self.db_path)
            current_pps = []
            for move_id in moves:
                if move_id:
                    move_info = temp_repo.get_move_by_id(move_id)
                    max_pp = move_info['pp'] if move_info else 0
                    current_pps.append(max_pp)
                else:
                    current_pps.append(0)

            self.update_user_pokemon_current_pp(user_id, pokemon_id,
                                              current_pp1=current_pps[0] if len(current_pps) > 0 else 0,
                                              current_pp2=current_pps[1] if len(current_pps) > 1 else 0,
                                              current_pp3=current_pps[2] if len(current_pps) > 2 else 0,
                                              current_pp4=current_pps[3] if len(current_pps) > 3 else 0)

    def update_user_pokemon_favorite(self, user_id: str, pokemon_id: int, is_favorite: int) -> None:
        """更新用户宝可梦的收藏状态"""
        self._update_user_pokemon_fields(user_id, pokemon_id, is_favorite=is_favorite)

    def update_user_pokemon_held_item(self, user_id: str, pokemon_id: int, held_item_id: int) -> None:
        """更新用户宝可梦的持有物"""
        self._update_user_pokemon_fields(user_id, pokemon_id, held_item_id=held_item_id)

    # =========查=========
    def get_user_pokemon(self, user_id: str) -> List[UserPokemonInfo]:
        sql = """
              SELECT up.*, ps.name_zh as species_name, ps.name_en as species_en_name
              FROM user_pokemon up
                       JOIN pokemon_species ps ON up.species_id = ps.id
              WHERE up.user_id = ?
              ORDER BY up.caught_time DESC, up.id \
              """
        cursor = self._get_connection().execute(sql, (user_id,))
        return [self._row_to_user_pokemon(row) for row in cursor.fetchall()]

    def get_user_pokemon_paged(self, user_id: str, limit: int, offset: int) -> List[UserPokemonInfo]:
        """分页获取用户宝可梦"""
        sql = """
              SELECT up.*, ps.name_zh as species_name, ps.name_en as species_en_name
              FROM user_pokemon up
                       JOIN pokemon_species ps ON up.species_id = ps.id
              WHERE up.user_id = ?
              ORDER BY up.caught_time DESC, up.id
              LIMIT ? OFFSET ? \
              """
        cursor = self._get_connection().execute(sql, (user_id, limit, offset))
        return [self._row_to_user_pokemon(row) for row in cursor.fetchall()]

    def get_user_pokemon_count(self, user_id: str) -> int:
        """获取用户宝可梦总数"""
        sql = """
              SELECT COUNT(*)
              FROM user_pokemon
              WHERE user_id = ? \
              """
        cursor = self._get_connection().execute(sql, (user_id,))
        return cursor.fetchone()[0]

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

        # 1. 查询已捕捉的 IDs (包括当前拥有的和历史上捕获过的)
        # 从用户拥有的宝可梦获取
        cursor = conn.execute("SELECT DISTINCT species_id FROM user_pokemon WHERE user_id = ? AND isdel = 0",
                              (user_id,))
        current_pokemon_species = {row[0] for row in cursor.fetchall()}

        # 从图鉴捕获历史获取
        cursor = conn.execute("SELECT DISTINCT species_id FROM user_pokedex_capture_history WHERE user_id = ? AND isdel = 0",
                              (user_id,))
        captured_history_species = {row[0] for row in cursor.fetchall()}

        # 合并所有已捕获的物种ID
        caught_ids = current_pokemon_species | captured_history_species

        # 2. 查询"遇到过"的 IDs (包含已捕捉的和在野外遇到的)
        # SQL逻辑：(用户拥有的) UNION (图鉴捕获历史) UNION (遇到记录关联的野怪种族)
        sql_seen = """
                   SELECT species_id
                   FROM user_pokemon
                   WHERE user_id = ?
                   UNION
                   SELECT species_id
                   FROM user_pokedex_capture_history
                   WHERE user_id = ?
                   UNION
                   SELECT w.species_id
                   FROM wild_pokemon_encounter_log log
                            JOIN wild_pokemon w ON log.wild_pokemon_id = w.id
                   WHERE log.user_id = ?
                     AND w.isdel = 0
                   """
        cursor = conn.execute(sql_seen, (user_id, user_id, user_id))
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

    def set_user_current_trainer_encounter(self, user_id: str, trainer_id: int) -> None:
        """设置用户当前遭遇的训练家ID"""
        # 需要借助用户仓储来更新用户表
        # 由于循环依赖，我们直接在这里操作用户表
        from .sqlite_user_repo import SqliteUserRepository
        conn = self._get_connection()
        with conn:
            conn.execute("""
                UPDATE users
                SET current_trainer_encounter_id = ?
                WHERE user_id = ?
            """, (trainer_id, user_id))

    def get_user_current_trainer_encounter(self, user_id: str) -> Optional[int]:
        """获取用户当前遭遇的训练家ID"""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT current_trainer_encounter_id
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else None

    def get_user_favorite_pokemon(self, user_id: str) -> List[UserPokemonInfo]:
        """获取用户收藏的宝可梦列表"""
        sql = """
              SELECT up.*, ps.name_zh as species_name, ps.name_en as species_en_name
              FROM user_pokemon up
                       JOIN pokemon_species ps ON up.species_id = ps.id
              WHERE up.user_id = ? AND up.is_favorite = 1
              ORDER BY up.caught_time DESC, up.id \
              """
        cursor = self._get_connection().execute(sql, (user_id,))
        return [self._row_to_user_pokemon(row) for row in cursor.fetchall()]

    def get_user_favorite_pokemon_paged(self, user_id: str, page: int, page_size: int) -> List[UserPokemonInfo]:
        """获取用户收藏的宝可梦列表（分页）"""
        offset = (page - 1) * page_size
        sql = """
              SELECT up.*, ps.name_zh as species_name, ps.name_en as species_en_name
              FROM user_pokemon up
                       JOIN pokemon_species ps ON up.species_id = ps.id
              WHERE up.user_id = ? AND up.is_favorite = 1
              ORDER BY up.caught_time DESC, up.id
              LIMIT ? OFFSET ?
              """
        cursor = self._get_connection().execute(sql, (user_id, page_size, offset))
        return [self._row_to_user_pokemon(row) for row in cursor.fetchall()]

    def clear_user_current_trainer_encounter(self, user_id: str) -> None:
        """清除用户当前遭遇的训练家ID"""
        conn = self._get_connection()
        with conn:
            conn.execute("""
                UPDATE users
                SET current_trainer_encounter_id = NULL
                WHERE user_id = ?
            """, (user_id,))

    def record_pokedex_capture(self, user_id: str, species_id: int) -> None:
        """记录用户捕获的宝可梦物种到图鉴历史"""
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT OR IGNORE INTO user_pokedex_capture_history
                    (user_id, species_id)
                VALUES (?, ?)
            """, (user_id, species_id))