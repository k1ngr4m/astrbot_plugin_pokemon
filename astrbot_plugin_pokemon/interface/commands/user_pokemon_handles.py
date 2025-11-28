from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING, List

from ...core.models.pokemon_models import UserPokemonInfo
from ...core.models.user_models import User
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class UserPokemonHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.user_service = container.user_service
        self.pokemon_service = container.pokemon_service
        self.user_pokemon_service = container.user_pokemon_service

    async def init_select(self, event: AstrMessageEvent):
        """初始化选择宝可梦"""
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return
        user:User = result.data

        # 检查用户是否已经初始化选择宝可梦
        if user.init_selected:
            yield event.plain_result(AnswerEnum.USER_ALREADY_INITIALIZED_POKEMON.value)
            return

        # 解析宝可梦ID
        args = event.message_str.split()
        # 检查参数数量是否正确
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

        # 检查宝可梦是否存在
        pokemon_info = self.pokemon_service.get_pokemon_by_id(pokemon_id)
        if not pokemon_info:
            yield event.plain_result(AnswerEnum.POKEMON_NOT_FOUND.value)
            return

        new_pokemon = self.pokemon_service.create_single_pokemon(pokemon_id, 1, 1)
        if not new_pokemon.success:
            yield event.plain_result(new_pokemon.message)
            return

        result = self.user_pokemon_service.init_select_pokemon(user_id, new_pokemon.data)
        if result.success:
            yield event.plain_result(
                AnswerEnum.POKEMON_INIT_SELECT_SUCCESS.value.format(
                    pokemon_name=result.data["pokemon_name"],
                    pokemon_id=result.data["pokemon_id"]
                )
            )
        else:
            yield event.plain_result(result.message)

    async def view_user_pokemon(self, event: AstrMessageEvent):
        """查看我的宝可梦，支持查看特定宝可梦详细信息"""
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        args = event.message_str.split()
        if len(args) >= 2:
            if not args[1].isdigit():
                yield event.plain_result(AnswerEnum.POKEMON_ID_INVALID.value)
            result = self.user_pokemon_service.get_user_pokemon_by_id(user_id, int(args[1]))
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

            # 招式信息
            message += "⚔️ 招式:\n\n"
            moves = pokemon_data['moves']
            move_names = []

            # 获取招式1名称
            if moves['move1_id']:
                move_info = self.plugin.move_repo.get_move_by_id(moves['move1_id'])
                move_name = move_info['name_zh'] if move_info else f"技能{moves['move1_id']}"
                move_names.append(f"  1. {move_name}")
            else:
                move_names.append("  1. (空)")

            # 获取招式2名称
            if moves['move2_id']:
                move_info = self.plugin.move_repo.get_move_by_id(moves['move2_id'])
                move_name = move_info['name_zh'] if move_info else f"技能{moves['move2_id']}"
                move_names.append(f"  2. {move_name}")
            else:
                move_names.append("  2. (空)")

            # 获取招式3名称
            if moves['move3_id']:
                move_info = self.plugin.move_repo.get_move_by_id(moves['move3_id'])
                move_name = move_info['name_zh'] if move_info else f"技能{moves['move3_id']}"
                move_names.append(f"  3. {move_name}")
            else:
                move_names.append("  3. (空)")

            # 获取招式4名称
            if moves['move4_id']:
                move_info = self.plugin.move_repo.get_move_by_id(moves['move4_id'])
                move_name = move_info['name_zh'] if move_info else f"技能{moves['move4_id']}"
                move_names.append(f"  4. {move_name}")
            else:
                move_names.append("  4. (空)")

            message += "\n".join(move_names) + "\n\n"

            message += f"捕获时间: {pokemon_data['caught_time']}"
            yield event.plain_result(message)
        else:
            result = self.user_pokemon_service.get_user_all_pokemon(user_id)
            if not result.success:
                yield event.plain_result(result.message)
                return
            user_pokemon_list:List[UserPokemonInfo] = result.data
            # 组织显示信息
            message = f"🌟 您拥有 {len(user_pokemon_list)} 只宝可梦：\n\n"
            for i, pokemon in enumerate(user_pokemon_list, 1):
                gender_str = {
                    "M": "♂️",
                    "F": "♀️",
                    "N": "⚲"
                }.get(pokemon.gender, "")

                message += f"{i}. {pokemon.name} {gender_str}\n"
                message += f"   ID：{pokemon.id} | 等级: {pokemon.level} | HP: {pokemon.stats['hp']}\n"

            message += f"\n您可以使用 /我的宝可梦 <宝可梦ID> 来查看特定宝可梦的详细信息。"
            yield event.plain_result(message)
