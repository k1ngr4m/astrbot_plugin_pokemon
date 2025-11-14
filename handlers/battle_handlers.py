from typing import TYPE_CHECKING
from astrbot.api.event import AstrMessageEvent
from ..core.answer.answer_enum import AnswerEnum

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class BattleHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.battle_service = plugin.battle_service

    async def battle(self, event: AstrMessageEvent):
        """处理战斗指令"""
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

        # 检查用户是否有设置队伍
        user_team_data = self.plugin.team_repo.get_user_team(user_id)
        if not user_team_data:
            yield event.plain_result("❌ 您还没有设置队伍。请先使用 /设置队伍 指令设置您的出场队伍。")
            return

        # 解析队伍数据
        import json
        try:
            team_pokemon_ids = json.loads(user_team_data) if user_team_data else []
            if not team_pokemon_ids:
                yield event.plain_result("❌ 您的队伍是空的，无法进行战斗。请先使用 /设置队伍 指令设置您的出场队伍。")
                return

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

            if not team_pokemon_ids:
                yield event.plain_result("❌ 您的队伍是空的，无法进行战斗。请先使用 /设置队伍 指令设置您的出场队伍。")
                return
        except json.JSONDecodeError:
            yield event.plain_result("❌ 队伍数据格式错误，请重新设置队伍。")
            return

        # 开始战斗，传入队伍中的第一只宝可梦
        result = self.battle_service.start_battle(user_id, wild_pokemon, str(team_pokemon_ids[0]))

        if result["success"]:
            battle_details = result["battle_details"]
            user_pokemon = battle_details["user_pokemon"]
            wild_pokemon_data = battle_details["wild_pokemon"]
            win_rates = battle_details["win_rates"]
            battle_result = battle_details["result"]
            exp_details = battle_details.get("exp_details", {})

            message = "⚔️ 宝可梦战斗开始！\n\n"
            message += f"👤 我方宝可梦: {user_pokemon['name']} (Lv.{user_pokemon['level']})\n"
            message += f"野生宝可梦: {wild_pokemon_data['name']} (Lv.{wild_pokemon_data['level']})\n\n"

            message += "📊 战斗胜率分析:\n"
            message += f"我方胜率: {win_rates['user_win_rate']}%\n"
            message += f"野生胜率: {win_rates['wild_win_rate']}%\n\n"

            message += f"🎯 战斗结果: {battle_result}\n"

            # 添加经验值信息
            if exp_details:
                team_pokemon_results = exp_details.get("team_pokemon_results", [])
                user_exp_info = exp_details.get("user_exp", {})

                if team_pokemon_results:
                    message += f"\n📈 经验值获取:\n"
                    for i, pokemon_result in enumerate(team_pokemon_results):
                        if pokemon_result.get("success"):
                            exp_gained = pokemon_result.get("exp_gained", 0)
                            pokemon_name = pokemon_result.get("pokemon_name", f"宝可梦{i+1}")
                            message += f"  {pokemon_name} 获得了 {exp_gained} 点经验值\n"

                            level_up_info = pokemon_result.get("level_up_info", {})
                            if level_up_info.get("should_level_up"):
                                levels_gained = level_up_info.get("levels_gained", 0)
                                new_level = level_up_info.get("new_level", 0)
                                message += f"  🎉 恭喜 {pokemon_name} 升级了！等级提升 {levels_gained} 级，现在是 {new_level} 级！\n"

                if user_exp_info.get("success"):
                    user_exp_gained = user_exp_info.get("exp_gained", 0)
                    if user_exp_gained > 0:  # 只有在获得经验时才显示
                        user_levels_gained = user_exp_info.get("levels_gained", 0)
                        new_user_level = user_exp_info.get("new_level", user.level)
                        message += f"  训练家获得了 {user_exp_gained} 点经验值"
                        if user_levels_gained > 0:
                            message += f"，等级提升 {user_levels_gained} 级，现在是 {new_user_level} 级！\n"
                        else:
                            message += "\n"

            # 清除缓存的野生宝可梦信息
            if hasattr(self.plugin, '_cached_wild_pokemon'):
                self.plugin._cached_wild_pokemon.pop(user_id, None)

            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ {result['message']}")