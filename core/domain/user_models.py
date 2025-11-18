import datetime
from typing import Optional, TypedDict, Dict, List

from dataclasses import dataclass

from lark_oapi.api.search.v2 import ListDataSourceRequest

from .pokemon_models import UserPokemonInfo


@dataclass
class User:
    """代表一个完整的用户领域模型"""
    user_id: str
    nickname: Optional[str]
    level: int
    exp: int
    coins: int
    created_at: datetime
    init_selected: Optional[int] = None
    last_adventure_time: Optional[int] = None

@dataclass
class UserTeam:
    """代表一个用户的队伍领域模型"""
    user_id: str
    team_pokemon_ids: List[int] = None