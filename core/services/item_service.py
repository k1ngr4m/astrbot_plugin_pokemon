from typing import Dict, List, Any
from ..repositories.abstract_repository import AbstractUserRepository


class ItemService:
    """处理用户道具业务逻辑"""

    def __init__(self, user_repo: AbstractUserRepository):
        self.user_repo = user_repo

    def get_user_items(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的所有道具
        Args:
            user_id: 用户ID
        Returns:
            包含用户道具信息的字典
        """
        # 检查用户是否存在
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {
                "success": False,
                "message": "❌ 用户不存在，请先注册！"
            }

        # 获取用户道具
        user_items = self.user_repo.get_user_items(user_id)

        if not user_items:
            return {
                "success": True,
                "message": "🎒 您的背包是空的，快去签到或冒险获得道具吧！",
                "items": []
            }

        # 按类型分组道具
        items_by_type = {}
        total_items = 0

        for item in user_items:
            item_type = item["type"]
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)
            total_items += item["quantity"]

        return {
            "success": True,
            "message": f"🎒 您的背包 (共{total_items}件物品)",
            "items": user_items,
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
        type_names = {
            "Pokeball": "精灵球",
            "Healing": "回复道具",
            "Battle": "对战道具",
            "Evolution": "进化道具",
            "Misc": "其他道具"
        }

        for item_type, items in items_by_type.items():
            type_name = type_names.get(item_type, item_type)
            formatted_text += f"🔸 {type_name}:\n"

            for item in items:
                formatted_text += f"  • [{item['item_id']}] {item['name']} x{item['quantity']}\n"
                if item['description']:
                    formatted_text += f"    {item['description']}\n"
            formatted_text += "\n"

        return formatted_text.strip()