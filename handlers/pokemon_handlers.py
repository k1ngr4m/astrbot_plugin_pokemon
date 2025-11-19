from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING
from ..core.answer.answer_enum import AnswerEnum
from ..core.utils import userid_to_base32

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class PokemonHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.team_service = plugin.team_service
        self.pokemon_service = plugin.pokemon_service

    async def my_pokemon(self, event: AstrMessageEvent):
        """查看我的宝可梦，支持查看特定宝可梦详细信息"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        args = event.message_str.split(" ")

        if len(args) >= 2:
            if not args[1].isdigit():
                yield event.plain_result(f"❌ 宝可梦ID {args[1]} 格式不正确（仅支持数字ID）。")

            result = self.user_service.get_user_specific_pokemon(user_id, int(args[1]))
            yield event.plain_result(result["message"])

        else:
            result = self.user_service.get_user_all_pokemon(user_id)
            yield event.plain_result(result["message"])
