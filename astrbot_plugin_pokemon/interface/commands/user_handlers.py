from typing import TYPE_CHECKING
from astrbot.api.event import AstrMessageEvent
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class UserHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.user_service = container.user_service

    async def register_user(self, event: AstrMessageEvent):
        """注册用户命令"""
        user_id = event.get_sender_id()

        nickname = event.get_sender_name() if event.get_sender_name() is not None else user_id
        result = self.user_service.register(user_id, nickname)
        yield event.plain_result(result.message)

    async def checkin(self, event: AstrMessageEvent):
        """签到命令处理器"""
        user_id = userid_to_base32(event.get_sender_id())
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

    async def profile(self, event: AstrMessageEvent):
        """查看用户个人资料"""
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.get_user_profile(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        profile_data = result.data
        level = profile_data["level"]
        exp = profile_data["exp"]
        coins = profile_data["coins"]
        nickname = profile_data["nickname"]

        # 计算经验进度百分比
        exp_percentage = 0

        # 检查用户的经验是否符合当前等级的范围
        required_for_current_level = self.user_service.exp_service.get_required_exp_for_level(level)
        required_for_next_level = self.user_service.exp_service.get_required_exp_for_level(level + 1) if level >= 1 else 0

        # 如果用户的经验不足以达到当前等级要求，说明数据库可能有不一致，按实际情况计算
        if exp < required_for_current_level:
            # 用户的经验不足以达到当前等级的最低要求，这是一个不一致状态
            # 按照实际经验计算可能的等级或显示进度到下一级
            if level == 1:
                # 如果等级是1但经验小于0（不应该发生），按0处理
                exp_percentage = 100 if exp >= 0 else 0
            else:
                # 检查用户实际应该在哪个等级
                actual_level = level
                while actual_level > 1 and exp < self.user_service.exp_service.get_required_exp_for_level(actual_level):
                    actual_level -= 1

                if actual_level == level:
                    # 如果计算出的等级等于当前等级，计算到下一级的进度
                    if required_for_next_level > required_for_current_level:
                        exp_percentage = int(((exp - required_for_current_level) /
                                            (required_for_next_level - required_for_current_level)) * 100)
                else:
                    # 如果发现用户实际应在更低等级，显示到升到当前等级的进度
                    exp_percentage = int((exp / required_for_current_level) * 100)
        else:
            # 经验符合当前等级，正常计算从当前等级到下一级的进度
            if level == 1:
                if required_for_next_level > 0:
                    exp_percentage = int((exp / required_for_next_level) * 100)
            else:
                if required_for_next_level > required_for_current_level:
                    exp_percentage = int(((exp - required_for_current_level) /
                                        (required_for_next_level - required_for_current_level)) * 100)

        # 限制进度百分比在0-100之间
        exp_percentage = max(0, min(100, exp_percentage))

        # 显示当前等级的经验范围
        if level > 1:
            required_for_current_level = self.user_service.exp_service.get_required_exp_for_level(level)
            required_for_next_level = self.user_service.exp_service.get_required_exp_for_level(level + 1)
            exp_progress = f"{exp}"
        else:
            required_for_next_level = self.user_service.exp_service.get_required_exp_for_level(2)
            exp_progress = f"{exp}"

        message = [
            f"👤 用户资料\n\n",
            f"昵称: {nickname}\n\n",
            f"等级: {level}\n\n",
            f"经验: {exp_progress}\n\n",
            f"经验进度: {exp_percentage}%\n\n",
            f"金币: {coins}",
        ]

        yield event.plain_result("\n".join(message))
