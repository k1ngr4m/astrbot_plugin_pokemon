from typing import Dict, Any, List
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractItemTemplateRepository, AbstractTeamRepository,
)

from ..utils import get_now, get_today
from ..domain.models import User


class PokemonService:
    """封装与宝可梦相关的业务逻辑"""
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

