from typing import Dict, Any
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from ..core.answer.answer_enum import AnswerEnum


class AreaHandlers:
    def __init__(self, plugin):
        self.plugin = plugin
        self.area_service = plugin.area_service

    async def view_areas(self, event: AstrMessageEvent):
        """查看所有可冒险的区域"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        result = self.area_service.get_all_areas()

        if not result["success"]:
            yield event.plain_result(f"❌ {result['message']}")
            return

        if not result["areas"]:
            yield event.plain_result(result["message"])
            return

        # 组织显示信息
        message = f"🗺️ {result['message']}：\n\n"
        for i, area in enumerate(result["areas"], 1):
            message += f"{i}. {area['name']}\n"
            message += f"   短码: {area['area_code']} | 等级: {area['min_level']}-{area['max_level']}\n"
            if area['description'] != "暂无描述":
                message += f"   描述: {area['description']}\n"
            message += "\n"

        message += "💡 使用 冒险 <区域短码> 指令进入冒险！"

        yield event.plain_result(message.strip())

    async def adventure(self, event: AstrMessageEvent):
        """进入指定区域冒险"""
        user_id = self.plugin._get_effective_user_id(event)

        # 检查用户是否有设置队伍
        user_team_data = self.plugin.team_repo.get_user_team(user_id)
        if not user_team_data:
            yield event.plain_result("❌ 您还没有设置队伍。请先使用 /设置队伍 指令设置您的出场队伍，才能进行冒险。")
            return

        # 解析队伍数据
        import json
        try:
            team_pokemon_ids = json.loads(user_team_data) if user_team_data else []
            if not team_pokemon_ids:
                yield event.plain_result("❌ 您的队伍是空的，无法进行冒险。请先使用 /设置队伍 指令设置您的出场队伍。")
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
                yield event.plain_result("❌ 您的队伍是空的，无法进行冒险。请先使用 /设置队伍 指令设置您的出场队伍。")
                return
        except json.JSONDecodeError:
            yield event.plain_result("❌ 队伍数据格式错误，请重新设置队伍。")
            return

        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result("❌ 请输入要冒险的区域短码。用法：冒险 <区域短码>\n\n💡 提示：使用 查看区域 指令查看所有可冒险的区域。")
            return

        area_code = args[1].upper()  # 转换为大写

        # 验证区域代码格式（A开头的四位数）
        if not (area_code.startswith('A') and len(area_code) == 4 and area_code[1:].isdigit()):
            yield event.plain_result(f"❌ 区域短码 {area_code} 格式不正确（应为A开头的四位数，如A001）。")
            return

        result = self.area_service.adventure_in_area(user_id, area_code)

        if result["success"]:
            wild_pokemon = result["wild_pokemon"]
            message = f"🌳 在 {result['area']['name']} 中冒险！\n\n"
            message += f"✨ 遇到了野生的 {wild_pokemon['name']}！\n"
            message += f"等级: {wild_pokemon['level']}\n"

            # 缓存野生宝可梦信息，供战斗使用
            if not hasattr(self.plugin, '_cached_wild_pokemon'):
                self.plugin._cached_wild_pokemon = {}
            self.plugin._cached_wild_pokemon[user_id] = wild_pokemon

            message += "接下来你可以选择战斗或捕捉...\n使用 /战斗 指令进行对战！"
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ {result['message']}")