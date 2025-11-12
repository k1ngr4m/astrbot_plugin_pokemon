from dataclasses import dataclass
from typing import Optional, List

@dataclass
class AdventureArea:
    """冒险区域模型"""
    id: int
    area_code: str  # 区域短码（A开头的三位数，如A001）
    name: str  # 区域名称
    description: Optional[str] = None  # 区域描述
    min_level: int = 1  # 最低推荐等级
    max_level: int = 100  # 最高推荐等级

@dataclass
class AreaPokemon:
    """区域宝可梦关联模型"""
    id: int
    area_id: int  # 区域ID
    pokemon_species_id: int  # 宝可梦种族ID
    encounter_rate: float = 10.0  # 遇见概率（百分比）
    min_level: int = 1  # 最低等级
    max_level: int = 10  # 最高等级