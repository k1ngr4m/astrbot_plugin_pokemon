import math
from typing import Dict, Any, Optional

from astrbot.core import logger
from ...models.pokemon_models import Item
from ....interface.response.answer_enum import AnswerEnum
from ....core.models.user_models import UserItems, UserItemInfo
from ....infrastructure.repositories.abstract_repository import AbstractUserRepository, AbstractUserItemRepository, \
    AbstractItemRepository
from ..battle.battle_config import battle_config


class ItemService:
    """处理用户道具业务逻辑"""

    def __init__(
            self,
            user_repo: AbstractUserRepository,
            user_item_repo: AbstractUserItemRepository,
            item_repo: AbstractItemRepository = None
    ):
        self.user_repo = user_repo
        self.user_item_repo = user_item_repo
        self.item_repo = item_repo

    def get_item_by_id(self, item_id):
        return self.item_repo.get_item_by_id(item_id)

    def get_item_by_name(self, item_name):
        """根据名称查询道具"""
        return self.item_repo.get_item_by_name(item_name)

    def get_user_items(self, user_id: str, page: int = 1, items_per_page: int = 20) -> Dict[str, Any]:
        """
        获取用户的所有道具
        Args:
            user_id: 用户ID
            page: 页码（从1开始）
            items_per_page: 每页物品数量
        Returns:
            包含用户道具信息的字典
        """
        # 获取用户道具
        user_items: UserItems = self.user_item_repo.get_user_items(user_id)

        if not user_items:
            return {
                "success": False,
                "message": AnswerEnum.USER_ITEMS_EMPTY.value,
                "items": [],
                "items_by_type": {},
                "total_count": 0
            }

        # 从配置获取物品类别映射（包含pocket_id信息）
        item_categories = battle_config.get_item_categories()
        # 创建category_id到pocket_id的映射
        category_to_pocket = {int(cat['id']): cat['pocket_id'] for cat in item_categories}

        # 按pocket_id分组道具
        items_by_pocket = {}
        total_items = 0

        for item in user_items.items:
            category_id = item.category_id
            pocket_id = category_to_pocket.get(category_id, 0)  # 默认为0
            if pocket_id not in items_by_pocket:
                items_by_pocket[pocket_id] = []
            items_by_pocket[pocket_id].append(item)
            total_items += item.quantity

        # 扁平化物品列表用于分页
        all_items = []
        for pocket_id, items in items_by_pocket.items():
            for item in items:
                all_items.append({
                    "item_id": item.item_id,
                    "name_en": item.name_en,
                    "name": item.name_zh or item.name_en or f"Item {item.item_id}",
                    "category_id": item.category_id,  # 保留原始category_id
                    "pocket_id": pocket_id,
                    "quantity": item.quantity,
                    "description": getattr(item, 'description', ''),
                    "price": getattr(item, 'price', 0)
                })

        # 计算总页数
        total_pages = max(1, math.ceil(len(all_items) / items_per_page))

        # 确保页码有效
        page = max(1, min(page, total_pages))

        # 获取当前页的物品
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_page_items = all_items[start_idx:end_idx]

        return {
            "success": True,
            "message": f"🎒 您的背包 (共{total_items}件物品)",
            "items": current_page_items,
            "all_items": all_items,  # 所有物品（未分页）
            "items_by_type": items_by_pocket,  # 按pocket分组
            "total_count": total_items,
            "page": page,
            "total_pages": total_pages,
            "items_per_page": items_per_page
        }

    def get_user_items_with_category_names(self, user_id: str, page: int = 1, items_per_page: int = 20) -> Dict[str, Any]:
        """
        获取用户的所有道具，并包含类别中文名称
        Args:
            user_id: 用户ID
            page: 页码（从1开始）
            items_per_page: 每页物品数量
        Returns:
            包含用户道具信息的字典，包含类别中文名称
        """
        # 从配置文件加载物品类别信息
        item_category_info = battle_config.get_item_category_info()
        # 创建category_id到名称的映射
        type_names = {int(cat['id']): cat['name'] for cat in item_category_info}

        # 从配置获取背包ID映射
        pocket_mapping = battle_config.get_pocket_id_mapping()
        # 创建pocket_id到背包名称的映射
        pocket_names = {int(pocket['id']): pocket['name'] for pocket in pocket_mapping}

        result = self.get_user_items(user_id, page, items_per_page)
        if result["success"]:
            # 为每件物品添加类别名称
            for item in result["items"]:
                item["category_name"] = type_names.get(item["category_id"], f"类别{item['category_id']}")
                item["pocket_name"] = pocket_names.get(item["pocket_id"], f"背包{item['pocket_id']}")

            # 为items_by_type也添加类别名称（现在是按pocket_id分组）
            formatted_by_pocket = {}
            for pocket_id, items in result["items_by_type"].items():
                formatted_by_pocket[pocket_id] = []
                pocket_name = pocket_names.get(pocket_id, f"背包{pocket_id}")
                for item in items:
                    # 从item_repo获取完整的物品信息，包括name_en
                    item_detail = self.item_repo.get_item_by_id(item.item_id) if self.item_repo else None
                    item_name_en = item_detail['name_en']
                    item_name_zh = item_detail['name_zh'] if item_detail['name_zh'] != "None" else item_detail['name_en']

                    formatted_by_pocket[pocket_id].append({
                        "item_id": item.item_id,
                        "name": item_name_zh or item_name_en or f"Item {item.item_id}",
                        "name_en": item_name_en,
                        "category_id": item.category_id,
                        "pocket_id": pocket_id,
                        "category_name": type_names.get(item.category_id, f"类别{item.category_id}"),
                        "pocket_name": pocket_name,
                        "quantity": item.quantity,
                        "description": getattr(item, 'description', ''),
                        "price": getattr(item, 'price', 0)
                    })
            result["items_by_category"] = formatted_by_pocket

        return result

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
        # 从配置获取背包ID映射
        pocket_mapping = battle_config.get_pocket_id_mapping()
        # 创建pocket_id到背包名称的映射
        pocket_names = {int(pocket['id']): pocket['name'] for pocket in pocket_mapping}

        for pocket_id, items in items_by_type.items():
            pocket_name = pocket_names.get(pocket_id, f"背包{pocket_id}")
            formatted_text += f"🔸 {pocket_name}:\n\n"

            for item in items:
                # 如果name_zh为None或空，则使用name_en作为兜底
                item_name = item.name_zh or item.name_en or f"Item {item.item_id}"
                formatted_text += f"  • [{item.item_id}] {item_name} x{item.quantity}\n\n"
                # if item.description:
                #     formatted_text += f"    {item.description}\n"
            formatted_text += "\n"

        return formatted_text.strip()