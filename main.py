import os

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .core.database.migration import run_migrations
from .core.repositories.sqlite_pokemon_repo import SqlitePokemonRepository
from .core.repositories.sqlite_team_repo import SqliteTeamRepository
from .core.repositories.sqlite_user_repo import SqliteUserRepository
from .core.repositories.sqlite_area_repo import SqliteAreaRepository
from .core.repositories.sqlite_shop_repo import SqliteShopRepository
from .core.services.data_setup_service import DataSetupService
from .core.services.pokemon_service import PokemonService
from .core.services.team_service import TeamService
from .core.services.area_service import AreaService
from .core.services.battle_service import BattleService
from .core.services.exp_service import ExpService
from .handlers.common_handlers import CommonHandlers
from .handlers.pokemon_handlers import PokemonHandlers
from .handlers.team_handlers import TeamHandlers
from .handlers.area_handlers import AreaHandlers
from .handlers.battle_handlers import BattleHandlers
from .handlers.checkin_handlers import CheckinHandlers
from .handlers.item_handlers import ItemHandlers
from .handlers.catch_handlers import CatchHandlers
from .handlers.shop_handlers import ShopHandlers

from .core.services.user_service import UserService
from .core.services.checkin_service import CheckinService
from .core.services.item_service import ItemService
from .core.services.shop_service import ShopService


class PokemonPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

        # 插件ID
        self.plugin_id = "astrbot_plugin_pokemon"

        # --- 1.1. 数据与临时文件路径管理 ---
        try:
            # 优先使用框架提供的 get_data_dir 方法
            self.data_dir = self.context.get_data_dir(self.plugin_id)
        except (AttributeError, TypeError):
            # 如果方法不存在或调用失败，则回退到旧的硬编码路径
            logger.warning(f"无法使用 self.context.get_data_dir('{self.plugin_id}'), 将回退到旧的 'data/' 目录。")
            self.data_dir = "data"

        self.tmp_dir = os.path.join(self.data_dir, "tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)

        db_path = os.path.join(self.data_dir, "pokemon.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # --- 1.2. 配置数据完整性检查注释 ---
        # 以下配置项必须在此处从 AstrBotConfig 中提取并放入 game_config，
        # 以确保所有服务在接收 game_config 时能够正确读取配置值
        #
        # 配置数据流：_conf_schema.json → AstrBotConfig (config) → game_config → 各个服务
        #
        # 从框架读取嵌套配置
        # 注意：框架会自动解析 _conf_schema.json 中的嵌套对象
        self.game_config = {}

        # 初始化数据库模式
        plugin_root_dir = os.path.dirname(__file__)
        migrations_path = os.path.join(plugin_root_dir, "core", "database", "migrations")
        print(migrations_path)
        run_migrations(db_path, migrations_path)

        # --- 2. 组合根：实例化所有仓储层 ---
        self.user_repo = SqliteUserRepository(db_path)
        self.pokemon_repo = SqlitePokemonRepository(db_path)
        self.team_repo = SqliteTeamRepository(db_path)
        self.area_repo = SqliteAreaRepository(db_path)
        self.shop_repo = SqliteShopRepository(db_path)


        # --- 3. 组合根：实例化所有服务层，并注入依赖 ---
        # 3.1 核心服务必须在效果管理器之前实例化，以解决依赖问题

        # 3.3 实例化其他核心服务
        self.user_service = UserService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            config=self.game_config
        )

        self.team_service = TeamService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            team_repo=self.team_repo,
            config=self.game_config
        )

        self.pokemon_service = PokemonService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            team_repo=self.team_repo,
            config=self.game_config
        )
        self.area_service = AreaService(
            area_repo=self.area_repo,
            pokemon_repo=self.pokemon_repo,
            user_repo=self.user_repo,
            config=self.game_config
        )
        self.exp_service = ExpService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            team_repo=self.team_repo,
            config=self.game_config
        )

        self.battle_service = BattleService(
            user_repo=self.user_repo,
            pokemon_repo=self.pokemon_repo,
            team_repo=self.team_repo,
            config=self.game_config,
            exp_service=self.exp_service
        )
        self.checkin_service = CheckinService(
            user_repo=self.user_repo
        )
        self.item_service = ItemService(
            user_repo=self.user_repo
        )
        self.shop_service = ShopService(
            user_repo=self.user_repo,
            shop_repo=self.shop_repo
        )
        self.common_handlers = CommonHandlers(self)
        self.team_handlers = TeamHandlers(self)
        self.pokemon_handlers = PokemonHandlers(self)
        self.area_handlers = AreaHandlers(self)
        self.battle_handlers = BattleHandlers(self)
        self.checkin_handlers = CheckinHandlers(self)
        self.item_handlers = ItemHandlers(self)
        self.catch_handlers = CatchHandlers(self)
        self.shop_handlers = ShopHandlers(self)
        # --- 4. 启动后台任务 ---

        # --- 5. 初始化核心游戏数据 ---
        data_setup_service = DataSetupService(self.pokemon_repo, self.area_repo, self.shop_repo)
        data_setup_service.setup_initial_data()

        # 管理员扮演功能
        self.impersonation_map = {}

        # 冒险冷却时间管理（默认60秒）
        self.adventure_cooldown = 60
        self._last_adventure_time = {}

    def _get_effective_user_id(self, event: AstrMessageEvent):
        """获取在当前上下文中应当作为指令执行者的用户ID。
        - 默认返回消息发送者ID
        - 若发送者是管理员且已开启代理，则返回被代理用户ID
        注意：仅在非管理员指令中调用该方法；管理员指令应使用真实管理员ID。
        """
        admin_id = event.get_sender_id()
        return self.impersonation_map.get(admin_id, admin_id)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    @filter.command("宝可梦注册")
    async def register(self, event: AstrMessageEvent):
        """注册成为宝可梦游戏玩家，开始你的宝可梦之旅"""
        async for r in self.common_handlers.register_user(event):
            yield r

    @filter.command("宝可梦签到")
    async def checkin(self, event: AstrMessageEvent):
        """每日签到，获得金币和道具奖励"""
        async for r in self.checkin_handlers.checkin(event):
            yield r

    @filter.command("初始选择")
    async def init_select(self, event: AstrMessageEvent):
        """初始化选择宝可梦。用法：初始选择 <宝可梦ID>"""
        async for r in self.common_handlers.init_select(event):
            yield r

    @filter.command("我的宝可梦")
    async def my_pokemon(self, event: AstrMessageEvent):
        """查看我的宝可梦列表，或使用 /我的宝可梦 <短码> 查看特定宝可梦详细信息"""
        async for r in self.pokemon_handlers.my_pokemon(event):
            yield r

    @filter.command("设置队伍")
    async def set_team(self, event: AstrMessageEvent):
        """设置队伍中的宝可梦，最多6只宝可梦，第一个为出战宝可梦"""
        async for r in self.team_handlers.set_team(event):
            yield r

    @filter.command("查看队伍")
    async def view_team(self, event: AstrMessageEvent):
        """查看当前队伍配置"""
        async for r in self.team_handlers.view_team(event):
            yield r

    @filter.command("查看区域")
    async def view_areas(self, event: AstrMessageEvent):
        """查看所有可冒险的区域"""
        async for r in self.area_handlers.view_areas(event):
            yield r

    @filter.command("冒险")
    async def adventure(self, event: AstrMessageEvent):
        """在指定区域进行冒险"""
        async for r in self.area_handlers.adventure(event):
            yield r

    @filter.command("战斗")
    async def battle(self, event: AstrMessageEvent):
        """与当前遇到的野生宝可梦战斗"""
        async for r in self.battle_handlers.battle(event):
            yield r

    @filter.command("捕捉")
    async def catch_pokemon(self, event: AstrMessageEvent):
        """捕捉当前遇到的野生宝可梦"""
        async for r in self.catch_handlers.catch_pokemon(event):
            yield r

    @filter.command("宝可梦背包")
    async def view_items(self, event: AstrMessageEvent):
        """查看用户背包中的所有道具"""
        async for r in self.item_handlers.view_items(event):
            yield r

    @filter.command("商店")
    async def view_shop(self, event: AstrMessageEvent):
        """查看商店中的所有商品"""
        async for r in self.shop_handlers.view_shop(event):
            yield r

    @filter.command("商店购买")
    async def purchase_item(self, event: AstrMessageEvent):
        """购买商店中的商品"""
        async for r in self.shop_handlers.purchase_item(event):
            yield r

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
