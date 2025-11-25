from typing import Optional, TypedDict, Dict, List, Any
from dataclasses import dataclass

@dataclass
class User:
    """代表一个完整的用户领域模型"""
    user_id: str
    nickname: Optional[str]
    level: int = 1
    exp: int = 0
    coins: int = 0
    init_selected: Optional[int] = None
    last_adventure_time: Optional[str] = None
    origin_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    isdel: Optional[int] = 0

@dataclass
class UserTeam:
    """代表一个用户的队伍领域模型"""
    user_id: str
    team_pokemon_ids: List[int] = None

@dataclass
class UserItemInfo:
    """代表一个用户的道具信息领域模型"""
    item_id: str
    quantity: int
    name_zh: str
    category_id: int
    description: str

@dataclass
class UserItems:
    """代表一个用户的道具领域模型"""
    user_id: str
    items: List[UserItemInfo] = None
