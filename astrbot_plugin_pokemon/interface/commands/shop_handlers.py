from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING

from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin

class ShopHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.shop_service = plugin.shop_service

    async def view_shop(self, event: AstrMessageEvent):
        """宝可梦商店查看命令处理器"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        args = event.message_str.split(" ")
        if len(args) < 2:
            shops=self.shop_service.get_active_shops()
            shop_list = "\n".join([f"{shop['shop_code']} - {shop['name']}" for shop in shops])

            yield event.plain_result(f"❌ 请输入商店短码！\n\n可用商店：\n{shop_list}\n\n用法：宝可梦商店 [商店短码]\n例如：宝可梦商店 S001")
            return

        shop_code = args[1].upper()  # 支持小写输入

        # 验证短码格式（S开头后跟1-3位数字，如S01, S001, S1）
        if not (shop_code.startswith('S') and shop_code[1:].isdigit() and len(shop_code) <= 4 and len(shop_code) > 1):
            yield event.plain_result(f"❌ 商店短码 {shop_code} 格式不正确（应为S开头后跟1-3位数字，如S01或S1）。")
            return

        # 确保短码是S+3位数字格式（补零）
        shop_number = shop_code[1:]  # 获取数字部分
        formatted_shop_code = f"S{shop_number.zfill(3)}"  # 补零到3位

        result = self.shop_service.get_shop_by_code(formatted_shop_code)

        if not result["success"]:
            yield event.plain_result(result["message"])
            return

        # 格式化商店信息和商品列表
        shop_info = result["shop"]
        message = f"🏪 {result['message']}\n\n"
        if shop_info.get("description"):
            message += f"📝 {shop_info['description']}\n\n"

        # 按类型分组商品
        items_by_type = {}
        for item in shop_info["items"]:
            item_type = item["type"]
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)

        type_names = {
            "Pokeball": "精灵球",
            "Healing": "回复道具",
            "Battle": "对战道具",
            "Evolution": "进化道具",
            "Misc": "其他道具"
        }

        for item_type, items in items_by_type.items():
            type_name = type_names.get(item_type, item_type)
            message += f"🔸 {type_name}:\n\n"

            for item in items:
                stock_text = "无限" if item["stock"] == -1 else f"{item['stock']}个"
                message += f"  • {item['name']} - {item['price']} 金币/个 (库存: {stock_text})\n"
                if item['description']:
                    message += f"    {item['description']}\n\n"
            message += "\n"

        yield event.plain_result(message.strip())

    async def purchase_item(self, event: AstrMessageEvent):
        """购买商品命令处理器"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        args = event.message_str.split(" ")
        if len(args) < 4:
            yield event.plain_result("❌ 请提供完整的购买信息！\n用法：商店购买 [商店短码] [物品ID] [数量]\n例如：商店购买 S001 1 5")
            return

        shop_code = args[1].upper()  # 商店短码
        item_id = args[2]  # 物品ID
        try:
            quantity = int(args[3])  # 数量
        except ValueError:
            yield event.plain_result("❌ 购买数量必须是整数！")
            return

        # 验证商店短码格式
        if not (shop_code.startswith('S') and shop_code[1:].isdigit() and len(shop_code) <= 4 and len(shop_code) > 1):
            yield event.plain_result(f"❌ 商店短码 {shop_code} 格式不正确（应为S开头后跟1-3位数字，如S01或S1）。")
            return

        # 确保短码是S+3位数字格式（补零）
        shop_number = shop_code[1:]  # 获取数字部分
        formatted_shop_code = f"S{shop_number.zfill(3)}"  # 补零到3位

        result = self.shop_service.purchase_item(user_id, formatted_shop_code, item_id, quantity)

        yield event.plain_result(result["message"])