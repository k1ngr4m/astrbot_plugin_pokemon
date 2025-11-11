from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class TeamHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.team_service = plugin.team_service

    async def set_team(self, event: AstrMessageEvent):
        """设置队伍中的宝可梦"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)

        if not user:
            yield event.plain_result("❌ 您还没有注册，请先使用 /宝可梦注册 命令注册。")
            return

        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result("❌ 请输入宝可梦实例ID。用法：队伍设置 <宝可梦ID>\n\n💡 提示：使用 我的宝可梦 指令查看您的宝可梦列表和对应的ID")
            return

        try:
            pokemon_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 请输入正确的宝可梦实例ID。\n💡 提示：使用 我的宝可梦 指令查看您的宝可梦列表和对应的ID")
            return

        result = self.team_service.set_team_pokemon(user_id, pokemon_id)

        if result["success"]:
            yield event.plain_result(f"✅ {result['message']}")
        else:
            yield event.plain_result(f"❌ {result['message']}")

    async def view_team(self, event: AstrMessageEvent):
        """查看当前队伍配置"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)

        if not user:
            yield event.plain_result("❌ 您还没有注册，请先使用 /宝可梦注册 命令注册。")
            return

        result = self.team_service.get_user_team(user_id)

        if not result["success"]:
            yield event.plain_result(f"❌ {result['message']}")
            return

        if not result["team"]:
            yield event.plain_result(result["message"])
            return

        team = result["team"]
        print(team)

        # 显示队伍信息
        message = "🏆 当前队伍配置：\n\n"
        if "active_pokemon_info" in team:
            pokemon = team["active_pokemon_info"]
            message += f"⚔️ 出战宝可梦：{pokemon['nickname']}\n"
            message += f"   实例ID: {pokemon['id']} | 等级: {pokemon['level']} | HP: {pokemon['current_hp']}\n"
        else:
            message += "⚔️ 出战宝可梦：暂无\n"

        # 显示队伍列表（当前只支持一只，但可以扩展）
        if "team_list" in team:
            message += f"\n队伍成员 ({len(team['team_list'])}/6)：\n"
            for i, pokemon in enumerate(team["team_list"], 1):
                # 这里可以进一步优化，显示更多宝可梦信息
                message += f"  {i}. 实例ID: {pokemon['id']} | 昵称: {pokemon['pokemon_data']['nickname']}\n"

        yield event.plain_result(message)
