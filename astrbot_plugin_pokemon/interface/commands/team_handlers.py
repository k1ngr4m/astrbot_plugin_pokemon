from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING, List

from ...core.models.pokemon_models import UserPokemonInfo
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class TeamHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.user_service = container.user_service
        self.team_service = container.team_service
        self.user_pokemon_service = container.user_pokemon_service

    async def set_team(self, event: AstrMessageEvent):
        """设置队伍中的宝可梦"""
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        args = event.message_str.split()
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
                yield event.plain_result(AnswerEnum.TEAM_SET_INVALID_ID.value.format(id=id))
                return

        result = self.team_service.set_team_pokemon(user_id, [int(id) for id in pokemon_ids])

        if result.success:
            d = result.data
            yield event.plain_result(AnswerEnum.TEAM_SET_SUCCESS.value.format(pokemon_names=', '.join(d)))
        else:
            yield event.plain_result(result.message)

    async def view_team(self, event: AstrMessageEvent):
        """查看当前队伍配置"""
        user_id = userid_to_base32(event.get_sender_id())
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        result = self.team_service.get_user_team(user_id)
        if not result.success or not result.data:
            yield event.plain_result(result.message)
            return

        team: List[UserPokemonInfo] = result.data

        # 显示队伍信息
        message = "🏆 当前队伍配置：\n\n"
        # 显示队伍列表
        if team:
            message += f"\n队伍成员 ({len(team)}/6)：\n"
            for i, pokemon_data in enumerate(team, 1):
                # 从pokemon_data中提取信息
                id = pokemon_data.id
                name = pokemon_data.name
                level = pokemon_data.level
                hp = pokemon_data.stats.hp
                current_hp = pokemon_data.current_hp

                # 标记出战宝可梦（第一个是出战的）
                marker = " ⭐" if i == 1 else ""
                message += f"  {i}. {name}{marker}\n"
                message += f"     ID: {id} | 等级: {level} | HP: {current_hp}\n"
        else:
            message += "\n队伍成员 (0/6)：暂无\n"

        yield event.plain_result(message)

    async def heal_team(self, event: AstrMessageEvent):
        """恢复队伍中所有宝可梦的生命值和状态"""
        user_id = userid_to_base32(event.get_sender_id())

        # 检查用户是否注册
        user = self.plugin.user_repo.get_user_by_id(user_id)
        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        # 检查用户金币是否足够
        cost = 1000
        if user.coins < cost:
            yield event.plain_result(f"金币不足！恢复队伍需要 {cost} 金币，您当前有 {user.coins} 金币。")
            return

        # 获取用户队伍
        team_result = self.team_service.get_user_team(user_id)
        if not team_result.success or not team_result.data:
            yield event.plain_result("您还没有设置队伍，无法进行恢复。")
            return

        team: List[UserPokemonInfo] = team_result.data

        # 检查队伍是否为空
        if not team:
            yield event.plain_result("您的队伍中没有宝可梦。")
            return

        # 准备恢复所有队伍成员
        healed_count = 0
        for pokemon_info in team:
            # 更新宝可梦的当前HP为最大HP，PP为最大PP
            result = self.user_pokemon_service.update_user_pokemon_full_heal(user_id, pokemon_info.id)
            if result is not None:  # 如果更新成功
                healed_count += 1

        # 扣除金币
        new_coins = user.coins - cost
        self.plugin.user_repo.update_user_coins(user_id, new_coins)

        # 记录金币变动日志
        from astrbot.api import logger
        logger.info(f"用户 {user_id} 花费 {cost} 金币恢复了 {healed_count} 只宝可梦的状态")

        yield event.plain_result(f"✅ 队伍恢复成功！\n花费了 {cost} 金币，恢复了 {healed_count} 只宝可梦的全部状态。\n当前金币: {new_coins}")
