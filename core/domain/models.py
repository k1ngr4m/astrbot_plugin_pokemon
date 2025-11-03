import datetime
from typing import Optional

from dataclasses import dataclass

@dataclass
class Pokemon:
    """代表一种Pokemon的模版信息"""
    species_id: int
    name_en: str
    name_cn: str
    generation: int
    base_hp: int
    base_attack: int
    base_defense: int
    base_sp_attack: int
    base_sp_defense: int
    base_speed: int
    height: float
    weight: float
    description: str

@dataclass
class User:
    """代表一个完整的用户领域模型"""
    user_id: str
    created_at: datetime
    nickname: Optional[str]

    # --- 有默认值的字段放后面 ---
    coins: int = 0
    level: int = 1
    exp: int = 0
    init_select: Optional[int] = 0
