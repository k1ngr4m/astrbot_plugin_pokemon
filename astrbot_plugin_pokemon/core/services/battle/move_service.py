from typing import Dict, Any, List, Optional

from ....infrastructure.repositories.abstract_repository import AbstractMoveRepository
from ...models.common_models import BaseResult


class MoveService:
    """技能相关业务逻辑服务"""

    def __init__(self, move_repo: AbstractMoveRepository):
        self.move_repo = move_repo

    def get_move_by_id(self, move_id: int) -> Optional[Dict[str, Any]]:
        """
        获取技能详细信息
        Args:
            move_id: 技能ID
        Returns:
            技能详细信息字典或None
        """
        return self.move_repo.get_move_by_id(move_id)

    def get_level_up_moves(self, pokemon_species_id: int, level: int) -> List[int]:
        """
        获取宝可梦在指定等级及以下可以学到的升级招式
        Args:
            pokemon_species_id: 宝可梦物种ID
            level: 等级
        Returns:
            技能ID列表
        """
        return self.move_repo.get_level_up_moves(pokemon_species_id, level)

    def get_moves_learned_in_level_range(self, pokemon_species_id: int, min_level: int, max_level: int) -> List[int]:
        """
        获取宝可梦在指定等级范围内新学会的升级招式
        Args:
            pokemon_species_id: 宝可梦物种ID
            min_level: 最小等级
            max_level: 最大等级
        Returns:
            技能ID列表
        """
        return self.move_repo.get_moves_learned_in_level_range(pokemon_species_id, min_level, max_level)

    def get_move_name_str(self, move_id: int) -> str:
        """
        安全获取技能名称
        Args:
            move_id: 技能ID
        Returns:
            技能名称
        """
        if not move_id:
            return "未知技能"
        move_info = self.get_move_by_id(move_id)
        return move_info['name_zh'] if move_info else f"技能{move_id}"

    def get_move_stat_changes_by_move_id(self, move_id: int) -> List[Dict[str, Any]]:
        """
        获取技能能力变化数据
        Args:
            move_id: 技能ID
        Returns:
            技能能力变化数据列表
        """
        return self.move_repo.get_move_stat_changes_by_move_id(move_id)

    def get_move_by_name(self, move_name: str) -> Optional[Dict[str, Any]]:
        """
        根据技能名称获取技能详细信息
        Args:
            move_name: 技能名称
        Returns:
            技能详细信息字典或None
        """
        return self.move_repo.get_move_by_name(move_name)