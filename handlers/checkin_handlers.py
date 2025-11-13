from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class CheckinHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.checkin_service = plugin.checkin_service

    async def checkin(self, event: AstrMessageEvent):
        """签到命令处理器"""
        user_id = self.plugin._get_effective_user_id(event)

        result = self.checkin_service.checkin(user_id)

        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(result["message"])