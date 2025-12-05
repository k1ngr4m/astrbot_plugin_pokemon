from __future__ import annotations
import datetime
from typing import Optional, TypedDict, Dict, List

from dataclasses import dataclass

from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.pokemon_models import WildPokemonInfo
from typing import Optional
from .trainer_models import BattleTrainer


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
    wild_pokemon: WildPokemonInfo
    location: LocationInfo
    trainer: Optional[BattleTrainer] = None  # 遇到的训练家信息

@dataclass
class BattleResult:
    user_pokemon: Dict[str, any]
    wild_pokemon: Dict[str, any]
    win_rates: Dict[str, float]
    result: str
    exp_details: Dict[str, any]
    battle_log: List[Dict[str, any]] = None  # 战斗日志，记录所有参与战斗的宝可梦及结果
    log_id: int = 0  # 战斗日志ID

@dataclass
class BattleMoveInfo:
    power: int
    accuracy: float
    type_name: str
    damage_class_id: int  # 2 for physical, 3 for special
    priority: int
    type_effectiveness: float
    stab_bonus: float
    move_id: int = 0
    move_name: str = ""
