from typing import TYPE_CHECKING
import random
from astrbot.api.event import AstrMessageEvent
from ..core.answer.answer_enum import AnswerEnum

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class RunHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin

    async def run(self, event: AstrMessageEvent):
        """处理逃跑指令"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        # 检查是否有缓存的野生宝可梦信息
        wild_pokemon = getattr(self.plugin, '_cached_wild_pokemon', {}).get(user_id)

        if not wild_pokemon:
            yield event.plain_result("❌ 您当前没有遇到野生宝可梦。请先使用 /冒险 <区域代码> 指令去冒险遇到野生宝可梦。")
            return

        # 检查用户是否有设置队伍（用于逃跑成功率计算）
        user_team_data = self.plugin.team_repo.get_user_team(user_id)
        if not user_team_data:
            # 如果没有队伍，默认80%逃跑成功率
            escape_success_rate = 80
        else:
            # 解析队伍数据，获取第一只宝可梦用于逃跑成功率计算
            import json
            try:
                team_pokemon_ids = json.loads(user_team_data) if user_team_data else []
                if team_pokemon_ids:
                    # 检查team_pokemon_ids是否为字典（如果是字典格式，则获取值列表）
                    if isinstance(team_pokemon_ids, dict):
                        # 如果是字典格式，获取其中的宝可梦IDs列表
                        if 'pokemon_list' in team_pokemon_ids:
                            team_pokemon_ids = team_pokemon_ids['pokemon_list']
                        elif 'team' in team_pokemon_ids:
                            team_pokemon_ids = team_pokemon_ids['team']
                        else:
                            # 尝试获取字典中的所有值
                            team_pokemon_ids = list(team_pokemon_ids.values())
                            if team_pokemon_ids and isinstance(team_pokemon_ids[0], list):
                                team_pokemon_ids = team_pokemon_ids[0]

                    # 确保team_pokemon_ids是列表
                    if not isinstance(team_pokemon_ids, list):
                        # 如果不是列表，尝试转换为列表
                        if isinstance(team_pokemon_ids, (str, int)):
                            team_pokemon_ids = [team_pokemon_ids]
                        else:
                            team_pokemon_ids = []

                    if team_pokemon_ids:
                        # 获取用户的宝可梦信息用于计算逃跑成功率
                        user_pokemon = self.plugin.user_repo.get_user_pokemon_by_id(str(team_pokemon_ids[0]))
                        if user_pokemon:
                            # 基于速度差异计算逃跑成功率
                            user_speed = user_pokemon.get('speed', 50)
                            wild_speed = wild_pokemon.get('speed', 50)

                            # 逃跑成功率 = 80% + (用户宝可梦速度 - 野生宝可梦速度) * 0.5%
                            # 限制在20%到95%之间
                            speed_diff = user_speed - wild_speed
                            escape_success_rate = 80 + (speed_diff * 0.5)
                            escape_success_rate = max(20, min(95, escape_success_rate))
                        else:
                            escape_success_rate = 80
                    else:
                        escape_success_rate = 80
                else:
                    escape_success_rate = 80
            except json.JSONDecodeError:
                escape_success_rate = 80

        # 计算逃跑结果（默认80%成功率）
        escape_success = random.random() * 100 < escape_success_rate

        if escape_success:
            message = "🏃 您成功逃跑了！\n\n"
            message += f"野生的 {wild_pokemon['name']} 没有追上来。\n"

            # 清除缓存的野生宝可梦信息
            if hasattr(self.plugin, '_cached_wild_pokemon'):
                self.plugin._cached_wild_pokemon.pop(user_id, None)
        else:
            message = "😅 逃跑失败了！\n\n"
            message += f"野生的 {wild_pokemon['name']} 还在盯着你...\n"
            message += "你可以再次尝试逃跑，或者选择战斗或捕捉！"

        yield event.plain_result(message)