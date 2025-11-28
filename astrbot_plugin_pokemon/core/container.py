from ..core.services.user_pokemon_service import UserPokemonService
from ..core.services.pokemon_service import PokemonService
from ..core.services.team_service import TeamService
from ..core.services.adventure_service import AdventureService
from ..core.services.exp_service import ExpService
from ..core.services.user_service import UserService
from ..core.services.item_service import ItemService
from ..core.services.shop_service import ShopService
from ..core.services.move_service import MoveService

from ..infrastructure.repositories.sqlite_item_repo import SqliteItemRepository
from ..infrastructure.repositories.sqlite_pokemon_repo import SqlitePokemonRepository
from ..infrastructure.repositories.sqlite_team_repo import SqliteTeamRepository
from ..infrastructure.repositories.sqlite_user_repo import SqliteUserRepository
from ..infrastructure.repositories.sqlite_adventure_repo import SqliteAdventureRepository
from ..infrastructure.repositories.sqlite_battle_repo import SqliteBattleRepository
from ..infrastructure.repositories.sqlite_shop_repo import SqliteShopRepository
from ..infrastructure.repositories.sqlite_move_repo import SqliteMoveRepository
from ..infrastructure.repositories.sqlite_user_pokemon_repo import SqliteUserPokemonRepository


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



        # 2. 初始化 Services (依赖注入逻辑)
        self.pokemon_service = PokemonService(
            pokemon_repo=self.pokemon_repo, user_pokemon_repo=self.user_pokemon_repo, move_repo=self.move_repo, config=self.config
        )
        self.user_service = UserService(
            user_repo=self.user_repo, pokemon_repo=self.pokemon_repo, item_repo=self.item_repo,
            pokemon_service=self.pokemon_service, config=self.config
        )
        self.user_pokemon_service = UserPokemonService(
            user_repo=self.user_repo, pokemon_repo=self.pokemon_repo,
            user_pokemon_repo=self.user_pokemon_repo, item_repo=self.item_repo,
            pokemon_service=self.pokemon_service, config=self.config
        )
        self.team_service = TeamService(
            user_repo=self.user_repo, pokemon_repo=self.pokemon_repo, team_repo=self.team_repo, config=self.config
        )
        self.exp_service = ExpService(
            user_repo=self.user_repo, pokemon_repo=self.pokemon_repo, team_repo=self.team_repo,
            move_repo=self.move_repo, config=self.config
        )
        self.adventure_service = AdventureService(
            adventure_repo=self.adventure_repo, pokemon_repo=self.pokemon_repo, team_repo=self.team_repo,
            pokemon_service=self.pokemon_service, user_repo=self.user_repo, exp_service=self.exp_service,
            config=self.config, move_repo=self.move_repo, battle_repo=self.battle_repo
        )
        self.item_service = ItemService(
            user_repo=self.user_repo
        )
        self.shop_service = ShopService(
            user_repo=self.user_repo, shop_repo=self.shop_repo
        )
        self.move_service = MoveService(
            move_repo=self.move_repo
        )