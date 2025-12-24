import random
from typing import Dict, Any, Optional

from astrbot.api import logger

from ...models.common_models import BaseResult
from ....infrastructure.repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractItemRepository, AbstractUserPokemonRepository,
    AbstractPokemonAbilityRepository, AbstractUserItemRepository,
)

from ....utils.utils import get_today, userid_to_base32
from ....core.models.user_models import User, UserItems, UserItemInfo
from ....core.models.pokemon_models import UserPokemonInfo, PokemonDetail, PokemonStats, WildPokemonInfo
from ....interface.response.answer_enum import AnswerEnum

class UserItemService:
    """封装与用户物品相关的业务逻辑"""
    def __init__(
            self,
            user_item_repo: AbstractUserItemRepository,
            config: Dict[str, Any]
    ):
        self.user_item_repo = user_item_repo
        self.config = config

    def get_user_items(self, user_id: str) -> BaseResult[UserItems]:
        """
        获取用户的所有物品
        Args:
            user_id: 用户ID
        Returns:
            用户物品列表，每个物品包含item_id, item_name, quantity等信息
        """
        user_items = self.user_item_repo.get_user_items(user_id)
        return BaseResult(
            success=True,
            message="获取用户道具成功",
            data=user_items
        )

    def add_user_item(self, user_id: str, item_id: int, quantity: int) -> BaseResult:
        """
        添加或更新用户物品
        Args:
            user_id: 用户ID
            item_id: 物品ID
            quantity: 数量（可以为负数表示减少）
        """
        self.user_item_repo.add_user_item(user_id, item_id, quantity)
        return BaseResult(
            success=True,
            message="添加用户道具成功",
            data=None
        )

    def get_user_item_by_id(self, user_id: str, item_id: int) -> BaseResult[UserItemInfo]:
        """
        获取用户指定物品的详细信息
        Args:
            user_id: 用户ID
            item_id: 物品ID
        Returns:
            物品详细信息，包含item_id, item_name, quantity等字段
        """
        user_item = self.user_item_repo.get_user_item_by_id(user_id, item_id)
        if not user_item:
            return BaseResult(
                success=False,
                message=f"用户 {user_id} 没有物品 {item_id}",
                data=None
            )
        return BaseResult(
            success=True,
            message="获取用户道具成功",
            data=user_item
        )
