from ..repositories.abstract_repository import (
    AbstractItemTemplateRepository,
)
from ..initial_data import (
    POKEMON_SPECIES_DATA,
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
