import datetime
from typing import Optional, TypedDict, Dict

from dataclasses import dataclass

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