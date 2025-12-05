import os
import pandas as pd
from ...infrastructure.repositories.abstract_repository import (
    AbstractPokemonRepository,
    AbstractAdventureRepository,
    AbstractShopRepository,
    AbstractMoveRepository, AbstractItemRepository,
    AbstractNatureRepository, AbstractTrainerRepository,
)
from astrbot.api import logger


class DataSetupService:
    """负责在首次启动时初始化游戏基础数据，从v3 CSV文件读取数据。"""

    def __init__(self,
                 pokemon_repo: AbstractPokemonRepository,
                 adventure_repo: AbstractAdventureRepository,
                 shop_repo: AbstractShopRepository,
                 move_repo: AbstractMoveRepository,
                 item_repo: AbstractItemRepository,
                 nature_repo: AbstractNatureRepository,
                 trainer_repo: AbstractTrainerRepository,
                 data_path: str = None
                 ):
        self.pokemon_repo = pokemon_repo
        self.adventure_repo = adventure_repo
        self.shop_repo = shop_repo
        self.move_repo = move_repo
        self.item_repo = item_repo
        self.nature_repo = nature_repo
        self.trainer_repo = trainer_repo

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
        这是一个幂等操作（idempotent）。
        """
        logger.info("开始检查并初始化游戏数据...")

        try:
            # 1. 填充 Pokemon 数据
            if not self.pokemon_repo.get_all_pokemon():
                df = self._read_csv_data("pokemon_species.csv")
                if not df.empty:
                    logger.info("正在初始化宝可梦种族数据...")
                    df = df.where(pd.notnull(df), None)

                    pokemon_data_list = [
                        {
                            "id": row['id'],
                            "name_en": row['name_en'],
                            "name_zh": row['name_zh'],
                            "generation_id": row['generation_id'],
                            "base_hp": row['base_hp'],
                            "base_attack": row['base_attack'],
                            "base_defense": row['base_defense'],
                            "base_sp_attack": row['base_sp_attack'],
                            "base_sp_defense": row['base_sp_defense'],
                            "base_speed": row['base_speed'],
                            "height": row['height'],
                            "weight": row['weight'],
                            "base_experience": row['base_experience'],
                            "gender_rate": row['gender_rate'],
                            "capture_rate": row['capture_rate'],
                            "growth_rate_id": row['growth_rate_id'],
                            "description": row['description'],
                            "orders": row.get('order', row['id']),
                            "effort": row.get('effort', '[]')
                        }
                        for row in df.to_dict('records')
                    ]

                    if hasattr(self.pokemon_repo, 'add_pokemon_templates_batch'):
                        self.pokemon_repo.add_pokemon_templates_batch(pokemon_data_list)
                    else:
                        for data in pokemon_data_list:
                            self.pokemon_repo.add_pokemon_template(data)

            # 2. 填充 Pokemon 类型数据
            if not self.pokemon_repo.get_pokemon_types(1):
                df = self._read_csv_data("pokemon_types.csv")
                if not df.empty:
                    for row in df.to_dict('records'):
                        self.pokemon_repo.add_pokemon_type_template({
                            "id": row['id'],
                            "name_en": row['name_en'],
                            "name_zh": row['name_zh'],
                        })

            # 3. 填充 Pokemon 类型关联
            if not self.pokemon_repo.get_pokemon_species_types(1):
                df = self._read_csv_data("pokemon_species_types.csv")
                if not df.empty:
                    for row in df.to_dict('records'):
                        try:
                            self.pokemon_repo.add_pokemon_species_type_template({
                                "species_id": int(row['pokemon_id']) if pd.notna(row['pokemon_id']) else 0,
                                "type_id": int(row['type_id']) if pd.notna(row['type_id']) else 0,
                            })
                        except Exception as e:
                            logger.error(f"宝可梦类型数据错误 (Species: {row.get('pokemon_id')}, Type: {row.get('type_id')}): {e}")

            # 4. 填充 Pokemon 进化数据
            if not self.pokemon_repo.get_pokemon_evolutions(1, 100):
                df = self._read_csv_data("pokemon_evolution.csv")
                if not df.empty:
                    logger.info("正在初始化宝可梦进化数据...")
                    df = df.where(pd.notnull(df), None)

                    evolution_data_list = [
                        {
                            "id": row['id'],
                            "pre_species_id": row['pre_species_id'],
                            "evolved_species_id": row['evolved_species_id'],
                            "evolution_trigger_id": row.get('evolution_trigger_id', 0),
                            "trigger_item_id": row.get('trigger_item_id', 0),
                            "minimum_level": row.get('minimum_level', 0),
                            "gender_id": row.get('gender_id', 0),
                            "location_id": row.get('location_id', 0),
                            "held_item_id": row.get('held_item_id', 0),
                            "time_of_day": row.get('time_of_day', ''),
                            "known_move_id": row.get('known_move_id', 0),
                            "known_move_type_id": row.get('known_move_type_id', 0),
                            "minimum_happiness": row.get('minimum_happiness', 0),
                            "minimum_beauty": row.get('minimum_beauty', 0),
                            "minimum_affection": row.get('minimum_affection', 0),
                            "relative_physical_stats": row.get('relative_physical_stats', 0),
                            "party_species_id": row.get('party_species_id', 0),
                            "party_type_id": row.get('party_type_id', 0),
                            "trade_species_id": row.get('trade_species_id', 0),
                            "needs_overworld_rain": row.get('needs_overworld_rain', 0),
                            "turn_upside_down": row.get('turn_upside_down', 0),
                            "region_id": row.get('region_id', 0),
                            "base_form_id": row.get('base_form_id', 0)
                        }
                        for row in df.to_dict('records')
                    ]

                    if hasattr(self.pokemon_repo, 'add_pokemon_evolutions_batch'):
                        self.pokemon_repo.add_pokemon_evolutions_batch(evolution_data_list)
                    else:
                        for data in evolution_data_list:
                            self.pokemon_repo.add_pokemon_evolution_template(data)

            # 5. 填充物品数据
            if not self.item_repo.get_item_name(1):
                df = self._read_csv_data("items.csv")
                if not df.empty:
                    logger.info("正在初始化物品数据...")
                    df = df.where(pd.notnull(df), None)
                    for row in df.to_dict('records'):
                        try:
                            item_data = {
                                "id": int(row['id']),
                                "name_en": str(row['name_en']),
                                "name_zh": str(row['name_zh']),
                                "category_id": int(row['category_id']),
                                "cost": int(row['cost']),
                                "description": str(row['description']) if row['description'] else ""
                            }
                            self.item_repo.add_item_template(item_data)
                        except Exception as e:
                            logger.error(f"物品数据错误 (ID: {row.get('id')}): {e}")

            # 6. 填充地点数据
            if not self.adventure_repo.get_location_by_id(1):
                df = self._read_csv_data("locations.csv")
                if not df.empty:
                    df = df.where(pd.notnull(df), None)
                    for row in df.to_dict('records'):
                        try:
                            self.adventure_repo.add_location_template({
                                "id": int(row['id']),
                                "name": str(row['name']),
                                "description": str(row['description']) if row['description'] else "",
                                "min_level": int(row['min_level']) if row['min_level'] else 1,
                                "max_level": int(row['max_level']) if row['max_level'] else 100
                            })
                        except Exception as e:
                            logger.error(f"地点数据错误 (ID: {row.get('id')}): {e}")

            # 7. 填充地点宝可梦关联
            if not self.adventure_repo.get_location_pokemon_by_location_id(1):
                df = self._read_csv_data("location_pokemon.csv")
                if not df.empty:
                    df = df.where(pd.notnull(df), None)
                    for row in df.to_dict('records'):
                        try:
                            self.adventure_repo.add_location_pokemon_template({
                                "id": int(row['id']),
                                "location_id": int(row['location_id']),
                                "pokemon_species_id": int(row['pokemon_species_id']),
                                "encounter_rate": float(row['encounter_rate']) if row['encounter_rate'] else 10.0,
                                "min_level": int(row['min_level']) if row['min_level'] else 1,
                                "max_level": int(row['max_level']) if row['max_level'] else 10
                            })
                        except Exception as e:
                            logger.error(f"地点宝可梦错误 (Loc: {row.get('location_id')}): {e}")

            # 8. 填充技能数据
            if not self.move_repo.get_move_by_id(1):
                df = self._read_csv_data("moves.csv")
                if not df.empty:
                    logger.info("正在初始化技能数据...")
                    df = df.where(pd.notnull(df), None)
                    for row in df.to_dict('records'):
                        try:
                            move_data = {
                                "id": int(row['id']) if pd.notna(row['id']) else 0,
                                "name_en": str(row['name_en']) if pd.notna(row['name_en']) else "",
                                "name_zh": str(row['name_zh']) if pd.notna(row['name_zh']) else None,
                                "generation_id": int(row['generation_id']) if pd.notna(row['generation_id']) else 0,
                                "type_id": int(row['type_id']) if pd.notna(row['type_id']) else 0,
                                "power": int(row['power']) if pd.notna(row['power']) else None,
                                "pp": int(row['pp']) if pd.notna(row['pp']) else None,
                                "accuracy": int(row['accuracy']) if pd.notna(row['accuracy']) else None,
                                "priority": int(row['priority']) if pd.notna(row['priority']) else 0,
                                "target_id": int(row['target_id']) if pd.notna(row['target_id']) else 0,
                                "damage_class_id": int(row['damage_class_id']) if pd.notna(row['damage_class_id']) else 0,
                                "effect_id": int(row['effect_id']) if pd.notna(row['effect_id']) else None,
                                "effect_chance": int(row['effect_chance']) if pd.notna(row['effect_chance']) else None,
                                "description": str(row['description']) if pd.notna(row['description']) else ""
                            }
                            self.move_repo.add_move_template(move_data)
                        except Exception as e:
                            logger.error(f"技能数据错误 (ID: {row.get('id')}): {e}")

            # 9. 填充宝可梦技能关联 (大批量数据)
            if not self.move_repo.get_pokemon_moves_by_species_id(1):
                df = self._read_csv_data("pokemon_moves.csv")
                if not df.empty:
                    logger.info("正在初始化宝可梦技能学习表 (可能需要几秒钟)...")
                    df = df.where(pd.notnull(df), None)
                    # 排序
                    df.sort_values(['pokemon_id', 'pokemon_move_method_id'], inplace=True)

                    records = df.to_dict('records')
                    batch_size = 1000

                    for i in range(0, len(records), batch_size):
                        batch = records[i:i + batch_size]
                        batch_data = []
                        for row in batch:
                            try:
                                batch_data.append({
                                    "pokemon_species_id": int(row['pokemon_id']) if pd.notna(row['pokemon_id']) else 0,
                                    "move_id": int(row['move_id']) if pd.notna(row['move_id']) else 0,
                                    "move_method_id": int(row['pokemon_move_method_id']) if pd.notna(row['pokemon_move_method_id']) else 0,
                                    "level": int(row['level']) if pd.notna(row['level']) else 0
                                })
                            except Exception:
                                continue

                        if batch_data:
                            try:
                                self.move_repo.add_pokemon_species_move_templates_batch(batch_data)
                            except Exception as e:
                                logger.error(f"批量插入技能失败，尝试单条插入: {e}")
                                for data in batch_data:
                                    try:
                                        self.move_repo.add_pokemon_species_move_template(data)
                                    except:
                                        pass

            # 10. 填充商店数据
            if not self.shop_repo.get_shop_by_id(1):
                df = self._read_csv_data("shops.csv")
                if not df.empty:
                    df = df.where(pd.notnull(df), None)
                    for row in df.to_dict('records'):
                        try:
                            self.shop_repo.add_shop_template({
                                "id": int(row['id']),
                                "name": str(row['name']),
                                "description": str(row['description']) if row['description'] else "",
                                "shop_type": str(row['shop_type']),
                                "is_active": int(row['is_active']),
                                "created_at": str(row['created_at']) if row['created_at'] else None,
                                "updated_at": str(row['updated_at']) if row['updated_at'] else None
                            })
                        except Exception as e:
                            logger.error(f"商店数据错误 (ID: {row.get('id')}): {e}")

            # 11. 填充商店物品
            if not self.shop_repo.get_shop_items_by_shop_id(1):
                df = self._read_csv_data("shop_items.csv")
                if not df.empty:
                    df = df.where(pd.notnull(df), None)
                    for row in df.to_dict('records'):
                        try:
                            self.shop_repo.add_shop_item_template({
                                "id": int(row['id']),
                                "shop_id": int(row['shop_id']),
                                "item_id": int(row['item_id']),
                                "price": int(row['price']),
                                "stock": int(row['stock']),
                                "is_active": int(row['is_active'])
                            })
                        except Exception as e:
                            logger.error(f"商店物品错误 (ID: {row.get('id')}): {e}")

            # 12. 填充性格数据
            if not self.nature_repo.get_nature_by_id(1):
                df = self._read_csv_data("natures.csv")
                if not df.empty:
                    logger.info("正在初始化性格数据...")
                    df = df.where(pd.notnull(df), None)

                    natures_list = [
                        {
                            "id": int(row['id']) if pd.notna(row['id']) else 0,
                            "name_en": str(row['name_en']) if pd.notna(row['name_en']) else "",
                            "name_zh": str(row['name_zh']) if pd.notna(row['name_zh']) else "",
                            "decreased_stat_id": int(row['decreased_stat_id']) if pd.notna(row['decreased_stat_id']) else 0,
                            "increased_stat_id": int(row['increased_stat_id']) if pd.notna(row['increased_stat_id']) else 0,
                            "hates_flavor_id": int(row['hates_flavor_id']) if pd.notna(row['hates_flavor_id']) else 0,
                            "likes_flavor_id": int(row['likes_flavor_id']) if pd.notna(row['likes_flavor_id']) else 0,
                            "game_index": int(row['game_index']) if pd.notna(row['game_index']) else 0
                        }
                        for row in df.to_dict('records')
                    ]

                    if hasattr(self.nature_repo, 'add_nature_templates_batch'):
                        self.nature_repo.add_nature_templates_batch(natures_list)
                    else:
                        for data in natures_list:
                            self.nature_repo.add_nature_template(data)


            if not self.nature_repo.get_nature_stats_by_nature_id(1):
                # 填充性格统计 (Pokeathlon)
                df_stats = self._read_csv_data("nature_stats.csv")
                if not df_stats.empty:
                    df_stats = df_stats.where(pd.notnull(df_stats), None)
                    stats_list = [
                        {
                            "nature_id": int(row['nature_id']) if pd.notna(row['nature_id']) else 0,
                            "pokeathlon_stat_id": int(row['pokeathlon_stat_id']) if pd.notna(row['pokeathlon_stat_id']) else 0,
                            "max_change": int(row['max_change']) if pd.notna(row['max_change']) else 0
                        }
                        for row in df_stats.to_dict('records')
                    ]

                    if hasattr(self.nature_repo, 'add_nature_stat_templates_batch'):
                        self.nature_repo.add_nature_stat_templates_batch(stats_list)
                    else:
                        for data in stats_list:
                            self.nature_repo.add_nature_stat_template(data)

            # 13. 填充训练家数据
            if self.trainer_repo:
                try:
                    # 检查是否已存在训练家数据（通过查询ID=1的记录）
                    first_trainer_exists = self.trainer_repo.get_trainer_by_id(1) is not None

                    if not first_trainer_exists:
                        logger.info("正在初始化训练家数据...")

                        # --- 13.1 训练家基础信息 (Trainers) ---
                        trainers_df = self._read_csv_data("trainers.csv")
                        if not trainers_df.empty:
                            trainers_df = trainers_df.where(pd.notnull(trainers_df), None)

                            # 预处理数据
                            trainers_data_list = [
                                {
                                    "id": int(row['id']),
                                    "name": str(row['name']),
                                    "trainer_class": str(row['trainer_class']),
                                    "base_payout": int(row['base_payout']),
                                    "description": str(row['description']) if row['description'] else None
                                }
                                for row in trainers_df.to_dict('records')
                            ]

                            # 尝试批量插入，如果Repo不支持则降级为单条插入
                            if hasattr(self.trainer_repo, 'create_trainers_batch'):
                                from ..models.trainer_models import Trainer
                                # 将字典转换为Trainer对象列表
                                trainer_list = [Trainer(**data) for data in trainers_data_list if data]
                                self.trainer_repo.create_trainers_batch(trainer_list)
                            else:
                                from ..models.trainer_models import Trainer
                                for data in trainers_data_list:
                                    try:
                                        self.trainer_repo.create_trainer(Trainer(**data))
                                    except Exception as e:
                                        logger.error(f"训练家插入失败 (ID: {data.get('id')}): {e}")

                        # --- 13.2 训练家宝可梦 (Trainer Pokemon) ---
                        trainer_pokemon_df = self._read_csv_data("trainer_pokemon.csv")
                        if not trainer_pokemon_df.empty:
                            trainer_pokemon_df = trainer_pokemon_df.where(pd.notnull(trainer_pokemon_df),
                                                                          None)

                            tp_data_list = [
                                {
                                    "id": int(row['id']),
                                    "trainer_id": int(row['trainer_id']),
                                    "pokemon_species_id": int(row['pokemon_species_id']),
                                    "level": int(row['level']),
                                    "position": int(row['position'])
                                }
                                for row in trainer_pokemon_df.to_dict('records')
                            ]

                            if hasattr(self.trainer_repo, 'create_trainer_pokemons_batch'):
                                from ..models.trainer_models import TrainerPokemon
                                # 将字典转换为TrainerPokemon对象列表
                                trainer_pokemon_list = [TrainerPokemon(**data) for data in tp_data_list if data]
                                self.trainer_repo.create_trainer_pokemons_batch(trainer_pokemon_list)
                            else:
                                from ..models.trainer_models import TrainerPokemon
                                for data in tp_data_list:
                                    try:
                                        self.trainer_repo.create_trainer_pokemon(TrainerPokemon(**data))
                                    except Exception as e:
                                        logger.error(f"训练家宝可梦插入失败 (ID: {data.get('id')}): {e}")

                        # --- 13.3 训练家分布位置 (Trainer Locations) ---
                        location_trainers_df = self._read_csv_data("location_trainers.csv")
                        if not location_trainers_df.empty:
                            location_trainers_df = location_trainers_df.where(
                                pd.notnull(location_trainers_df), None)

                            # 准备批量插入的元组列表
                            tl_params = [
                                {
                                    "id": int(row['id']),
                                    "trainer_id": int(row['trainer_id']),
                                    "location_id": int(row['location_id']),
                                    "encounter_rate": float(row['encounter_rate'])
                                }
                                for row in location_trainers_df.to_dict('records')
                            ]

                            if hasattr(self.trainer_repo, 'create_location_trainers_batch'):
                                from ..models.trainer_models import TrainerLocation
                                # 将字典转换为TrainerLocation对象列表
                                location_trainers_list = [TrainerLocation(**data) for data in tl_params if data]
                                self.trainer_repo.create_location_trainers_batch(location_trainers_list)

                        logger.info("训练家数据初始化完成")
                    else:
                        # 这是一个幂等检查，如果数据已存在则静默跳过或打印debug
                        pass
                except Exception as e:
                    logger.error(f"初始化训练家数据时发生错误: {e}")

        except Exception as e:
            logger.error(f"初始化数据时发生全局错误: {e}")
            # 允许继续运行，因为部分数据可能已经加载成功