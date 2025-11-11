from astrbot.api.event import filter, AstrMessageEvent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class CommonHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service

    async def register_user(self, event: AstrMessageEvent):
        """注册用户命令"""
        user_id = self.plugin._get_effective_user_id(event)
        nickname = event.get_sender_name() if event.get_sender_name() is not None else user_id
        if result := self.user_service.register(user_id, nickname):
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result("❌ 出错啦！请稍后再试。")

    async def init_select(self, event: AstrMessageEvent):
        """初始化选择宝可梦"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)
        if not user:
            yield event.plain_result("❌ 您还没有注册，请先使用 /宝可梦注册 命令注册。")
            return
        if user.init_selected:
            yield event.plain_result("❌ 用户已初始化选择宝可梦")
            return

        args = event.message_str.split(" ")

        if len(args) < 2:
            yield event.plain_result("❌ 请输入宝可梦ID。用法：初始选择 <宝可梦ID>")
            return
        try:
            pokemon_id = int(args[1])

            if pokemon_id not in (1, 4, 7):
                yield event.plain_result("❌ 请从妙蛙种子1、小火龙4、杰尼龟7中选择。")
                return
        except ValueError:
            yield event.plain_result("❌ 请输入正确的宝可梦ID。")
            return

        result = self.user_service.init_select_pokemon(user_id, pokemon_id)

        if result["success"]:
            yield event.plain_result(f"✅ {result['message']}")
        else:
            yield event.plain_result(f"❌ {result['message']}")

    async def my_pokemon(self, event: AstrMessageEvent):
        """查看我的宝可梦"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)

        if not user:
            yield event.plain_result("❌ 您还没有注册，请先使用 /宝可梦注册 命令注册。")
            return

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
            message += f"   短码: {pokemon['shortcode']} | 等级: {pokemon['level']} | HP: {pokemon['current_hp']}\n"
            # message += f"   种族ID: {pokemon['species_id']} | 捕获时间: {pokemon['caught_time']}\n\n"

        yield event.plain_result(message.strip())