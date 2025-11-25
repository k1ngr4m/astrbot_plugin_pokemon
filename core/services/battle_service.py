import math
from typing import Dict, Any, Tuple, List

from ..domain.pokemon_models import WildPokemonInfo, UserPokemonInfo
from ..domain.user_models import UserTeam
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository,
)

from .exp_service import ExpService

class BattleService:
    """
    封装宝可梦战斗相关的业务逻辑
    包含属性克制计算、战力评分模型和胜率计算
    """

    def __init__(
        self,
        user_repo: AbstractUserRepository,
        pokemon_repo: AbstractPokemonRepository,
        team_repo,
        config: Dict[str, Any],
        exp_service = ExpService
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.team_repo = team_repo
        self.config = config
        self.exp_service = exp_service


