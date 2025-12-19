from typing import Dict, Any, Optional

from ....infrastructure.repositories.abstract_repository import AbstractAbilityRepository
from ...models.common_models import BaseResult
from ...models.pokemon_models import PokemonAbility
from ....interface.response.answer_enum import AnswerEnum


class AbilityService:
    """特性相关业务逻辑服务"""

    def __init__(self, ability_repo: AbstractAbilityRepository):
        self.ability_repo = ability_repo

    def get_ability_by_id(self, ability_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取特性信息"""
        return self.ability_repo.get_ability_by_id(ability_id)

    def get_all_abilities(self) -> list[Dict[str, Any]]:
        """获取所有特性信息"""
        return self.ability_repo.get_all_abilities()