from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import PokemonPlugin

async def register_user(self: "PokemonPlugin", event: AstrMessageEvent):
    """注册用户命令"""
    user_id = self._get_effective_user_id(event)
    nickname = event.get_sender_name() if event.get_sender_name() is not None else user_id
    if result := self.user_service.register(user_id, nickname):
        yield event.plain_result(result["message"])
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")