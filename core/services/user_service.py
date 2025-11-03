from typing import Dict, Any
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractItemTemplateRepository,
)

from ..utils import get_now, get_today
from ..domain.models import User


class UserService:
    """封装与用户相关的业务逻辑"""
    def __init__(
            self,
            user_repo: AbstractUserRepository,
            item_template_repo: AbstractItemTemplateRepository,
            config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.item_template_repo = item_template_repo
        self.config = config

    def register(self, user_id: str, nickname: str) -> Dict[str, Any]:
        """
        注册新用户。
        Args:
            user_id: 用户ID
            nickname: 用户昵称
        Returns:
            一个包含成功状态和消息的字典。
        """
        if self.user_repo.check_exists(user_id):
            return {"success": False, "message": "用户已注册"}

        initial_coins = self.config.get("user", {}).get("initial_coins", 200)
        new_user = User(
            user_id=user_id,
            nickname=nickname,
            coins=initial_coins,
            created_at=get_now()
        )
        self.user_repo.add(new_user)

        return {
            "success": True,
            "message": f"注册成功！欢迎 {nickname} 🎉 你获得了 {initial_coins} 金币作为起始资金。"
        }

    def init_select_pokemon(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        初始化选择宝可梦。
        Args:
            user_id: 用户ID
            nickname: 用户昵称
        Returns:
            一个包含成功状态和消息的字典。
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}
        if user.init_select:
            return {"success": False, "message": "用户已初始化选择宝可梦"}

        # 检查宝可梦是否存在
        pokemon_template = self.item_template_repo.get_pokemon_by_id(pokemon_id)
        if not pokemon_template:
            return {"success": False, "message": "宝可梦不存在"}

        return {
            "success": True,
            "message": f"成功将 {pokemon_name_cn} 初始选择为宝可梦！"
        }