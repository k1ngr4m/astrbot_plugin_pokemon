from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING
from ..core.answer.answer_enum import AnswerEnum

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class CommonHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service

    async def register_user(self, event: AstrMessageEvent):
        """注册用户命令"""
        user_id = self.plugin._get_effective_user_id(event)
        nickname = event.get_sender_name() if event.get_sender_name() is not None else user_id
        if result := self.user_service.register(user_id, nickname):
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result("❌ 出错啦！请稍后再试。")

    async def init_select(self, event: AstrMessageEvent):
        """初始化选择宝可梦"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)
        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return
        if user.init_selected:
            yield event.plain_result("❌ 用户已初始化选择宝可梦")
            return

        args = event.message_str.split(" ")

        if len(args) < 2:
            yield event.plain_result("❌ 请输入宝可梦ID。用法：初始选择 <宝可梦ID>")
            return
        try:
            pokemon_id = int(args[1])

            if pokemon_id not in (1, 4, 7):
                yield event.plain_result("❌ 请从妙蛙种子1、小火龙4、杰尼龟7中选择。")
                return
        except ValueError:
            yield event.plain_result("❌ 请输入正确的宝可梦ID。")
            return

        result = self.user_service.init_select_pokemon(user_id, pokemon_id)

        if result["success"]:
            yield event.plain_result(f"✅ {result['message']}")
        else:
            yield event.plain_result(f"❌ {result['message']}")

