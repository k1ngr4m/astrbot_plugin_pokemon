from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING

from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin

class UserHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service

    async def register_user(self, event: AstrMessageEvent):
        """注册用户命令"""
        user_id = self.plugin._get_effective_user_id(event)
        nickname = event.get_sender_name() if event.get_sender_name() is not None else user_id
        result = self.user_service.register(user_id, nickname)
        yield event.plain_result(result.message)

    async def checkin(self, event: AstrMessageEvent):
        """签到命令处理器"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return
        result = self.user_service.checkin(user_id)
        if result.success:
            d = result.data
            message = AnswerEnum.USER_CHECKIN_SUCCESS.value.format(
                gold_reward=d["gold_reward"],
                item_name=d["item_reward"],
                item_quantity=d["quantity"],
                new_coins=d["new_coins"]
            )
            yield event.plain_result(message)
        else:
            yield event.plain_result(result.message)
