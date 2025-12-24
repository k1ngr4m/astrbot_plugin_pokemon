from typing import Dict, Any

from ....interface.response.answer_enum import AnswerEnum
from ....core.models.user_models import UserItems
from ....infrastructure.repositories.abstract_repository import AbstractUserRepository, AbstractUserItemRepository


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
        type_names = {
            1: "状态增强",
            2: "努力值提升",
            3: "药物",
            4: "其他",
            5: "紧急时刻",
            6: "选择性治疗",
            7: "属性保护",
            8: "烘焙专用",
            9: "收藏品",
            10: "进化道具",
            11: "洞窟探索",
            12: "携带物品",
            13: "选择类道具",
            14: "努力值训练",
            15: "负面携带物品",
            16: "训练道具",
            17: "石板",
            18: "特定物种",
            19: "属性增强",
            20: "活动道具",
            21: "游戏玩法",
            22: "剧情推进",
            23: "未使用",
            24: "战利品",
            25: "全部邮件",
            26: "维生素",
            27: "治疗",
            28: "PP恢复",
            29: "复活",
            30: "状态恢复",
            32: "堆肥",
            33: "特殊精灵球",
            34: "标准精灵球",
            35: "图鉴完成",
            36: "围巾",
            37: "全部机器",
            38: "笛子",
            39: "树果精灵球",
            40: "树果盒",
            41: "数据卡片",
            42: "宝石",
            43: "奇迹发射器",
            44: "超级石",
            45: "回忆",
            46: "Z纯晶",
            47: "物种糖果",
            48: "捕捉加成",
            49: "超极巨晶",
            50: "性格薄荷",
            51: "咖喱食材",
            52: "太晶碎块",
            53: "三明治食材",
            54: "招式机器材料",
            55: "野餐"
        }

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