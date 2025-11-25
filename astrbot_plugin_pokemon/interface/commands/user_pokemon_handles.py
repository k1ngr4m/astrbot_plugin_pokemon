from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING

from ...core.models.pokemon_models import UserPokemonInfo
from ...core.models.user_models import User
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin

class UserPokemonHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service

    async def init_select(self, event: AstrMessageEvent):
        """初始化选择宝可梦"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return
        user:User = result.data
        if user.init_selected:
            yield event.plain_result(AnswerEnum.USER_ALREADY_INITIALIZED_POKEMON.value)
            return

        args = event.message_str.split()
        if len(args) < 2:
            yield event.plain_result(AnswerEnum.POKEMON_INIT_SELECT_USAGE_ERROR.value)
            return
        try:
            pokemon_id = int(args[1])
            if pokemon_id not in (1, 4, 7):
                yield event.plain_result(AnswerEnum.POKEMON_INIT_SELECT_INVALID_POKEMON_ID.value)
                return
        except ValueError:
            yield event.plain_result(AnswerEnum.POKEMON_ID_INVALID.value)
            return

        result = self.user_service.init_select_pokemon(user_id, pokemon_id)
        if result.success:
            yield event.plain_result(
                AnswerEnum.POKEMON_INIT_SELECT_SUCCESS.value.format(pokemon_name=result.data["pokemon_name"])
            )
        else:
            yield event.plain_result(result.message)

    async def view_user_pokemon(self, event: AstrMessageEvent):
        """查看我的宝可梦，支持查看特定宝可梦详细信息"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        args = event.message_str.split()
        if len(args) >= 2:
            if not args[1].isdigit():
                yield event.plain_result(AnswerEnum.POKEMON_ID_INVALID.value)
            result = self.user_service.get_user_specific_pokemon(user_id, int(args[1]))
            if not result.success:
                yield event.plain_result(result.message)
                return
            pokemon_data: UserPokemonInfo = result.data
            # 显示详细信息
            gender_str = {
                "M": "♂️",
                "F": "♀️",
                "N": "⚲"
            }.get(pokemon_data["gender"], "")

            message = f"🔍 宝可梦详细信息：\n\n"
            message += f"{pokemon_data['name']} {gender_str}\n\n"
            message += f"等级: {pokemon_data['level']}\n"
            message += f"经验: {pokemon_data['exp']}\n\n"

            # 实际属性值
            message += "💪 属性值:\n\n"
            message += f"  HP: {pokemon_data['stats']['hp']}\t\n"
            message += f"  攻击: {pokemon_data['stats']['attack']}\t\n"
            message += f"  防御: {pokemon_data['stats']['defense']}\n\n"
            message += f"  特攻: {pokemon_data['stats']['sp_attack']}\t\n"
            message += f"  特防: {pokemon_data['stats']['sp_defense']}\t\n"
            message += f"  速度: {pokemon_data['stats']['speed']}\n\n"

            # 个体值 (IV)
            message += "📊 个体值 (IV):\n\n"
            message += f"  HP: {pokemon_data['ivs']['hp_iv']}/31\t\n"
            message += f"  攻击: {pokemon_data['ivs']['attack_iv']}/31\t\n"
            message += f"  防御: {pokemon_data['ivs']['defense_iv']}/31\n\n"
            message += f"  特攻: {pokemon_data['ivs']['sp_attack_iv']}/31\t\n"
            message += f"  特防: {pokemon_data['ivs']['sp_defense_iv']}/31\t\n"
            message += f"  速度: {pokemon_data['ivs']['speed_iv']}/31\n\n"

            # 努力值 (EV)
            message += "📈 努力值 (EV):\n\n"
            message += f"  HP: {pokemon_data['evs']['hp_ev']}\t\n"
            message += f"  攻击: {pokemon_data['evs']['attack_ev']}\t\n"
            message += f"  防御: {pokemon_data['evs']['defense_ev']}\n\n"
            message += f"  特攻: {pokemon_data['evs']['sp_attack_ev']}\t\n"
            message += f"  特防: {pokemon_data['evs']['sp_defense_ev']}\t\n"
            message += f"  速度: {pokemon_data['evs']['speed_ev']}\n\n"

            message += f"捕获时间: {pokemon_data['caught_time']}"
            yield event.plain_result(message)
        else:
            result = self.user_service.get_user_all_pokemon(user_id)
            yield event.plain_result(result.message)
