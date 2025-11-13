from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class ItemHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.item_service = plugin.item_service

    async def view_items(self, event: AstrMessageEvent):
        """查看用户道具命令处理器"""
        user_id = self.plugin._get_effective_user_id(event)

        result = self.item_service.get_user_items(user_id)
        formatted_message = self.item_service.format_items_list(result)

        yield event.plain_result(formatted_message)