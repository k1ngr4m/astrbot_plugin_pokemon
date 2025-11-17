from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING
from ..core.answer.answer_enum import AnswerEnum

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class UserHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service

    async def register_user(self, event: AstrMessageEvent):
        """注册用户命令"""
        user_id = self.plugin._get_effective_user_id(event)
        nickname = event.get_sender_name() if event.get_sender_name() is not None else user_id

        result = self.user_service.register(user_id, nickname)

        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(result["message"])

    async def checkin(self, event: AstrMessageEvent):
        """签到命令处理器"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)
        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        result = self.user_service.checkin(user_id)

        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(result["message"])