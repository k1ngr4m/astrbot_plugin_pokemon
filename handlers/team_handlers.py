from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING
from ..core.answer.answer_enum import AnswerEnum
from ..core.utils import userid_to_base32

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class TeamHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.team_service = plugin.team_service

    async def set_team(self, event: AstrMessageEvent):
        """设置队伍中的宝可梦"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result(AnswerEnum.TEAM_SET_USAGE_ERROR.value)
            return

        # 获取用户输入的宝可梦ID列表（跳过命令本身）
        pokemon_ids = args[1:]

        if len(pokemon_ids) > 6:
            yield event.plain_result(AnswerEnum.TEAM_SET_MAX_POKEMON.value)
            return

        if len(pokemon_ids) == 0:
            yield event.plain_result(AnswerEnum.TEAM_SET_MIN_POKEMON.value)
            return

        # 验证每个ID格式（仅支持数字ID）
        for id in pokemon_ids:
            if not id.isdigit():
                yield event.plain_result(f"❌ 宝可梦ID {id} 格式不正确（仅支持数字ID）。")
                return

        result = self.team_service.set_team_pokemon(user_id, [int(id) for id in pokemon_ids])

        if result["success"]:
            yield event.plain_result(result['message'])
        else:
            yield event.plain_result(result['message'])

    async def view_team(self, event: AstrMessageEvent):
        """查看当前队伍配置"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        result = self.team_service.get_user_team(user_id)

        if not result["success"] or not result["team"]:
            yield event.plain_result(result["message"])
            return

        team:list = result["team"]

        # 显示队伍信息
        message = "🏆 当前队伍配置：\n\n"
        # 显示队伍列表
        if team:
            message += f"\n队伍成员 ({len(team)}/6)：\n"
            for i, pokemon_data in enumerate(team, 1):
                # 从pokemon_data中提取信息
                id = pokemon_data.get('id')
                name = pokemon_data.get('name')
                level = pokemon_data.get('level', 1)
                hp = pokemon_data.get('hp', 0)

                # 标记出战宝可梦（第一个是出战的）
                marker = " ⭐" if i == 1 else ""
                message += f"  {i}. {name}{marker}\n"
                message += f"     ID: {id} | 等级: {level} | HP: {hp}\n"
        else:
            message += "\n队伍成员 (0/6)：暂无\n"

        yield event.plain_result(message)
