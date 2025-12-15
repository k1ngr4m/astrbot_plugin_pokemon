from typing import Dict, Any, Optional, List
from .abstract_repository import AbstractMoveRepository
from astrbot.api import logger
import sqlite3

class SqliteMoveRepository(AbstractMoveRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def add_move_template(self, move_data: Dict[str, Any]) -> None:
        """添加技能模板"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO moves (
                        id, name_en, name_zh, generation_id, type_id, power, pp, 
                        accuracy, priority, target_id, damage_class_id, effect_id, 
                        effect_chance, description
                    ) VALUES (
                        :id, :name_en, :name_zh, :generation_id, :type_id, :power, :pp, 
                        :accuracy, :priority, :target_id, :damage_class_id, :effect_id, 
                        :effect_chance, :description
                    )
                """, move_data)
                conn.commit()
        except Exception as e:
            logger.error(f"添加技能模板失败: {e}")

    def add_pokemon_species_move_template(self, pokemon_moves_data: Dict[str, Any]) -> None:
        """添加宝可梦物种招式模板"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO pokemon_moves (
                        pokemon_species_id, move_id, move_method_id, level
                    ) VALUES (
                        :pokemon_species_id, :move_id, :move_method_id, :level
                    )
                """, pokemon_moves_data)
                conn.commit()
        except Exception as e:
            logger.error(f"添加宝可梦物种招式模板失败: {e}")

    def add_pokemon_species_move_templates_batch(self, pokemon_moves_list: List[Dict[str, Any]]) -> None:
        """批量添加宝可梦物种招式模板"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 准备批量插入的数据
                batch_records = []
                for data in pokemon_moves_list:
                    batch_records.append((
                        data['pokemon_species_id'],
                        data['move_id'],
                        data['move_method_id'],
                        data['level']
                    ))

                cursor.executemany("""
                    INSERT OR IGNORE INTO pokemon_moves (
                        pokemon_species_id, move_id, move_method_id, level
                    ) VALUES (?, ?, ?, ?)
                """, batch_records)
                conn.commit()
        except Exception as e:
            logger.error(f"批量添加宝可梦物种招式模板失败: {e}")
            raise

    def get_level_up_moves(self, pokemon_species_id: int, level: int) -> List[int]:
        """
        获取宝可梦在指定等级及以下可以学到的升级招式（method_id=1），
        优先等级高的招式。
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pm.move_id
                    FROM pokemon_moves pm
                    WHERE pm.pokemon_species_id = ?
                      AND pm.move_method_id = 1
                      AND pm.level <= ?
                    ORDER BY pm.level DESC
                """, (pokemon_species_id, level))
                rows = cursor.fetchall()
                # rows 是 [(move_id,), (move_id,), ...]
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"获取宝可梦升级招式失败: {e}")
            return []

    def get_moves_learned_in_level_range(self, pokemon_species_id: int, min_level: int, max_level: int) -> List[int]:
        """
        获取宝可梦在指定等级范围内新学会的升级招式
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT pm.move_id
                    FROM pokemon_moves pm
                    WHERE pm.pokemon_species_id = ?
                      AND pm.move_method_id = 1
                      AND pm.level > ?
                      AND pm.level <= ?
                    ORDER BY pm.level ASC
                """, (pokemon_species_id, min_level, max_level))
                rows = cursor.fetchall()
                return [row[0] for row in rows if row[0] is not None]
        except Exception as e:
            logger.error(f"获取宝可梦在等级范围内学会的招式失败: {e}")
            return []

    def get_move_by_id(self, move_id: int) -> Dict[str, Any] | None:
        """
        获取招式详细信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT m.id, m.name_en, m.name_zh, m.type_id, m.power, m.pp, m.accuracy,
                           m.priority, m.target_id, m.damage_class_id, m.effect_id, m.effect_chance, m.description,
                           mm.meta_category_id, mm.meta_ailment_id, mm.min_hits, mm.max_hits, mm.min_turns, mm.max_turns,
                           mm.drain, mm.healing, mm.crit_rate, mm.ailment_chance, mm.flinch_chance, mm.stat_chance
                    FROM moves m
                    JOIN move_meta mm ON m.id = mm.move_id
                    WHERE m.id = ?
                """, (move_id,))
                row = cursor.fetchone()
                if row:
                    # 获取招式类型名称
                    cursor.execute("SELECT name_en FROM pokemon_types WHERE id = ?", (row[3],))  # type_id
                    type_row = cursor.fetchone()
                    type_name = type_row[0] if type_row else "normal"

                    return {
                        "id": row[0],
                        "name_en": row[1],
                        "name_zh": row[2],
                        "type_name": type_name.lower(),
                        "power": row[4] if row[4] is not None else 0,
                        "pp": row[5] if row[5] is not None else 1,
                        "accuracy": row[6] if row[6] is not None else 100,
                        "priority": row[7] if row[7] is not None else 0,
                        "target_id": row[8],
                        "damage_class_id": row[9],
                        "effect_id": row[10],
                        "effect_chance": row[11],
                        "description": row[12],
                        "meta_category_id": row[13],
                        "meta_ailment_id": row[14],
                        "min_hits": row[15],
                        "max_hits": row[16],
                        "min_turns": row[17],
                        "max_turns": row[18],
                        "drain": row[19],
                        "healing": row[20],
                        "crit_rate": row[21],
                        "ailment_chance": row[22],
                        "flinch_chance": row[23],
                        "stat_chance": row[24],
                    }
        except Exception as e:
            logger.error(f"获取招式详细信息失败: {e}")
            return None

    def get_pokemon_moves_by_species_id(self, pokemon_species_id: int) -> List[Dict[str, Any]]:
        """
        获取宝可梦物种的所有招式
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pm.move_id, pm.move_method_id, pm.level
                    FROM pokemon_moves pm
                    WHERE pm.pokemon_species_id = ?
                """, (pokemon_species_id,))
                rows = cursor.fetchall()
                return [
                    {
                        "move_id": row[0],
                        "move_method_id": row[1],
                        "level": row[2]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取宝可梦物种招式失败: {e}")
            return []

    def add_move_flag_map_templates_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """批量添加招式Flag映射"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                batch_records = [(d['move_id'], d['move_flag_id']) for d in data_list]
                cursor.executemany("INSERT OR IGNORE INTO move_flag_map (move_id, move_flag_id) VALUES (?, ?)", batch_records)
                conn.commit()
        except Exception as e:
            logger.error(f"批量添加招式Flag映射失败: {e}")

    def add_move_meta_templates_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """批量添加招式元数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                batch_records = []
                for d in data_list:
                    batch_records.append((
                        d['move_id'], d['meta_category_id'], d['meta_ailment_id'],
                        d['min_hits'], d['max_hits'], d['min_turns'], d['max_turns'],
                        d['drain'], d['healing'], d['crit_rate'],
                        d['ailment_chance'], d['flinch_chance'], d['stat_chance']
                    ))
                
                cursor.executemany("""
                    INSERT OR IGNORE INTO move_meta (
                        move_id, meta_category_id, meta_ailment_id, 
                        min_hits, max_hits, min_turns, max_turns, 
                        drain, healing, crit_rate, 
                        ailment_chance, flinch_chance, stat_chance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch_records)
                conn.commit()
        except Exception as e:
            logger.error(f"批量添加招式元数据失败: {e}")

    def add_move_stat_change_templates_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """批量添加招式能力变化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                batch_records = [(d['move_id'], d['stat_id'], d['change']) for d in data_list]
                cursor.executemany("""
                    INSERT OR IGNORE INTO move_meta_stat_changes (move_id, stat_id, change) 
                    VALUES (?, ?, ?)
                """, batch_records)
                conn.commit()
        except Exception as e:
            logger.error(f"批量添加招式能力变化失败: {e}")

    def get_move_meta_by_move_id(self, move_id: int) -> Optional[Dict[str, Any]]:
        """获取招式元数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM move_meta WHERE move_id = ?", (move_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"获取招式元数据失败: {e}")
            return None

    def get_move_stat_changes_by_move_id(self, move_id: int) -> List[Dict[str, Any]]:
        """获取招式能力变化数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM move_meta_stat_changes WHERE move_id = ?", (move_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取招式能力变化数据失败: {e}")
            return []

    def get_moves_by_ids(self, move_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """批量获取招式详细信息"""
        if not move_ids:
            return {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 使用参数化查询和 IN 语句进行批量查询
                placeholders = ','.join('?' for _ in move_ids)
                cursor.execute(f"""
                    SELECT m.id, m.name_en, m.name_zh, m.type_id, m.power, m.pp, m.accuracy,
                           m.priority, m.target_id, m.damage_class_id, m.effect_id, m.effect_chance, m.description,
                           mm.meta_category_id, mm.meta_ailment_id, mm.min_hits, mm.max_hits, mm.min_turns, mm.max_turns,
                           mm.drain, mm.healing, mm.crit_rate, mm.ailment_chance, mm.flinch_chance, mm.stat_chance
                    FROM moves m
                    JOIN move_meta mm ON m.id = mm.move_id
                    WHERE m.id IN ({placeholders})
                """, move_ids)
                rows = cursor.fetchall()

                # 构建结果字典，键为 move_id
                result = {}
                for row in rows:
                    # 获取招式类型名称
                    cursor.execute("SELECT name_en FROM pokemon_types WHERE id = ?", (row[3],))  # type_id
                    type_row = cursor.fetchone()
                    type_name = type_row[0] if type_row else "normal"

                    result[row[0]] = {  # row[0] is move.id
                        "id": row[0],
                        "name_en": row[1],
                        "name_zh": row[2],
                        "type_name": type_name.lower(),
                        "power": row[4] if row[4] is not None else 0,
                        "pp": row[5] if row[5] is not None else 1,
                        "accuracy": row[6] if row[6] is not None else 100,
                        "priority": row[7] if row[7] is not None else 0,
                        "target_id": row[8],
                        "damage_class_id": row[9],
                        "effect_id": row[10],
                        "effect_chance": row[11],
                        "description": row[12],
                        "meta_category_id": row[13],
                        "meta_ailment_id": row[14],
                        "min_hits": row[15],
                        "max_hits": row[16],
                        "min_turns": row[17],
                        "max_turns": row[18],
                        "drain": row[19],
                        "healing": row[20],
                        "crit_rate": row[21],
                        "ailment_chance": row[22],
                        "flinch_chance": row[23],
                        "stat_chance": row[24],
                    }

                return result
        except Exception as e:
            logger.error(f"批量获取招式详细信息失败: {e}")
            return {}
