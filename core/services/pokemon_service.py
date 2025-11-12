from typing import Dict, Any, List
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractTeamRepository,
)

from ..utils import get_now, get_today
from ..domain.models import User


class PokemonService:
    """封装与宝可梦相关的业务逻辑"""
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

