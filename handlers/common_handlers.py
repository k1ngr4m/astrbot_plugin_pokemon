from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING
from ..core.answer.answer_enum import AnswerEnum
from ..core.utils import userid_to_base32

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class CommonHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service

    async def init_select(self, event: AstrMessageEvent):
        """初始化选择宝可梦"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))

        user = self.plugin.user_repo.get_by_id(user_id)
        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        if user.init_selected:
            yield event.plain_result(AnswerEnum.USER_ALREADY_INITIALIZED_POKEMON.value)
            return

        args = event.message_str.split(" ")

        if len(args) < 2:
            yield event.plain_result(AnswerEnum.POKEMON_INIT_SELECT_USAGE_ERROR.value)
            return
        try:
            pokemon_id = int(args[1])

            if pokemon_id not in (1, 4, 7):
                yield event.plain_result("❌ 请从妙蛙种子1、小火龙4、杰尼龟7中选择。")
                return

        except ValueError:
            yield event.plain_result(AnswerEnum.POKEMON_ID_INVALID.value)
            return

        result = self.user_service.init_select_pokemon(user_id, pokemon_id)

        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(result["message"])

