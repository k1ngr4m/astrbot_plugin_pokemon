import asyncio
import os

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger, AstrBotConfig
from .astrbot_plugin_pokemon.core.container import GameContainer

from .astrbot_plugin_pokemon.infrastructure.database.migration import run_migrations
from .astrbot_plugin_pokemon.core.services import DataSetupService

from .astrbot_plugin_pokemon.interface.commands.common_handlers import CommonHandlers
from .astrbot_plugin_pokemon.interface.commands.pokemon_handlers import PokemonHandlers
from .astrbot_plugin_pokemon.interface.commands.team_handlers import TeamHandlers
from .astrbot_plugin_pokemon.interface.commands.adventure_handlers import AdventureHandlers
from .astrbot_plugin_pokemon.interface.commands.item_handlers import ItemHandlers
from .astrbot_plugin_pokemon.interface.commands.shop_handlers import ShopHandlers
from .astrbot_plugin_pokemon.interface.commands.user_handlers import UserHandlers
from .astrbot_plugin_pokemon.interface.commands.user_pokemon_handles import UserPokemonHandlers
from .astrbot_plugin_pokemon.interface.commands.evolution_handlers import EvolutionHandlers


class PokemonPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.plugin_id = "astrbot_plugin_pokemon"

        # 1. 基础配置与路径
        self.data_dir = "data"
        self.db_path = os.path.join(self.data_dir, "pokemon.db")

        # 确保目录存在
        os.makedirs(os.path.join(self.data_dir, "tmp"), exist_ok=True)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # 2. 读取配置
        user_config = config.get("user", {})
        adventure_config = config.get("adventure", {})
        self.game_config = {
            "user": {"initial_coins": user_config.get("initial_coins", 200)},
            "adventure": {"cooldown": adventure_config.get("cooldown_seconds", 10)}
        }

        self.web_admin_task = None
        webui_config = config.get("webui", {})
        self.secret_key = webui_config.get("secret_key", "default-secret-key")
        self.port = webui_config.get("port", 7777)

        # 3. 初始化容器
        self.container = GameContainer(str(self.db_path), self.game_config)

        # 4. 兼容性桥接
        self._bridge_compatibility()

        # 5. 初始化 Handlers
        self._init_handlers()

    def _init_handlers(self):
        """负责实例化所有的 Repository, Service 和 Handler"""

        # --- Handlers (注入 Plugin self) ---
        self.common_handlers = CommonHandlers(self, self.container)
        self.user_handlers = UserHandlers(self, self.container)
        self.user_pokemon_handlers = UserPokemonHandlers(self, self.container)
        self.team_handlers = TeamHandlers(self, self.container)
        self.pokemon_handlers = PokemonHandlers(self, self.container)
        self.adventure_handlers = AdventureHandlers(self, self.container)
        self.item_handlers = ItemHandlers(self, self.container)
        self.shop_handlers = ShopHandlers(self, self.container)
        self.evolution_handlers = EvolutionHandlers(self, self.container)

    def _bridge_compatibility(self):
        """
        将容器中的 Service 映射到 self 上，以兼容现有的 Handler 代码。
        现有的 Handler 可能通过 self.plugin.user_service 调用。
        """
        self.pokemon_service = self.container.pokemon_service
        self.user_service = self.container.user_service
        self.user_pokemon_service = self.container.user_pokemon_service
        self.team_service = self.container.team_service
        self.exp_service = self.container.exp_service
        self.adventure_service = self.container.adventure_service
        self.item_service = self.container.item_service
        self.shop_service = self.container.shop_service
        self.move_service = self.container.move_service
        self.trainer_service = self.container.trainer_service  # 添加训练家服务

        self.user_repo = self.container.user_repo
        self.pokemon_repo = self.container.pokemon_repo
        self.team_repo = self.container.team_repo
        self.adventure_repo = self.container.adventure_repo
        self.shop_repo = self.container.shop_repo
        self.item_repo = self.container.item_repo
        self.move_repo = self.container.move_repo
        self.battle_repo = self.container.battle_repo
        self.nature_repo = self.container.nature_repo
        self.trainer_repo = self.container.trainer_repo  # 添加训练家仓库
        self.pokemon_ability_relation_repo = self.container.pokemon_ability_relation_repo  # 添加宝可梦特性关联仓库

    async def initialize(self):
        """
        框架会在插件加载完成后自动 await 调用此方法。
        在这里执行耗时的数据库迁移和初始化。
        """
        logger.info(f"[{self.plugin_id}] 正在初始化数据...")

        # 1. 准备路径
        plugin_root_dir = os.path.dirname(__file__)
        migrations_path = os.path.join(plugin_root_dir, self.plugin_id, "infrastructure", "database", "migrations")

        # 2. 执行数据库迁移
        try:
            run_migrations(self.db_path, migrations_path)
            logger.info(f"[{self.plugin_id}] 数据库迁移完成。")
        except Exception as e:
            logger.error(f"[{self.plugin_id}] 数据库迁移失败: {e}")
            return

        # 3. 初始化核心游戏数据
        try:
            data_setup_service = DataSetupService(
                self.pokemon_repo,
                self.adventure_repo,
                self.shop_repo,
                self.move_repo,
                self.item_repo,
                self.nature_repo,
                self.trainer_repo,  # 添加训练家仓库
                self.container.ability_repo,  # 添加特性仓库
                self.container.pokemon_ability_relation_repo  # 添加宝可梦特性关联仓库
            )
            data_setup_service.setup_initial_data()
            logger.info(f"[{self.plugin_id}] 初始数据检查/写入完成。")
        except Exception as e:
            logger.error(f"[{self.plugin_id}] 初始数据设置失败: {e}")


    # ====================== 指令注册区 ======================

    # ==========注册与初始化==========
    @filter.command("宝可梦注册")
    async def register(self, event: AstrMessageEvent):
        """注册成为宝可梦游戏玩家，开始你的宝可梦之旅"""
        async for r in self.user_handlers.register_user(event):
            yield r

    @filter.command("宝可梦个人资料", alias={"个人资料", "查看状态", "查看个人资料", "status"})
    async def profile(self, event: AstrMessageEvent):
        """查看用户个人资料，包括等级、经验和金币"""
        async for r in self.user_handlers.profile(event):
            yield r

    @filter.command("宝可梦签到")
    async def checkin(self, event: AstrMessageEvent):
        """每日签到，获得金币和道具奖励"""
        async for r in self.user_handlers.checkin(event):
            yield r

    @filter.command("初始选择")
    async def init_select(self, event: AstrMessageEvent):
        """初始化选择宝可梦。用法：初始选择 [宝可梦ID]"""
        async for r in self.user_pokemon_handlers.init_select(event):
            yield r

    # ==========用户资产==========
    @filter.command("宝可梦背包")
    async def view_items(self, event: AstrMessageEvent):
        """查看用户背包中的所有道具"""
        async for r in self.item_handlers.view_items(event):
            yield r

    # ==========宝可梦和队伍管理==========
    @filter.command("我的宝可梦")
    async def view_user_pokemon(self, event: AstrMessageEvent):
        """查看我的宝可梦列表，或使用 /我的宝可梦 <宝可梦ID> 查看特定宝可梦详细信息"""
        async for r in self.user_pokemon_handlers.view_user_pokemon(event):
            yield r

    @filter.command("学习招式")
    async def learn_move(self, event: AstrMessageEvent):
        """学习新招式。用法：/学习招式 [宝可梦ID] [技能ID] [槽位编号]"""
        async for r in self.adventure_handlers.learn_move(event):
            yield r

    @filter.command("查看招式", alias={"招式信息", "技能信息", "move_info"})
    async def view_move_info(self, event: AstrMessageEvent):
        """查看招式详细信息。用法：/查看招式 [招式ID]"""
        async for r in self.pokemon_handlers.view_move_info(event):
            yield r

    @filter.command("宝可梦进化")
    async def evolve_pokemon(self, event: AstrMessageEvent):
        """进化宝可梦。用法：/宝可梦进化 <宝可梦ID>"""
        async for r in self.evolution_handlers.evolve_pokemon(event):
            yield r

    @filter.command("查看进化状态")
    async def check_evolution_status(self, event: AstrMessageEvent):
        """查看宝可梦进化状态。用法：/查看进化状态 <宝可梦ID>"""
        async for r in self.evolution_handlers.check_evolution_status(event):
            yield r

    @filter.command("图鉴", alias={"宝可梦图鉴", "pokedex"})
    async def pokedex(self, event: AstrMessageEvent):
        """查看宝可梦图鉴。用法：/图鉴 (第一页) /图鉴 P+[页码] /图鉴 M+[宝可梦名/ID]"""
        async for r in self.pokemon_handlers.pokedex(event):
            yield r

    # ==========冒险系统==========
    @filter.command("设置队伍")
    async def set_team(self, event: AstrMessageEvent):
        """设置队伍中的宝可梦"""
        async for r in self.team_handlers.set_team(event):
            yield r

    @filter.command("查看队伍")
    async def view_team(self, event: AstrMessageEvent):
        """查看当前队伍配置"""
        async for r in self.team_handlers.view_team(event):
            yield r

    @filter.command("宝可梦恢复", alias={"恢复队伍", "恢复宝可梦", "治疗所有宝可梦", "heal"})
    async def heal_team(self, event: AstrMessageEvent):
        """恢复队伍中所有宝可梦的生命值和状态，花费1000金币"""
        async for r in self.team_handlers.heal_team(event):
            yield r

    @filter.command("查看区域")
    async def view_locations(self, event: AstrMessageEvent):
        """查看所有可冒险的区域"""
        async for r in self.adventure_handlers.view_locations(event):
            yield r

    @filter.command("冒险")
    async def adventure(self, event: AstrMessageEvent):
        """在指定区域进行冒险"""
        async for r in self.adventure_handlers.adventure(event):
            yield r

    @filter.command("战斗")
    async def battle(self, event: AstrMessageEvent):
        """与当前遇到的野生宝可梦战斗"""
        async for r in self.adventure_handlers.battle(event):
            yield r

    @filter.command("捕捉")
    async def catch_pokemon(self, event: AstrMessageEvent):
        """捕捉当前遇到的野生宝可梦"""
        async for r in self.adventure_handlers.catch_pokemon(event):
            yield r

    @filter.command("逃跑")
    async def run(self, event: AstrMessageEvent):
        """逃跑离开当前遇到的野生宝可梦"""
        async for r in self.adventure_handlers.run(event):
            yield r

    @filter.command("查看战斗")
    async def view_battle_log(self, event: AstrMessageEvent):
        """查看战斗日志。用法：/查看战斗 <日志ID>"""
        async for r in self.adventure_handlers.view_battle_log(event):
            yield r

    # ==========商店系统==========
    @filter.command("宝可梦商店")
    async def view_shop(self, event: AstrMessageEvent):
        """查看商店中的所有商品"""
        async for r in self.shop_handlers.view_shop(event):
            yield r

    @filter.command("宝可梦商店购买")
    async def purchase_item(self, event: AstrMessageEvent):
        """购买商店中的商品"""
        async for r in self.shop_handlers.purchase_item(event):
            yield r

    # ==========通用帮助==========
    @filter.command("宝可梦帮助", alias={"宝可梦菜单", "菜单"})
    async def pokemon_help(self, event: AstrMessageEvent):
        """查看宝可梦游戏的帮助信息和所有可用命令"""
        async for r in self.common_handlers.pokemon_help(event):
            yield r

    # @filter.permission_type(PermissionType.ADMIN)
    @filter.command("开启宝可梦后台管理")
    async def start_admin(self, event: AstrMessageEvent):
        """[管理员] 启动Web后台管理服务器"""
        async for r in self.common_handlers.start_admin(event):
            yield r

    # @filter.permission_type(PermissionType.ADMIN)
    @filter.command("关闭宝可梦后台管理")
    async def stop_admin(self, event: AstrMessageEvent):
        """[管理员] 关闭Web后台管理服务器"""
        async for r in self.common_handlers.stop_admin(event):
            yield r

    async def _check_port_active(self):
        """验证端口是否实际已激活"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", self.port),
                timeout=1
            )
            writer.close()
            return True
        except:
            return False

    async def terminate(self):
        """可选择实现异步的插件销毁方法"""
        pass