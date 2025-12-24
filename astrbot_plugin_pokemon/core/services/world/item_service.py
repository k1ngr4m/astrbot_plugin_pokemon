from typing import Dict, Any

from ....interface.response.answer_enum import AnswerEnum
from ....core.models.user_models import UserItems
from ....infrastructure.repositories.abstract_repository import AbstractUserRepository, AbstractUserItemRepository
from ..battle.battle_config import battle_config


class ItemService:
    """处理用户道具业务逻辑"""

    def __init__(
            self,
            user_repo: AbstractUserRepository,
            user_item_repo: AbstractUserItemRepository
    ):
        self.user_repo = user_repo
        self.user_item_repo = user_item_repo

    def get_user_items(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的所有道具
        Args:
            user_id: 用户ID
        Returns:
            包含用户道具信息的字典
        """
        # 获取用户道具
        user_items: UserItems = self.user_item_repo.get_user_items(user_id)

        if not user_items:
            return {
                "success": True,
                "message": AnswerEnum.USER_ITEMS_EMPTY.value,
                "items": []
            }

        # 按类型分组道具
        items_by_type = {}
        total_items = 0

        for item in user_items.items:
            item_type = item.category_id
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)
            total_items += item.quantity

        return {
            "success": True,
            "message": f"🎒 您的背包 (共{total_items}件物品)",
            "items": user_items.items,
            "items_by_type": items_by_type,
            "total_count": total_items
        }

    def format_items_list(self, items_result: Dict[str, Any]) -> str:
        """
        格式化道具列表为可读文本
        Args:
            items_result: get_user_items方法返回的结果
        Returns:
            格式化后的文本
        """
        if not items_result["success"]:
            return items_result["message"]

        if not items_result["items"]:
            return items_result["message"]

        # 按类型分组显示
        formatted_text = f"✅ {items_result['message']}\n\n"

        items_by_type = items_result["items_by_type"]
        # 从配置文件加载物品类别名称映射
        config_type_names = battle_config.get_item_category_names()
        # 将字符串键转换为整数键以匹配category_id
        type_names = {int(k): v for k, v in config_type_names.items()}

        for item_type, items in items_by_type.items():
            type_name = type_names.get(item_type, item_type)
            formatted_text += f"🔸 {type_name}:\n\n"

            for item in items:
                # 如果name_zh为None或空，则使用name_en作为兜底
                item_name = item.name_zh or item.name_en or f"Item {item.item_id}"
                formatted_text += f"  • [{item.item_id}] {item_name} x{item.quantity}\n\n"
                # if item.description:
                #     formatted_text += f"    {item.description}\n"
            formatted_text += "\n"

        return formatted_text.strip()