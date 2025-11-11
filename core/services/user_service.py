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
            "message": f"注册成功！欢迎 {nickname} 🎉 你获得了 {initial_coins} 金币作为起始资金。请从妙蛙种子1、小火龙4、杰尼龟7中选择作为初始宝可梦。输入 /初始选择 <宝可梦ID> 来选择。"
        }

    def init_select_pokemon(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        初始化选择宝可梦。
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            一个包含成功状态和消息的字典。
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}
        if user.init_selected:
            return {"success": False, "message": "用户已初始化选择宝可梦"}

        # 检查宝可梦是否存在
        pokemon_template = self.item_template_repo.get_pokemon_by_id(pokemon_id)
        if not pokemon_template:
            return {"success": False, "message": "宝可梦不存在"}

        # 创建用户宝可梦记录
        self.user_repo.create_user_pokemon(user_id, pokemon_id, pokemon_template.name_cn)

        # 更新用户的初始选择状态
        self.user_repo.update_init_select(user_id, pokemon_id)

        return {
            "success": True,
            "message": f"成功将 {pokemon_template.name_cn} 初始选择为宝可梦！"
        }

    def get_user_pokemon(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的所有宝可梦信息
        Args:
            user_id: 用户ID
        Returns:
            包含用户宝可梦信息的字典
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        user_pokemon_list = self.user_repo.get_user_pokemon(user_id)

        if not user_pokemon_list:
            return {"success": True, "message": "您还没有获得任何宝可梦", "pokemon_list": []}

        # 格式化返回数据
        formatted_pokemon = []
        for pokemon in user_pokemon_list:
            formatted_pokemon.append({
                "id": pokemon["id"],
                "species_id": pokemon["species_id"],
                "species_name": pokemon["species_name"],
                "species_en_name": pokemon["species_en_name"],
                "nickname": pokemon["nickname"] or pokemon["species_name"],
                "level": pokemon["level"],
                "exp": pokemon["exp"],
                "gender": pokemon["gender"],
                "current_hp": pokemon["current_hp"],
                "is_shiny": bool(pokemon["is_shiny"]),
                "caught_time": pokemon["caught_time"]
            })

        return {
            "success": True,
            "pokemon_list": formatted_pokemon,
            "count": len(formatted_pokemon),
            "message": f"您拥有 {len(formatted_pokemon)} 只宝可梦"
        }

