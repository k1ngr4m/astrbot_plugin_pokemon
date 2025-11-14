from ..repositories.abstract_repository import (
    AbstractPokemonRepository,
    AbstractAreaRepository,
    AbstractShopRepository,
)
from ..database.data.initial_data import (
    POKEMON_SPECIES_DATA, POKEMON_TYPES_DATA, POKEMON_SPECIES_TYPES_DATA, POKEMON_EVOLUTION_DATA, ITEM_DATA,
    POKEMON_MOVES_DATA, ADVENTURE_AREAS_DATA, AREA_POKEMON_DATA, SHOP_DATA, SHOP_ITEM_DATA,
)
from ..domain.models import AdventureArea, AreaPokemon, Shop, ShopItem
from ..database.data.pokemon_moves_data import (
    POKEMON_SPECIES_MOVES_DATA,
)
from astrbot.api import logger

class DataSetupService:
    """负责在首次启动时初始化游戏基础数据。"""

    def __init__(self,
                 pokemon_repo: AbstractPokemonRepository,
                 area_repo=AbstractAreaRepository,
                 shop_repo=AbstractShopRepository,
                 ):
        self.pokemon_repo = pokemon_repo
        self.area_repo = area_repo
        self.shop_repo = shop_repo


    def setup_initial_data(self):
        """
        检查核心数据表是否为空，如果为空则进行数据填充。
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

        logger.info("检测到数据库为空或核心数据不完整，正在初始化游戏数据...")

        # 填充Pokemon类型数据
        for type in POKEMON_TYPES_DATA:
            self.pokemon_repo.add_pokemon_type_template(
                {
                    "name": type[0],
                }
            )
        # 填充Pokemon数据
        for pokemon in POKEMON_SPECIES_DATA:
            self.pokemon_repo.add_pokemon_template(
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
            self.pokemon_repo.add_pokemon_species_type_template(
                {
                    "species_id": species_type[0],
                    "type_id": species_type[1],
                }
            )
        for evaluation in POKEMON_EVOLUTION_DATA:
            self.pokemon_repo.add_pokemon_evolution_template(
                {
                    "from_species_id": evaluation[0],
                    "to_species_id": evaluation[1],
                    "method": evaluation[2],
                    "condition_value": evaluation[3],
                }
            )
        for item in ITEM_DATA:
            self.pokemon_repo.add_item_template(
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
            self.pokemon_repo.add_pokemon_move_template(
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
            self.pokemon_repo.add_pokemon_species_move_template(
                {
                    "species_id": species_moves[0],
                    "move_id": species_moves[1],
                    "learn_method": species_moves[2],
                    "learn_value": species_moves[3],
                }
            )

        # 填充冒险区域数据（仅在area_repo可用时执行）
        if self.area_repo:
            for area in ADVENTURE_AREAS_DATA:
                # 创建AdventureArea对象，使用临时id（数据库会自动生成正确id）
                area_obj = AdventureArea(
                    id=0,  # 临时id，实际id会在数据库插入后生成
                    area_code=area[0],
                    name=area[1],
                    description=area[2],
                    min_level=area[3],
                    max_level=area[4]
                )
                self.area_repo.add_area(area_obj)

            # 填充区域宝可梦关联数据
            for area_pokemon in AREA_POKEMON_DATA:
                # area_pokemon[0]是区域代码，需要先获取区域ID
                area = self.area_repo.get_area_by_code(area_pokemon[0])
                if area:
                    # 创建AreaPokemon对象，使用临时id（数据库会自动生成正确id）
                    ap_obj = AreaPokemon(
                        id=0,  # 临时id，实际id会在数据库插入后生成
                        area_id=area.id,
                        pokemon_species_id=area_pokemon[1],
                        encounter_rate=area_pokemon[2],
                        min_level=area_pokemon[3],
                        max_level=area_pokemon[4]
                    )
                    self.area_repo.add_area_pokemon(ap_obj)

        # 填充商店数据（仅在shop_repo可用时执行）
        if self.shop_repo:
            for shop in SHOP_DATA:
                # 创建Shop对象，使用临时id（数据库会自动生成正确id）
                shop_obj = Shop(
                    id=0,  # 临时id，实际id会在数据库插入后生成
                    shop_code=shop[0],
                    name=shop[1],
                    description=shop[2],
                )
                self.shop_repo.add_shop(shop_obj)

            # 填充商店商品关联数据
            for shop_item in SHOP_ITEM_DATA:
                # shop_item[0]是商店代码，需要先获取商店ID
                shop = self.shop_repo.get_shop_by_code(shop_item[0])
                if shop:
                    # 创建ShopItem对象，使用临时id（数据库会自动生成正确id）
                    si_obj = ShopItem(
                        id=0,  # 临时id，实际id会在数据库插入后生成
                        shop_id=shop.id,
                        item_id=shop_item[1],
                        price=shop_item[2],
                        stock=shop_item[3],
                        is_active=shop_item[4],
                    )
                    self.shop_repo.add_shop_item(si_obj)

                logger.info("✅ 商店数据初始化完成")