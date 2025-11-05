from ..repositories.abstract_repository import (
    AbstractItemTemplateRepository,
)
from ..initial_data import (
    POKEMON_SPECIES_DATA, POKEMON_TYPES_DATA, POKEMON_SPECIES_TYPES_DATA, POKEMON_EVOLUTION_DATA, ITEM_DATA,
    POKEMON_MOVES_DATA, POKEMON_SPECIES_MOVES_DATA,
)
from astrbot.api import logger

class DataSetupService:
    """负责在首次启动时初始化游戏基础数据。"""

    def __init__(self,
                 item_template_repo: AbstractItemTemplateRepository,
):
        self.item_template_repo = item_template_repo


    def setup_initial_data(self):
        """
        检查核心数据表是否为空，如果为空则进行数据填充。
        这是一个幂等操作（idempotent），可以安全地多次调用而不会重复插入数据。
        """
        try:
            existing_pokemon = self.item_template_repo.get_all_pokemon()
            if existing_pokemon:
                logger.info("数据库核心数据已存在，跳过初始化。")
                return
        except Exception as e:
            # 如果表不存在等数据库错误，也需要继续执行创建和插入
            logger.error(f"检查数据时发生错误 (可能是表不存在，将继续初始化): {e}")

        logger.info("检测到数据库为空或核心数据不完整，正在初始化游戏数据...")

        # 填充Pokemon类型数据
        for type in POKEMON_TYPES_DATA:
            self.item_template_repo.add_pokemon_type_template(
                {
                    "name": type[0],
                }
            )
        # 填充Pokemon数据
        for pokemon in POKEMON_SPECIES_DATA:
            self.item_template_repo.add_pokemon_template(
                {
                    "id": pokemon[0],
                    "name_en": pokemon[1],
                    "name_cn": pokemon[2],
                    "generation": pokemon[3],
                    "base_hp": pokemon[4],
                    "base_attack": pokemon[5],
                    "base_defense": pokemon[6],
                    "base_sp_attack": pokemon[7],
                    "base_sp_defense": pokemon[8],
                    "base_speed": pokemon[9],
                    "height": pokemon[10],
                    "weight": pokemon[11],
                    "description": pokemon[12],
                }
            )
        # 填充Pokemon类型关联数据
        for species_type in POKEMON_SPECIES_TYPES_DATA:
            self.item_template_repo.add_pokemon_species_type_template(
                {
                    "species_id": species_type[0],
                    "type_id": species_type[1],
                }
            )
        for evaluation in POKEMON_EVOLUTION_DATA:
            self.item_template_repo.add_pokemon_evolution_template(
                {
                    "from_species_id": evaluation[0],
                    "to_species_id": evaluation[1],
                    "method": evaluation[2],
                    "condition_value": evaluation[3],
                }
            )
        for item in ITEM_DATA:
            self.item_template_repo.add_item_template(
                {
                    "id": item[0],
                    "name": item[1],
                    "rarity": item[2],
                    "price": item[3],
                    "type": item[4],
                    "description": item[5],
                }
            )
        for moves in POKEMON_MOVES_DATA:
            self.item_template_repo.add_pokemon_move_template(
                {
                    "id": moves[0],
                    "name": moves[1],
                    "type_id": moves[2],
                    "category": moves[3],
                    "power": moves[4],
                    "accuracy": moves[5],
                    "pp": moves[6],
                    "description": moves[7],
                }
            )
        for species_moves in POKEMON_SPECIES_MOVES_DATA:
            self.item_template_repo.add_pokemon_species_move_template(
                {
                    "species_id": species_moves[0],
                    "move_id": species_moves[1],
                    "learn_method": species_moves[2],
                    "learn_value": species_moves[3],
                }
            )