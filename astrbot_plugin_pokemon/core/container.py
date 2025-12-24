import os
import shutil

from .services.player.user_item_serviece import UserItemService
from ..core.services import (
    UserPokemonService, PokemonService, TeamService, AdventureService,
    ExpService, UserService, ItemService, ShopService, MoveService,
    EvolutionService, NatureService, TrainerService, AbilityService
)

from ..infrastructure.repositories.sqlite_item_repo import SqliteItemRepository
from ..infrastructure.repositories.sqlite_nature_repo import SqliteNatureRepository
from ..infrastructure.repositories.sqlite_pokemon_repo import SqlitePokemonRepository
from ..infrastructure.repositories.sqlite_team_repo import SqliteTeamRepository
from ..infrastructure.repositories.sqlite_user_item_repo import SqliteUserItemRepository
from ..infrastructure.repositories.sqlite_user_repo import SqliteUserRepository
from ..infrastructure.repositories.sqlite_adventure_repo import SqliteAdventureRepository
from ..infrastructure.repositories.sqlite_battle_repo import SqliteBattleRepository
from ..infrastructure.repositories.sqlite_shop_repo import SqliteShopRepository
from ..infrastructure.repositories.sqlite_move_repo import SqliteMoveRepository
from ..infrastructure.repositories.sqlite_user_pokemon_repo import SqliteUserPokemonRepository
from ..infrastructure.repositories.sqlite_trainer_repo import SqliteTrainerRepository
from ..infrastructure.repositories.sqlite_ability_repo import SqliteAbilityRepository
from ..infrastructure.repositories.sqlite_pokemon_ability_repo import SqlitePokemonAbilityRepository


class GameContainer:
    """
    依赖注入容器：负责管理所有游戏核心组件的生命周期和依赖关系。
    """
    def __init__(self, db_path: str, config: dict):
        self.db_path = db_path
        self.config = config

        # 1. 初始化 Repositories
        self.user_repo = SqliteUserRepository(self.db_path)
        self.pokemon_repo = SqlitePokemonRepository(self.db_path)
        self.team_repo = SqliteTeamRepository(self.db_path)
        self.adventure_repo = SqliteAdventureRepository(self.db_path)
        self.shop_repo = SqliteShopRepository(self.db_path)
        self.item_repo = SqliteItemRepository(self.db_path)
        self.move_repo = SqliteMoveRepository(self.db_path)
        self.battle_repo = SqliteBattleRepository(self.db_path)
        self.user_pokemon_repo = SqliteUserPokemonRepository(self.db_path)
        self.user_item_repo = SqliteUserItemRepository(self.db_path)
        self.nature_repo = SqliteNatureRepository(self.db_path)
        self.trainer_repo = SqliteTrainerRepository(self.db_path)  # 添加训练家仓库
        self.ability_repo = SqliteAbilityRepository(self.db_path)  # 添加特性定义仓库
        self.pokemon_ability_repo = SqlitePokemonAbilityRepository(self.db_path)  # 添加宝可梦特性关联仓库



        # 2. 初始化 Services (依赖注入逻辑)
        self.nature_service = NatureService(
            nature_repo=self.nature_repo
        )
        self.exp_service = ExpService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            team_repo=self.team_repo,
            move_repo=self.move_repo,
            user_pokemon_repo=self.user_pokemon_repo,
            config=self.config,
            nature_service=self.nature_service
        )
        self.pokemon_service = PokemonService(
            pokemon_repo=self.pokemon_repo,
            move_repo=self.move_repo,
            user_pokemon_repo=self.user_pokemon_repo,
            config=self.config,
            nature_service=self.nature_service,
            exp_service=self.exp_service
        )
        self.user_service = UserService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            item_repo=self.item_repo,
            user_pokemon_repo=self.user_pokemon_repo,
            user_item_repo=self.user_item_repo,
            team_repo=self.team_repo,
            battle_repo=self.battle_repo,
            exp_service=self.exp_service,
            config=self.config
        )
        self.user_pokemon_service = UserPokemonService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            user_pokemon_repo=self.user_pokemon_repo,
            item_repo=self.item_repo,
            pokemon_ability_repo=self.pokemon_ability_repo,  # 注意：这里参数名未变，但传入的是重命名后的仓库
            config=self.config
        )
        self.user_item_service = UserItemService(
            user_item_repo=self.user_item_repo,
            config=self.config
        )
        self.team_service = TeamService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            team_repo=self.team_repo,
            user_pokemon_repo=self.user_pokemon_repo,
            config=self.config
        )

        self.trainer_service = TrainerService(
            trainer_repo=self.trainer_repo,
            pokemon_repo=self.pokemon_repo,
            user_pokemon_repo=self.user_pokemon_repo,
            user_repo=self.user_repo,
            pokemon_service=self.pokemon_service
        )
        self.ability_service = AbilityService(
            ability_repo=self.ability_repo
        )
        self.adventure_service = AdventureService(
            adventure_repo=self.adventure_repo,
            pokemon_repo=self.pokemon_repo,
            team_repo=self.team_repo,
            user_repo=self.user_repo,
            move_repo=self.move_repo,
            battle_repo=self.battle_repo,
            user_pokemon_repo=self.user_pokemon_repo,
            user_item_repo=self.user_item_repo,
            item_repo=self.item_repo,
            pokemon_service=self.pokemon_service,
            pokemon_ability_repo=self.pokemon_ability_repo,
            exp_service=self.exp_service,
            config=self.config
        )
        # 设置冒险服务中的训练家服务引用
        self.adventure_service.set_trainer_service(self.trainer_service)
        self.item_service = ItemService(
            user_repo=self.user_repo,
            user_item_repo=self.user_item_repo,
            item_repo=self.item_repo
        )
        self.shop_service = ShopService(
            user_repo=self.user_repo,
            shop_repo=self.shop_repo,
            user_item_repo=self.user_item_repo
        )
        self.move_service = MoveService(
            move_repo=self.move_repo
        )
        self.evolution_service = EvolutionService(
            user_pokemon_repo=self.user_pokemon_repo,
            pokemon_repo=self.pokemon_repo,
            nature_service=self.nature_service
        )
        self.data_dir = "data"

        self.tmp_dir = os.path.join(self.data_dir, "tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)
        self._clear_tmp_directory()

    def _clear_tmp_directory(self):
        """清空临时目录中的文件"""
        if os.path.exists(self.tmp_dir):
            for filename in os.listdir(self.tmp_dir):
                file_path = os.path.join(self.tmp_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # 删除文件或符号链接
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # 删除子目录及其内容
                except Exception as e:
                    # 如果删除失败，记录错误但不中断操作
                    print(f"删除临时文件 {file_path} 时出错: {e}")
