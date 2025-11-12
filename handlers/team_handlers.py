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
            yield event.plain_result("❌ 请输入宝可梦短码列表。用法：设置队伍 <宝可梦短码1> <宝可梦短码2> ...\n\n💡 提示：最多可设置6只宝可梦，第一个为出战宝可梦。使用 我的宝可梦 指令查看您的宝可梦列表和对应的短码。")
            return

        # 获取用户输入的宝可梦短码列表（跳过命令本身）
        pokemon_shortcodes = args[1:]

        if len(pokemon_shortcodes) > 6:
            yield event.plain_result("❌ 队伍最多只能包含6只宝可梦。")
            return

        if len(pokemon_shortcodes) == 0:
            yield event.plain_result("❌ 请至少选择1只宝可梦加入队伍。")
            return

        # 验证每个短码格式（支持数字ID或P开头的短码）
        for shortcode in pokemon_shortcodes:
            if not (shortcode.isdigit() or (shortcode.startswith('P') and shortcode[1:].isdigit())):
                yield event.plain_result(f"❌ 宝可梦短码 {shortcode} 格式不正确（支持数字ID或P开头的短码如P001）。")
                return

        result = self.team_service.set_team_pokemon(user_id, pokemon_shortcodes)

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
            shortcode = pokemon.get("shortcode", pokemon.get("id", "P0000"))
            message += f"⚔️ 出战宝可梦：{pokemon['species_name']}\n"
            message += f"   短码: {shortcode} | 等级: {pokemon['level']} | HP: {pokemon['current_hp']}\n"
        else:
            message += "⚔️ 出战宝可梦：暂无\n"

        # 显示队伍列表
        if "team_list" in team and team["team_list"]:
            message += f"\n队伍成员 ({len(team['team_list'])}/6)：\n"
            for i, pokemon_data_entry in enumerate(team["team_list"], 1):
                # 从pokemon_data_entry中提取信息
                pokemon = pokemon_data_entry.get('pokemon_data', {})
                shortcode = pokemon.get('shortcode', f"P{pokemon.get('id', 0):04d}")
                species_name = pokemon.get('species_name', '未知')
                level = pokemon.get('level', 1)
                current_hp = pokemon.get('current_hp', 0)

                # 标记出战宝可梦（第一个是出战的）
                marker = " ⭐" if i == 1 else ""
                message += f"  {i}. {species_name}{marker}\n"
                message += f"     短码: {shortcode} | 等级: {level} | HP: {current_hp}\n"
        else:
            message += "\n队伍成员 (0/6)：暂无\n"

        yield event.plain_result(message)
