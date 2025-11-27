from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING

from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class ItemHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.item_service = container.item_service

    async def view_items(self, event: AstrMessageEvent):
        """查看用户道具命令处理器"""
        user_id = userid_to_base32(event.get_sender_id())
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        result = self.item_service.get_user_items(user_id)
        formatted_message = self.item_service.format_items_list(result)

        yield event.plain_result(formatted_message)