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
