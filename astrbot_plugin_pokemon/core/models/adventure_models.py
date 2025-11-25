from __future__ import annotations
import datetime
from typing import Optional, TypedDict, Dict

from dataclasses import dataclass


@dataclass
class LocationPokemon:
    """区域宝可梦关联模型"""
    id: int
    location_id: int  # 区域ID
    pokemon_species_id: int  # 宝可梦种族ID
    encounter_rate: float = 10.0  # 遇见概率（百分比）
    min_level: int = 1  # 最低等级
    max_level: int = 10  # 最高等级

@dataclass
class LocationInfo:
    id: int
    name: str   # 区域名称
    description: Optional[str] = None  # 区域描述
    min_level: int = 1  # 最低推荐等级
    max_level: int = 100  # 最高推荐等级

@dataclass
class LocationTemplate:
    """冒险区域模型"""
    id: int
    name: str   # 区域名称
    description: Optional[str] = None  # 区域描述
    min_level: int = 1  # 最低推荐等级
    max_level: int = 100  # 最高推荐等级

@dataclass
class AdventureResult:
    success: bool
    message: str
    wild_pokemon: 'WildPokemonInfo' | None
    location: 'LocationInfo' | None

@dataclass
class BattleResult:
    success: bool
    message: str
