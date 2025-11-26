import os
import pandas as pd
import glob
import re

from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.infrastructure.repositories.abstract_repository import (
    AbstractPokemonRepository,
    AbstractAdventureRepository,
    AbstractShopRepository,
    AbstractMoveRepository,
)
from astrbot.api import logger


class DataSetupService:
    """负责在首次启动时初始化游戏基础数据，从v3 CSV文件读取数据。"""

    def __init__(self,
                 pokemon_repo: AbstractPokemonRepository,
                 adventure_repo: AbstractAdventureRepository,
                 shop_repo: AbstractShopRepository,
                 move_repo: AbstractMoveRepository,
                 data_path: str = None
                 ):
        self.pokemon_repo = pokemon_repo
        self.adventure_repo = adventure_repo
        self.shop_repo = shop_repo
        self.move_repo = move_repo
        # 如果未指定路径，则使用相对于插件根目录的路径
        if data_path is None:
            plugin_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            self.data_path = os.path.join(plugin_root_dir, "assets", "data", "v3")
        else:
            self.data_path = data_path

    def _read_csv_data(self, filename: str) -> pd.DataFrame:
        """读取CSV文件数据"""
        file_path = os.path.join(self.data_path, filename)
        if not os.path.exists(file_path):
            logger.warning(f"CSV文件不存在: {file_path}")
            return pd.DataFrame()
        return pd.read_csv(file_path)

    def setup_initial_data(self):
        """
        检查核心数据表是否为空，如果为空则进行数据填充。
        从v3目录中的CSV文件读取数据并填充到数据库。
        这是一个幂等操作（idempotent），可以安全地多次调用而不会重复插入数据。
        """
        try:
            existing_pokemon = self.pokemon_repo.get_all_pokemon()
            if existing_pokemon:
                logger.info("数据库核心数据已存在，跳过初始化。")
                return
        except Exception as e:
            # 如果表不存在等数据库错误，也需要继续执行创建和插入
            logger.error(f"检查数据时发生错误 (可能是表不存在，将继续初始化): {e}")

        logger.info("检测到数据库为空或核心数据不完整，正在从v3目录初始化游戏数据...")

        # 读取v3目录中的CSV数据
        pokemon_species_df = self._read_csv_data("pokemon_species.csv")
        pokemon_types_df = self._read_csv_data("pokemon_types.csv")
        pokemon_species_types_df = self._read_csv_data("pokemon_species_types.csv")
        pokemon_evolution_df = self._read_csv_data("pokemon_evolution.csv")
        items_df = self._read_csv_data("items.csv")
        locations_df = self._read_csv_data("locations.csv")
        location_pokemon_df = self._read_csv_data("location_pokemon.csv")
        moves_df = self._read_csv_data("moves.csv")
        pokemon_moves_df = self._read_csv_data("pokemon_moves.csv")
        # 注意：初始数据中的其他数据（如技能、冒险区域等）可能仍需要从其他来源获取
        # 我们假设这些数据仍然在initial_data.py中，或者需要创建对应的CSV文件

        # 填充Pokemon数据
        if not pokemon_species_df.empty:
            for _, pokemon_row in pokemon_species_df.iterrows():
                self.pokemon_repo.add_pokemon_template(
                    {
                        "id": pokemon_row['id'],
                        "name_en": pokemon_row['name_en'],
                        "name_zh": pokemon_row['name_zh'],
                        "generation_id": pokemon_row['generation_id'],
                        "base_hp": pokemon_row['base_hp'],
                        "base_attack": pokemon_row['base_attack'],
                        "base_defense": pokemon_row['base_defense'],
                        "base_sp_attack": pokemon_row['base_sp_attack'],
                        "base_sp_defense": pokemon_row['base_sp_defense'],
                        "base_speed": pokemon_row['base_speed'],
                        "height": pokemon_row['height'],
                        "weight": pokemon_row['weight'],
                        "base_experience": pokemon_row['base_experience'],
                        "gender_rate": pokemon_row['gender_rate'],
                        "capture_rate": pokemon_row['capture_rate'],
                        "growth_rate_id": pokemon_row['growth_rate_id'],
                        "description": pokemon_row['description'],
                        "orders": pokemon_row['order'] if 'order' in pokemon_species_df.columns else pokemon_row['id']
                    }
                )

        # 填充Pokemon类型数据
        if not pokemon_types_df.empty:
            for _, type_row in pokemon_types_df.iterrows():
                self.pokemon_repo.add_pokemon_type_template(
                    {
                        "id": type_row['id'],
                        "name_en": type_row['name_en'],  # 英文名称
                        "name_zh": type_row['name_zh'],  # 中文名称
                    }
                )

        # 填充Pokemon类型关联数据
        if not pokemon_species_types_df.empty:
            for _, species_type_row in pokemon_species_types_df.iterrows():
                self.pokemon_repo.add_pokemon_species_type_template(
                    {
                        "species_id": int(species_type_row['pokemon_id']),
                        "type_id": int(species_type_row['type_id']),
                    }
                )

        # 填充Pokemon进化数据
        if not pokemon_evolution_df.empty:
            for _, evolution_row in pokemon_evolution_df.iterrows():
                # 直接使用CSV中的字段映射到数据库字段
                evolution_data = {
                    "id": evolution_row['id'],
                    "pre_species_id": evolution_row['pre_species_id'],
                    "evolved_species_id": evolution_row['evolved_species_id'],
                    "evolution_trigger_id": evolution_row.get('evolution_trigger_id', 0),
                    "trigger_item_id": evolution_row.get('trigger_item_id', 0),
                    "minimum_level": evolution_row.get('minimum_level', 0),
                    "gender_id": evolution_row.get('gender_id', 0),
                    "location_id": evolution_row.get('location_id', 0),
                    "held_item_id": evolution_row.get('held_item_id', 0),
                    "time_of_day": evolution_row.get('time_of_day', ''),
                    "known_move_id": evolution_row.get('known_move_id', 0),
                    "known_move_type_id": evolution_row.get('known_move_type_id', 0),
                    "minimum_happiness": evolution_row.get('minimum_happiness', 0),
                    "minimum_beauty": evolution_row.get('minimum_beauty', 0),
                    "minimum_affection": evolution_row.get('minimum_affection', 0),
                    "relative_physical_stats": evolution_row.get('relative_physical_stats', 0),
                    "party_species_id": evolution_row.get('party_species_id', 0),
                    "party_type_id": evolution_row.get('party_type_id', 0),
                    "trade_species_id": evolution_row.get('trade_species_id', 0),
                    "needs_overworld_rain": evolution_row.get('needs_overworld_rain', 0),
                    "turn_upside_down": evolution_row.get('turn_upside_down', 0),
                    "region_id": evolution_row.get('region_id', 0),
                    "base_form_id": evolution_row.get('base_form_id', 0)
                }

                self.pokemon_repo.add_pokemon_evolution_template(evolution_data)

        # 填充物品数据
        if not items_df.empty:
            for _, item_row in items_df.iterrows():
                try:
                    # 注意：数据库items表字段为: id, name, rarity, price, type, description
                    # 需要调整字段映射以适配数据库结构
                    item_data = {
                        "id": int(item_row['id']),
                        "name_en": str(item_row['name_en']),  # 使用英文名称作为name_en字段
                        "name_zh": str(item_row['name_zh']),  # 使用中文名称作为name_zh字段
                        "category_id": int(item_row['category_id']),
                        "cost": int(item_row['cost']),
                        "description": str(item_row['description']) if pd.notna(item_row['description']) else ""
                    }

                    self.shop_repo.add_item_template(item_data)
                except (ValueError, TypeError) as e:
                    logger.error(f"处理物品数据时出错 (ID: {item_row.get('id', 'Unknown')}): {e}")
                    continue

        # 填充地点数据
        if not locations_df.empty:
            for _, location_row in locations_df.iterrows():
                try:
                    location_data = {
                        "id": int(location_row['id']),
                        "name": str(location_row['name']),
                        "description": str(location_row['description']) if pd.notna(location_row['description']) else "",
                        "min_level": int(location_row['min_level']) if pd.notna(location_row['min_level']) else 1,
                        "max_level": int(location_row['max_level']) if pd.notna(location_row['max_level']) else 100
                    }
                    self.adventure_repo.add_location_template(location_data)
                except (ValueError, TypeError) as e:
                    logger.error(f"处理地点数据时出错 (ID: {location_row.get('id', 'Unknown')}): {e}")
                    continue

        # 填充地点宝可梦关联数据
        if not location_pokemon_df.empty:
            for _, loc_pokemon_row in location_pokemon_df.iterrows():
                try:
                    location_pokemon_data = {
                        "id": int(loc_pokemon_row['id']),
                        "location_id": int(loc_pokemon_row['location_id']),  # 需要将CSV中的location_id映射为location_id
                        "pokemon_species_id": int(loc_pokemon_row['pokemon_species_id']),
                        "encounter_rate": float(loc_pokemon_row['encounter_rate']) if pd.notna(loc_pokemon_row['encounter_rate']) else 10.0,
                        "min_level": int(loc_pokemon_row['min_level']) if pd.notna(loc_pokemon_row['min_level']) else 1,
                        "max_level": int(loc_pokemon_row['max_level']) if pd.notna(loc_pokemon_row['max_level']) else 10
                    }
                    self.adventure_repo.add_location_pokemon_template(location_pokemon_data)
                except (ValueError, TypeError) as e:
                    logger.error(f"处理地点宝可梦关联数据时出错 (Location: {loc_pokemon_row.get('location_id', 'Unknown')}, Pokemon: {loc_pokemon_row.get('pokemon_species_id', 'Unknown')}): {e}")
                    continue

        # 填充技能数据
        if not moves_df.empty:
            for _, move_row in moves_df.iterrows():
                try:
                    move_data = {
                        "id": int(move_row['id']),
                        "name_en": str(move_row['name_en']),
                        "name_zh": str(move_row['name_zh']) if pd.notna(move_row['name_zh']) else None,
                        "generation_id": int(move_row['generation_id']),
                        "type_id": int(move_row['type_id']),
                        "power": int(move_row['power']) if pd.notna(move_row['power']) else None,
                        "pp": int(move_row['pp']) if pd.notna(move_row['pp']) else None,
                        "accuracy": int(move_row['accuracy']) if pd.notna(move_row['accuracy']) else None,
                        "priority": int(move_row['priority']) if pd.notna(move_row['priority']) else 0,
                        "target_id": int(move_row['target_id']),
                        "damage_class_id": int(move_row['damage_class_id']),
                        "effect_id": int(move_row['effect_id']) if pd.notna(move_row['effect_id']) else None,
                        "effect_chance": int(move_row['effect_chance']) if pd.notna(move_row['effect_chance']) else None,
                        "description": str(move_row['description']) if pd.notna(move_row['description']) else ""
                    }
                    self.move_repo.add_move_template(move_data)


                except (ValueError, TypeError) as e:
                    logger.error(f"处理技能数据时出错 (ID: {move_row.get('id', 'Unknown')}): {e}")
                    continue

        if not pokemon_moves_df.empty:
            # 对数据进行排序，按 pokemon_species_id (pokemon_id) 和 level 排序，确保数据有序
            pokemon_moves_df_sorted = pokemon_moves_df.sort_values(['pokemon_id', 'pokemon_move_method_id']).reset_index(drop=True)

            # 分批处理数据以提高性能，使用批量插入方法
            batch_size = 1000  # 设置批量大小为1000条记录
            total_rows = len(pokemon_moves_df_sorted)

            for i in range(0, total_rows, batch_size):
                batch_df = pokemon_moves_df_sorted.iloc[i:i + batch_size]

                # 收集批量数据
                batch_data = []
                for _, pokemon_move_row in batch_df.iterrows():
                    try:
                        pokemon_move_data = {
                            "pokemon_species_id": int(pokemon_move_row['pokemon_id']),
                            "move_id": int(pokemon_move_row['move_id']),
                            "move_method_id": int(pokemon_move_row['pokemon_move_method_id']),
                            "level": int(pokemon_move_row['level']) if pd.notna(pokemon_move_row['level']) else 0
                        }
                        batch_data.append(pokemon_move_data)
                    except (ValueError, TypeError) as e:
                        logger.error(f"处理宝可梦技能学习数据时出错 (Pokemon ID: {pokemon_move_row.get('pokemon_id', 'Unknown')}, Move ID: {pokemon_move_row.get('move_id', 'Unknown')}): {e}")
                        continue

                # 批量插入数据
                if batch_data:
                    try:
                        self.move_repo.add_pokemon_species_move_templates_batch(batch_data)
                    except Exception as e:
                        logger.error(f"批量插入宝可梦技能学习数据时出错: {e}")
                        # 如果批量插入失败，尝试逐条插入
                        for data in batch_data:
                            try:
                                self.move_repo.add_pokemon_species_move_template(data)
                            except Exception as single_e:
                                logger.error(f"单条插入宝可梦技能学习数据失败: {data}, 错误: {single_e}")