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

    def _show_pokedex_detail(self, user_id, query):
        """
        显示单只宝可梦的图鉴详情
        :param user_id: 用户ID
        :param query: 查询参数（宝可梦ID或名称）
        :return: 图鉴详情文本或错误消息
        """
        # 先尝试按ID查找
        if query.isdigit():
            species_info = self.pokemon_service.get_pokemon_by_id(int(query))
        else:
            # 按名称查找
            species_info = self.pokemon_service.get_pokemon_by_name(query)

        if not species_info:
            message = f"❌ 未找到宝可梦: {query}"
            return message

        # 检查用户是否已遇到或捕捉过该宝可梦
        user_progress = self.user_pokemon_service.get_user_pokedex_ids(user_id)
        if user_progress.success:
            d = user_progress.data
            caught_set = d['caught']
            seen_set = d['seen']
        else:
            return user_progress.message

        # 构建图鉴详情
        if species_info.id not in seen_set:
            # 用户未遇到过该宝可梦，显示未知信息
            detail_text = f"🔍 图鉴信息: #{species_info.id:04d} ???\n\n"
            detail_text += f"该宝可梦的详细信息暂未解锁。\n\n"
            detail_text += f"请先在野外遇到该宝可梦以解锁图鉴信息。"
        else:
            # 用户已遇到过，显示基础信息
            detail_text = f"📖 图鉴信息: #{species_info.id:04d} {species_info.name_zh}\n\n"
            detail_text += f"类型: {'/'.join(self.pokemon_repo.get_pokemon_types(species_info.id))}\n\n"
            detail_text += f"身高: {species_info.height}m | 体重: {species_info.weight}kg\n\n"
            detail_text += f"种族值: \n\n"
            detail_text += f"HP:{species_info.base_stats.base_hp}\n"
            detail_text += f"攻击:{species_info.base_stats.base_attack}\n"
            detail_text += f"防御:{species_info.base_stats.base_defense}\n\n"
            detail_text += f"特攻:{species_info.base_stats.base_sp_attack}\n"
            detail_text += f"特防:{species_info.base_stats.base_sp_defense}\n"
            detail_text += f"速度:{species_info.base_stats.base_speed}\n\n"
            detail_text += f"描述: {species_info.description}\n\n"

            if species_info.id in caught_set:
                detail_text += f"\n✅ 状态: 已捕捉"
            else:
                detail_text += f"\n👁️ 状态: 已遇见"
        return detail_text

    async def pokedex(self, event: AstrMessageEvent):
        """
        查询图鉴
        指令1: /图鉴 ：查看第一页图鉴
        指令2: /图鉴 P+[页码] ：查看第P页图鉴
        指令3: /图鉴 M+[宝可梦ID/宝可梦名] ：查看宝可梦图鉴详情
        """
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        # 获取查询参数
        args = event.message_str.split()
        if len(args) > 1:
            query = ' '.join(args[1:]).strip()
        else:
            query = ''

        # 情况 A: 检查是否为P页码格式
        if query.upper().startswith('P'):
            try:
                page_str = query[1:]  # 去掉"P"前缀
                page = int(page_str)
                if page <= 0:
                    yield event.plain_result("页码必须是正整数！")
                    return
                # 调用 Service 获取列表视图
                result_text = self.pokemon_service.get_pokedex_view(user_id, page)
                yield event.plain_result(result_text)
                return
            except ValueError:
                yield event.plain_result("页码格式错误！请使用 /图鉴 P+页码 格式。")
                return

        # 情况 B: 检查是否为M+查询格式
        elif query.upper().startswith('M'):
            query_param = query[1:]  # 去掉"M"前缀
            if not query_param:
                yield event.plain_result("查询参数不能为空！请使用 /图鉴 M+宝可梦ID或名称 格式。")
                return
            detail_text = self._show_pokedex_detail(user_id, query_param)
            if isinstance(detail_text, str):
                yield event.plain_result(detail_text)
            else:
                yield event.plain_result(detail_text.message)
            return

        # 情况 C: 如果是纯数字，视为页码
        elif query.isdigit():
            page = int(query)
            if page <= 0:
                yield event.plain_result("页码必须是正整数！")
                return
            # 调用 Service 获取列表视图
            result_text = self.pokemon_service.get_pokedex_view(user_id, page)
            yield event.plain_result(result_text)
            return

        # 情况 D: 其他非空参数视为宝可梦名称或ID查询
        elif query:
            detail_text = self._show_pokedex_detail(user_id, query)
            if isinstance(detail_text, str):
                yield event.plain_result(detail_text)
            else:
                yield event.plain_result(detail_text.message)
            return

        # 情况 E: 默认显示第一页
        result_text = self.pokemon_service.get_pokedex_view(user_id, 1)
        yield event.plain_result(result_text)