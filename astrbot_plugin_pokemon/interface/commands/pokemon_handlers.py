from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class PokemonHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.pokemon_service = container.pokemon_service
        self.user_pokemon_service = container.user_pokemon_service
        self.pokemon_repo = container.pokemon_repo

    def _show_pokedex_detail(self, event, user_id, query):
        """
        显示单只宝可梦的图鉴详情
        :param event: 事件对象
        :param user_id: 用户ID
        :param query: 查询参数（宝可梦ID或名称）
        """
        # 先尝试按ID查找
        species_info = None
        if query.isdigit():
            species_info = self.pokemon_service.get_pokemon_by_id(int(query))
        else:
            # 按名称查找
            species_info = self.pokemon_service.get_pokemon_by_name(query)

        if not species_info:
            event.plain_result(f"❌ 未找到宝可梦: {query}")
            return

        # 检查用户是否已遇到或捕捉过该宝可梦
        user_progress = self.user_pokemon_service.get_user_pokedex_ids(user_id)
        if user_progress.success:
            caught_set = user_progress['caught']
            seen_set = user_progress['seen']
        else:
            event.plain_result(user_progress.message)
            return

        # 构建图鉴详情
        if species_info.id not in seen_set:
            # 用户未遇到过该宝可梦，显示未知信息
            detail_text = f"🔍 图鉴信息: #{species_info.id:04d} ???"
            detail_text += f"\n该宝可梦的详细信息暂未解锁。"
            detail_text += f"\n请先在野外遇到该宝可梦以解锁图鉴信息。"
        else:
            # 用户已遇到过，显示基础信息
            detail_text = f"📖 图鉴信息: #{species_info.id:04d} {species_info.name_zh}"
            detail_text += f"\n类型: {'/'.join(self.pokemon_repo.get_pokemon_types(species_info.id))}"
            detail_text += f"\n身高: {species_info.height}m | 体重: {species_info.weight}kg"
            detail_text += f"\n种族值: HP:{species_info.base_stats.base_hp} "
            detail_text += f"攻击:{species_info.base_stats.base_attack} "
            detail_text += f"防御:{species_info.base_stats.base_defense} "
            detail_text += f"特攻:{species_info.base_stats.base_sp_attack} "
            detail_text += f"特防:{species_info.base_stats.base_sp_defense} "
            detail_text += f"速度:{species_info.base_stats.base_speed}"
            detail_text += f"\n描述: {species_info.description}"

            if species_info.id in caught_set:
                detail_text += f"\n✅ 状态: 已捕捉"
            else:
                detail_text += f"\n👁️ 状态: 已遇见"

        event.plain_result(detail_text)

    async def pokedex(self, event: AstrMessageEvent):
        """
        查询图鉴
        指令: /图鉴 [页码 | 宝可梦名]
        """
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        # 获取查询参数
        args = event.message_str.split()
        # 移除指令前缀（如"/图鉴"），只保留参数部分
        if len(args) > 1:
            query = ' '.join(args[1:]).strip()
        else:
            query = ''

        # 情况 A: 用户输入了数字，视为页码
        if query.isdigit():
            page = int(query)
            # 调用 Service 获取列表视图
            result_text = self.plugin.container.pokemon_service.get_pokedex_view(user_id, page)
            yield event.plain_result(result_text)
            return

        # 情况 B: 用户输入了名字，视为查询详情
        if query:
            # 这里调用现有的查询逻辑，但需要增加一个判断：
            # 如果用户没【遇见】过该宝可梦，不允许查看详细数据
            # 通常图鉴逻辑是：未遇到显示"数据未知"，已遇到显示基础信息，已捕捉显示全部信息。
            self._show_pokedex_detail(event, user_id, query)
            return

        # 情况 C: 默认显示第一页
        result_text = self.plugin.container.pokemon_service.get_pokedex_view(user_id, 1)
        yield event.plain_result(result_text)