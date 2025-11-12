from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class PokemonHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.team_service = plugin.team_service
        self.pokemon_service = plugin.pokemon_service

    async def my_pokemon(self, event: AstrMessageEvent):
        """查看我的宝可梦，支持查看特定宝可梦详细信息"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)

        if not user:
            yield event.plain_result("❌ 您还没有注册，请先使用 /宝可梦注册 命令注册。")
            return

        args = event.message_str.split(" ")
        if len(args) >= 2:
            # 用户想查看特定宝可梦的详细信息
            shortcode = args[1].upper()  # 支持小写输入

            # 验证短码格式（支持数字ID或P开头的短码）
            if not (shortcode.isdigit() or (shortcode.startswith('P') and shortcode[1:].isdigit())):
                yield event.plain_result(f"❌ 宝可梦短码 {shortcode} 格式不正确（支持数字ID或P开头的短码如P001）。")
                return

            # 获取特定宝可梦的信息
            pokemon_data = self.plugin.user_repo.get_user_pokemon_by_id(shortcode)
            if not pokemon_data:
                yield event.plain_result("❌ 您没有这只宝可梦，或宝可梦不存在。")
                return

            # 检查宝可梦是否属于该用户
            if pokemon_data.get('user_id') != user_id:
                yield event.plain_result("❌ 这只宝可梦不属于您。")
                return

            # 显示详细信息
            shiny_str = "✨" if pokemon_data["is_shiny"] else ""
            gender_str = {
                "M": "♂️",
                "F": "♀️",
                "N": "⚲"
            }.get(pokemon_data["gender"], "")

            message = f"🔍 宝可梦详细信息：\n\n"
            message += f"{shiny_str}{pokemon_data['nickname']} {gender_str}\n"
            message += f"短码: {pokemon_data['shortcode']}\n"
            message += f"种族: {pokemon_data['species_name']} ({pokemon_data['species_en_name']})\n"
            message += f"等级: {pokemon_data['level']}\n"
            message += f"HP: {pokemon_data['current_hp']}\n\n"

            # 实际属性值
            message += "💪 实际属性值:\n"
            message += f"  攻击: {pokemon_data.get('attack', 0)}\n"
            message += f"  防御: {pokemon_data.get('defense', 0)}\n"
            message += f"  特攻: {pokemon_data.get('sp_attack', 0)}\n"
            message += f"  特防: {pokemon_data.get('sp_defense', 0)}\n"
            message += f"  速度: {pokemon_data.get('speed', 0)}\n\n"

            # 个体值 (IV)
            message += "📊 个体值 (IV):\n"
            message += f"  HP: {pokemon_data['hp_iv']}/31\n"
            message += f"  攻击: {pokemon_data['attack_iv']}/31\n"
            message += f"  防御: {pokemon_data['defense_iv']}/31\n"
            message += f"  特攻: {pokemon_data['sp_attack_iv']}/31\n"
            message += f"  特防: {pokemon_data['sp_defense_iv']}/31\n"
            message += f"  速度: {pokemon_data['speed_iv']}/31\n\n"

            # 努力值 (EV)
            message += "📈 努力值 (EV):\n"
            message += f"  HP: {pokemon_data['hp_ev']}\n"
            message += f"  攻击: {pokemon_data['attack_ev']}\n"
            message += f"  防御: {pokemon_data['defense_ev']}\n"
            message += f"  特攻: {pokemon_data['sp_attack_ev']}\n"
            message += f"  特防: {pokemon_data['sp_defense_ev']}\n"
            message += f"  速度: {pokemon_data['speed_ev']}\n\n"

            message += f"捕获时间: {pokemon_data['caught_time']}"

            yield event.plain_result(message.strip())
        else:
            # 显示所有宝可梦的列表
            result = self.user_service.get_user_pokemon(user_id)

            if not result["success"]:
                yield event.plain_result(f"❌ {result['message']}")
                return

            if not result["pokemon_list"]:
                yield event.plain_result(result["message"])
                return

            # 组织显示信息
            message = f"🌟 {result['message']}：\n\n"
            for i, pokemon in enumerate(result["pokemon_list"], 1):
                shiny_str = "✨" if pokemon["is_shiny"] else ""
                gender_str = {
                    "M": "♂️",
                    "F": "♀️",
                    "N": "⚲"
                }.get(pokemon["gender"], "")

                message += f"{i}. {shiny_str}{pokemon['nickname']} {gender_str}\n"
                message += f"   短码: {pokemon['shortcode']} | 等级: {pokemon['level']} | HP: {pokemon['current_hp']} | 速度: {pokemon.get('speed', 0)}\n"
                # message += f"   种族ID: {pokemon['species_id']} | 捕获时间: {pokemon['caught_time']}\n\n"

            message += f"\n您可以使用 /我的宝可梦 <短码> 来查看特定宝可梦的详细信息。"

            yield event.plain_result(message.strip())