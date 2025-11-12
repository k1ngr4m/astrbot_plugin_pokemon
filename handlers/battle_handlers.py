from typing import TYPE_CHECKING
from astrbot.api.event import AstrMessageEvent

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class BattleHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.battle_service = plugin.battle_service

    async def battle(self, event: AstrMessageEvent):
        """处理战斗指令"""
        user_id = self.plugin._get_effective_user_id(event)

        # 检查用户是否已注册
        user = self.plugin.user_repo.get_by_id(user_id)
        if not user:
            yield event.plain_result("❌ 您尚未注册成为宝可梦训练家，请先使用 /宝可梦注册 指令注册。")
            return

        # 检查是否有缓存的野生宝可梦信息
        wild_pokemon = getattr(self.plugin, '_cached_wild_pokemon', {}).get(user_id)

        if not wild_pokemon:
            yield event.plain_result("❌ 您当前没有遇到野生宝可梦。请先使用 /冒险 <区域代码> 指令去冒险遇到野生宝可梦。")
            return

        # 开始战斗
        result = self.battle_service.start_battle(user_id, wild_pokemon)

        if result["success"]:
            battle_details = result["battle_details"]
            user_pokemon = battle_details["user_pokemon"]
            wild_pokemon_data = battle_details["wild_pokemon"]
            win_rates = battle_details["win_rates"]
            battle_result = battle_details["result"]

            message = "⚔️ 宝可梦战斗开始！\n\n"
            message += f"👤 我方宝可梦: {user_pokemon['name']} (Lv.{user_pokemon['level']})\n"
            message += f"野生宝可梦: {wild_pokemon_data['name']} (Lv.{wild_pokemon_data['level']})\n\n"

            message += "📊 战斗胜率分析:\n"
            message += f"我方胜率: {win_rates['user_win_rate']}%\n"
            message += f"野生胜率: {win_rates['wild_win_rate']}%\n\n"

            message += f"🎯 战斗结果: {battle_result}\n"

            # 清除缓存的野生宝可梦信息
            if hasattr(self.plugin, '_cached_wild_pokemon'):
                self.plugin._cached_wild_pokemon.pop(user_id, None)

            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ {result['message']}")