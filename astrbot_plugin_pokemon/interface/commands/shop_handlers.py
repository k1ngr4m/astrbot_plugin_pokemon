from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING

from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class ShopHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.user_service = container.user_service
        self.shop_service = container.shop_service

    async def view_shop(self, event: AstrMessageEvent):
        """宝可梦商店查看命令处理器"""
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        args = event.message_str.split(" ")
        if len(args) < 2:
            shops = self.shop_service.get_active_shops()
            if not shops:
                yield event.plain_result("❌ 暂无可用商店！")
                return

            shop_list = "\n".join([f"{shop['id']} - {shop['name']}" for shop in shops])
            message = f"🏪 可用商店：\n{shop_list}\n\n"
            message += f"💡 用法：宝可梦商店 [商店ID]\n例如：宝可梦商店 1"
            yield event.plain_result(message)
            return

        try:
            shop_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 商店ID必须是数字！")
            return

        # 使用商店ID查找商店 - 我们需要修改服务层以支持ID查找
        result = self.shop_service.get_shop_by_id(shop_id)

        if not result["success"]:
            yield event.plain_result(result["message"])
            return

        # 格式化商店信息和商品列表
        shop_info = result["shop"]
        message = f"🏪 {result['message']}\n\n"
        if shop_info.get("description"):
            message += f"📝 {shop_info['description']}\n\n"

        # 按类型分组商品（如果type字段存在）
        items_by_type = {}
        for item in shop_info["items"]:
            item_type = item.get("type", "Misc")  # 默认为Misc类型
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)

        type_names = {
            34: "精灵球",
        }

        for item_type, items in items_by_type.items():
            type_name = type_names.get(item_type, item_type)
            message += f"🔸 {type_name}:\n\n"

            for item in items:
                stock_text = "无限" if item["stock"] == -1 else f"{item['stock']}个"
                message += f"  • {item['name']} - {item['price']} 金币/个 (库存: {stock_text})\n"
                if item.get('description'):
                    message += f"    {item['description']}\n"
                # 显示物品ID
                message += f"    [物品ID: {item.get('item_id', '未知')}]"
                message += f"\n\n"
            message += "💡 用法：宝可梦商店购买 [商店ID] [物品ID] [数量]\n例如：宝可梦商店购买 1 4 5\n"
            message += "\n"

        yield event.plain_result(message.strip())

    async def purchase_item(self, event: AstrMessageEvent):
        """购买商品命令处理器"""
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        args = event.message_str.split(" ")
        if len(args) < 4:
            yield event.plain_result("❌ 请提供完整的购买信息！\n用法：宝可梦商店购买 [商店ID] [物品ID] [数量]\n例如：宝可梦商店购买 1 4 5")
            return

        try:
            shop_id = int(args[1])  # 商店ID（数字）
        except ValueError:
            yield event.plain_result("❌ 商店ID必须是数字！")
            return

        item_id_str = args[2]  # 物品ID
        try:
            quantity = int(args[3])  # 数量
        except ValueError:
            yield event.plain_result("❌ 购买数量必须是整数！")
            return

        # 将数字ID转换为字符串格式的商店代码，以便现有服务层使用
        # 由于现有的服务层使用商店code，我们需要适配它
        shop_code = str(shop_id)

        result = self.shop_service.purchase_item(user_id, shop_code, item_id_str, quantity)

        yield event.plain_result(result["message"])