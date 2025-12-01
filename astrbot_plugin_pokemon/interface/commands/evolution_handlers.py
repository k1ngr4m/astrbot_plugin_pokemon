from typing import TYPE_CHECKING

from astrbot.api.event import AstrMessageEvent
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.interface.response.answer_enum import AnswerEnum
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer


class EvolutionHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        # 提取常用 Service，减少 self.plugin.xxx 的调用链长度
        self.user_service = container.user_service
        self.evolution_service = container.evolution_service
        self.user_pokemon_service = container.user_pokemon_service

    async def evolve_pokemon(self, event: AstrMessageEvent):
        """处理宝可梦进化指令"""
        user_id = userid_to_base32(event.get_sender_id())

        # 统一处理注册检查
        check_res = self.user_service.check_user_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        # 解析参数
        args = event.message_str.split()
        if len(args) != 2:
            yield event.plain_result("❌ 格式错误！正确格式: /宝可梦进化 <宝可梦ID>")
            return

        try:
            pokemon_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 宝可梦ID必须是数字")
            return

        # 执行进化
        result = self.evolution_service.evolve_pokemon(user_id, pokemon_id)

        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(result["message"])

    async def check_evolution_status(self, event: AstrMessageEvent):
        """检查宝可梦进化状态"""
        user_id = userid_to_base32(event.get_sender_id())

        # 统一处理注册检查
        check_res = self.user_service.check_user_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        # 解析参数
        args = event.message_str.split()
        if len(args) != 2:
            yield event.plain_result("❌ 格式错误！正确格式: /查看进化状态 <宝可梦ID>")
            return

        try:
            pokemon_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 宝可梦ID必须是数字")
            return

        # 检查进化状态
        result = self.evolution_service.check_evolution_status(user_id, pokemon_id)

        yield event.plain_result(result["message"])