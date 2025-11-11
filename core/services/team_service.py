from typing import Dict, Any, List
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractItemTemplateRepository, AbstractTeamRepository,
)

from ..utils import get_now, get_today
from ..domain.models import User


class TeamService:
    """封装与用户相关的业务逻辑"""
    def __init__(
            self,
            user_repo: AbstractUserRepository,
            item_template_repo: AbstractItemTemplateRepository,
            team_repo: AbstractTeamRepository,
            config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.item_template_repo = item_template_repo
        self.team_repo = team_repo
        self.config = config

    def set_team_pokemon(self, user_id: str, pokemon_shortcodes: List[str]) -> Dict[str, Any]:
        """
        设置用户的队伍配置，指定最多6只宝可梦组成队伍，第一个为出战宝可梦
        Args:
            user_id: 用户ID
            pokemon_shortcodes: 宝可梦短码列表（如['P001', 'P002', ...]），最多6个，第一个为出战宝可梦
        Returns:
            包含操作结果的字典
        """
        import json

        # 首先验证用户是否存在
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 获取用户所有的宝可梦
        user_pokemon_list = self.user_repo.get_user_pokemon(user_id)
        user_pokemon_dict = {pokemon.get('shortcode', f"P{pokemon['id']:04d}"): pokemon for pokemon in user_pokemon_list}

        # 检查输入的宝可梦是否都在用户拥有的宝可梦列表中
        for shortcode in pokemon_shortcodes:
            if shortcode not in user_pokemon_dict:
                # 检查是否是数字ID格式，如果是则尝试转换为短码
                if shortcode.isdigit():
                    temp_shortcode = f"P{int(shortcode):04d}"
                    if temp_shortcode not in user_pokemon_dict:
                        return {"success": False, "message": f"宝可梦 {shortcode} 不属于您或不存在"}
                else:
                    return {"success": False, "message": f"宝可梦 {shortcode} 不属于您或不存在"}

        # 限制队伍最多6只宝可梦
        if len(pokemon_shortcodes) > 6:
            return {"success": False, "message": "队伍最多只能包含6只宝可梦"}

        if len(pokemon_shortcodes) == 0:
            return {"success": False, "message": "请至少选择1只宝可梦加入队伍"}

        # 构建队伍数据
        pokemon_list_data = []
        for shortcode in pokemon_shortcodes:
            # 检查是否是数字ID，如果是则转换为短码格式
            actual_shortcode = shortcode
            if shortcode.isdigit():
                actual_shortcode = f"P{int(shortcode):04d}"

            pokemon_data = self.user_repo.get_user_pokemon_by_shortcode(actual_shortcode)
            if not pokemon_data:
                # 尝试用数字ID格式
                pokemon_data = self.user_repo.get_user_pokemon_by_numeric_id(int(shortcode))

            if not pokemon_data:
                return {"success": False, "message": f"无法找到宝可梦 {shortcode}"}

            pokemon = {
                "id": actual_shortcode,  # 保留短码格式
                "pokemon_data": pokemon_data,
            }
            pokemon_list_data.append(pokemon)

        # 第一个为出战宝可梦
        active_pokemon_shortcode = pokemon_shortcodes[0] if pokemon_shortcodes else None
        if active_pokemon_shortcode.isdigit():
            active_pokemon_shortcode = f"P{int(active_pokemon_shortcode):04d}"

        # 创建队伍配置
        team_data = {
            "active_pokemon_id": active_pokemon_shortcode,
            "team_list": pokemon_list_data,
            "last_updated": get_now().isoformat()
        }

        # 保存队伍配置
        self.team_repo.update_user_team(user_id, json.dumps(team_data, ensure_ascii=False))

        # 返回成功信息
        team_names = [pokemon['pokemon_data']['species_name'] for pokemon in pokemon_list_data]
        team_display = ', '.join(team_names)
        active_name = team_names[0] if team_names else ""

        return {
            "success": True,
            "message": f"成功设置队伍！出战宝可梦：{active_name}，队伍成员：[{team_display}]。"
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

        team_str = self.team_repo.get_user_team(user_id)
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

            # 查找匹配的宝可梦，支持短码ID和数字ID
            active_pokemon = None
            if isinstance(active_pokemon_id, str) and active_pokemon_id.startswith('P') and active_pokemon_id[1:].isdigit():
                # 短码ID匹配
                active_pokemon = next((p for p in user_pokemon_list if p.get("shortcode") == active_pokemon_id), None)
            elif isinstance(active_pokemon_id, (int, str)) and str(active_pokemon_id).isdigit():
                # 数字ID匹配
                numeric_id = int(active_pokemon_id)
                active_pokemon = next((p for p in user_pokemon_list if p["id"] == numeric_id), None)

            if active_pokemon:
                team_data["active_pokemon_info"] = {
                    "shortcode": active_pokemon.get("shortcode", f"P{active_pokemon['id']:04d}"),
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