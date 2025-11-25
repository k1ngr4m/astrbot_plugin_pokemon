from typing import Dict, Any, List
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.infrastructure.repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractTeamRepository,
)

from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.user_models import UserTeam


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
        user_team = self.team_repo.get_user_team(user_id)
        if not user_team:
            return {"success": False, "message": "您还没有设置队伍", "team": None}

        team_pokemon_ids = user_team.team_pokemon_ids
        team_info = []
        for pokemon_id in team_pokemon_ids:
            pokemon_info = self.user_repo.get_user_pokemon_by_id(user_id, pokemon_id)
            if not pokemon_info:
                return {"success": False, "message": f"队伍中包含不存在的宝可梦 {pokemon_id}"}

            pokemon_info_data = {
                "id": pokemon_info.id,
                "name": pokemon_info.name,
                "level": pokemon_info.level,
                "hp": pokemon_info.stats['hp'],
                "attack": pokemon_info.stats['attack'],
                "defense": pokemon_info.stats['defense'],
                "sp_attack": pokemon_info.stats['sp_attack'],
                "sp_defense": pokemon_info.stats['sp_defense'],
                "speed": pokemon_info.stats['speed'],
            }
            team_info.append(pokemon_info_data)


        return {
            "success": True,
            "team": team_info,
            "message": "成功获取队伍信息"
        }