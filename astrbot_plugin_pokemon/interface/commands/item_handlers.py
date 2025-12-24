import math
from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING

from astrbot.core import logger
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32
from .draw.item_drawer import draw_user_items

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class ItemHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.item_service = container.item_service
        self.tmp_dir = container.tmp_dir

    async def view_items(self, event: AstrMessageEvent):
        """查看用户道具命令处理器，支持分页和图片显示"""
        user_id = userid_to_base32(event.get_sender_id())
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        # 解析参数
        args = event.message_str.split()
        page = 1
        if len(args) > 1:
            page_arg = args[1].lower()
            if page_arg.startswith('p'):
                try:
                    page = int(page_arg[1:])
                except ValueError:
                    yield event.plain_result("❌ 页码格式错误，请使用 P<数字> 格式，例如：/我的物品 P2")
                    return
            elif page_arg.isdigit():
                try:
                    page = int(page_arg)
                except ValueError:
                    yield event.plain_result("❌ 页码格式错误")
                    return

        # 获取用户物品
        result = self.item_service.get_user_items_with_category_names(user_id, page=page)

        if not result["success"]:
            yield event.plain_result(result["message"])
            return

        # 如果用户没有物品
        if not result["items"]:
            yield event.plain_result(AnswerEnum.USER_ITEMS_EMPTY.value)
            return
        # 生成图片
        try:
            image = draw_user_items({
                "items": result["items"],
                "items_by_category": result["items_by_category"],
                "total_count": result["total_count"],
                "page": result["page"],
                "total_pages": result["total_pages"]
            })

            # 临时保存图片
            import os
            import time
            filename = f"user_items_{user_id}_{int(time.time())}.png"
            image_path = os.path.join(self.tmp_dir, filename)
            image.save(image_path)

            # 返回图片
            yield event.image_result(image_path)
        except Exception as e:
            # 如果绘图失败，返回文本格式
            formatted_message = self.item_service.format_items_list(result)
            yield event.plain_result(formatted_message)