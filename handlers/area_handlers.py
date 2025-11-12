from typing import Dict, Any
from astrbot.api.event import AstrMessageEvent, MessageEventResult


class AreaHandlers:
    def __init__(self, plugin):
        self.plugin = plugin
        self.area_service = plugin.area_service

    async def view_areas(self, event: AstrMessageEvent):
        """查看所有可冒险的区域"""
        user_id = self.plugin._get_effective_user_id(event)

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
            message += f"遇见概率: {wild_pokemon['encounter_rate']:.1f}%\n\n"
            message += "接下来你可以选择捕捉、战斗或其他操作...\n（冒险功能后续实现）"
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ {result['message']}")