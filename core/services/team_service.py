from typing import Dict, Any, List
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractTeamRepository,
)

from ..utils import get_now, get_today
from ..domain.user_models import User, UserTeam


class TeamService:
    """封装与用户相关的业务逻辑"""
    def __init__(
            self,
            user_repo: AbstractUserRepository,
            pokemon_repo: AbstractPokemonRepository,
            team_repo: AbstractTeamRepository,
            config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.team_repo = team_repo
        self.config = config

    def set_team_pokemon(self, user_id: str, pokemon_ids: List[int]) -> Dict[str, Any]:
        """
        设置用户的队伍配置，指定最多6只宝可梦组成队伍
        Args:
            user_id: 用户ID
            pokemon_ids: 宝可梦ID列表（如[123, 456, ...]），最多6个
        Returns:
            包含操作结果的字典
        """
        # 获取用户所有的宝可梦
        user_pokemon_list = self.user_repo.get_user_pokemon(user_id)
        user_pokemon_dict = {str(pokemon.id): pokemon for pokemon in user_pokemon_list}

        # 检查输入的宝可梦是否都在用户拥有的宝可梦列表中
        for id in pokemon_ids:
            if id not in user_pokemon_dict:
                temp_id = int(id)
                if str(temp_id) not in user_pokemon_dict:
                    return {"success": False, "message": f"宝可梦 {id} 不属于您或不存在"}

        user_team_pokemon_list = []
        user_team_pokemon_name_list = []
        for id in pokemon_ids:
            pokemon = self.user_repo.get_user_pokemon_by_id(user_id, id)
            pokemon_id = pokemon.id
            pokemon_name = pokemon.name
            user_team_pokemon_list.append(pokemon_id)
            user_team_pokemon_name_list.append(pokemon_name)

        # 创建队伍配置
        user_team: UserTeam = UserTeam(
            user_id=user_id,
            team_pokemon_ids=user_team_pokemon_list
        )

        # 保存队伍配置
        self.team_repo.update_user_team(user_id, user_team)


        return {
            "success": True,
            "message": f"成功设置队伍！队伍成员：{', '.join(user_team_pokemon_name_list)}。"
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

        print(f"原始队伍字符串: {team_str}")

        # 如果 team_str 已经是字典类型，则直接使用；否则解析JSON字符串
        if isinstance(team_str, str):
            try:
                team_data = json.loads(team_str)
            except json.JSONDecodeError:
                return {"success": False, "message": "队伍数据格式错误"}
        else:
            # 假设已经是字典格式
            team_data = team_str

        # 如果有活跃的宝可梦，获取详细信息
        if "active_pokemon_id" in team_data:
            active_pokemon_id = team_data["active_pokemon_id"]
            user_pokemon_list = self.user_repo.get_user_pokemon(user_id)

            # 查找匹配的宝可梦，支持短码ID和数字ID
            active_pokemon = None
            for p in user_pokemon_list:
                # 检查是否为字典或其他对象并适配获取shortcode的方式
                pokemon_shortcode = None
                if hasattr(p, 'shortcode'):
                    pokemon_shortcode = p.shortcode
                elif hasattr(p, 'get') and callable(getattr(p, 'get')):
                    pokemon_shortcode = p.get("shortcode")
                elif isinstance(p, dict):
                    pokemon_shortcode = p.get("shortcode")

                if isinstance(active_pokemon_id, str) and active_pokemon_id.startswith('P') and active_pokemon_id[1:].isdigit():
                    # 短码ID匹配
                    if pokemon_shortcode == active_pokemon_id:
                        active_pokemon = p
                        break
                elif isinstance(active_pokemon_id, (int, str)) and str(active_pokemon_id).isdigit():
                    # 数字ID匹配
                    numeric_id = int(active_pokemon_id)
                    pokemon_id = None
                    if hasattr(p, 'id'):
                        pokemon_id = p.id
                    elif hasattr(p, 'get') and callable(getattr(p, 'get')):
                        pokemon_id = p.get("id")
                    elif isinstance(p, dict):
                        pokemon_id = p.get("id")

                    if pokemon_id == numeric_id:
                        active_pokemon = p
                        break

            if active_pokemon:
                # 适配不同类型的对象获取属性
                def get_attr(obj, attr_name, default=None):
                    if hasattr(obj, attr_name):
                        return getattr(obj, attr_name)
                    elif isinstance(obj, dict):
                        return obj.get(attr_name, default)
                    elif hasattr(obj, 'get') and callable(getattr(obj, 'get')):
                        return obj.get(attr_name, default)
                    else:
                        return default

                def get_item(obj, key, default=None):
                    if isinstance(obj, dict):
                        return obj.get(key, default)
                    elif hasattr(obj, '__getitem__'):
                        try:
                            return obj[key]
                        except (KeyError, IndexError, TypeError):
                            return default
                    elif hasattr(obj, key):
                        return getattr(obj, key)
                    elif hasattr(obj, 'get') and callable(getattr(obj, 'get')):
                        return obj.get(key, default)
                    else:
                        return default

                team_data["active_pokemon_info"] = {
                    "shortcode": get_attr(active_pokemon, 'shortcode', f"P{get_item(active_pokemon, 'id', 0):04d}"),
                    "species_name": get_item(active_pokemon, 'species_name', get_attr(active_pokemon, 'name', '')),
                    "nickname": get_item(active_pokemon, 'nickname', '') or get_item(active_pokemon, 'species_name', get_attr(active_pokemon, 'name', '')),
                    "level": get_item(active_pokemon, 'level', get_attr(active_pokemon, 'level', 0)),
                    "current_hp": get_item(active_pokemon, 'current_hp', get_attr(active_pokemon, 'current_hp', 0)),
                    "attack": get_attr(active_pokemon, 'attack', get_item(active_pokemon, 'attack', 0)),
                    "defense": get_attr(active_pokemon, 'defense', get_item(active_pokemon, 'defense', 0)),
                    "sp_attack": get_attr(active_pokemon, 'sp_attack', get_item(active_pokemon, 'sp_attack', 0)),
                    "sp_defense": get_attr(active_pokemon, 'sp_defense', get_item(active_pokemon, 'sp_defense', 0)),
                    "speed": get_attr(active_pokemon, 'speed', get_item(active_pokemon, 'speed', 0))
                }

        return {
            "success": True,
            "team": team_data,
            "message": "成功获取队伍信息"
        }