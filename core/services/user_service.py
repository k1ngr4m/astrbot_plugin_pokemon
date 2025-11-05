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

    def set_team_pokemon(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        设置用户的队伍配置，指定一只宝可梦加入队伍出战
        Args:
            user_id: 用户ID
            pokemon_id: 要加入队伍的宝可梦实例ID
        Returns:
            包含操作结果的字典
        """
        import json

        # 首先验证用户和宝可梦是否存在
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 检查宝可梦是否属于该用户
        user_pokemon_list = self.user_repo.get_user_pokemon(user_id)
        pokemon_exists = any(p["id"] == pokemon_id for p in user_pokemon_list)

        if not pokemon_exists:
            return {"success": False, "message": "该宝可梦不属于您或不存在"}

        # 创建队伍配置，当前只设置一只宝可梦
        team_data = {
            "active_pokemon_id": pokemon_id,
            "team_list": [pokemon_id],  # 可以扩展为最多6只宝可梦的队伍
            "last_updated": get_now().isoformat()
        }

        # 保存队伍配置
        self.user_repo.update_user_team(user_id, json.dumps(team_data, ensure_ascii=False))

        # 获取宝可梦信息用于返回
        selected_pokemon = next(p for p in user_pokemon_list if p["id"] == pokemon_id)

        return {
            "success": True,
            "message": f"成功将 {selected_pokemon['species_name']} 加入队伍出战！"
        }

    def get_user_team(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的队伍信息
        Args:
            user_id: 用户ID
        Returns:
            包含用户队伍信息的字典
        """
        import json

        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        team_str = self.user_repo.get_user_team(user_id)
        if not team_str:
            return {"success": True, "message": "您还没有设置队伍", "team": None}

        try:
            team_data = json.loads(team_str)
        except json.JSONDecodeError:
            return {"success": False, "message": "队伍数据格式错误"}

        # 如果有活跃的宝可梦，获取详细信息
        if "active_pokemon_id" in team_data:
            active_pokemon_id = team_data["active_pokemon_id"]
            user_pokemon_list = self.user_repo.get_user_pokemon(user_id)
            active_pokemon = next((p for p in user_pokemon_list if p["id"] == active_pokemon_id), None)

            if active_pokemon:
                team_data["active_pokemon_info"] = {
                    "id": active_pokemon["id"],
                    "species_name": active_pokemon["species_name"],
                    "nickname": active_pokemon["nickname"] or active_pokemon["species_name"],
                    "level": active_pokemon["level"],
                    "current_hp": active_pokemon["current_hp"]
                }

        return {
            "success": True,
            "team": team_data,
            "message": "成功获取队伍信息"
        }