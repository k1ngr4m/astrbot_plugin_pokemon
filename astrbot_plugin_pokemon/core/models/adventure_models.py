from __future__ import annotations
import datetime
from typing import Optional, TypedDict, Dict, List

from dataclasses import dataclass

from .trainer_models import BattleTrainer
from ..models.pokemon_models import WildPokemonInfo, UserPokemonInfo
from typing import Union


@dataclass
class BattleMoveInfo:
    power: int
    accuracy: float
    type_name: str
    damage_class_id: int  # 2 for physical, 3 for special
    priority: int
    type_effectiveness: float
    stab_bonus: float
    max_pp: int = 0  # 技能最大使用次数
    current_pp: int = 0  # 当前剩余使用次数
    move_id: int = 0
    move_name: str = ""
    # 预加载的技能属性变化数据，避免在战斗循环中查库
    stat_changes: List[Dict] = None  # 技能对属性的影响: [{'stat_id': int, 'change': int}, ...]
    target_id: int = 0  # 技能目标ID，用于判断影响对象
    meta_category_id: int = 0  # 技能元类别ID，用于区分特殊逻辑类型
    ailment_chance: float = 0.0  # 异常状态触发概率
    meta_ailment_id: int = 0  # 异常状态ID，用于触发异常状态效果
    healing: float = 0.0  # 技能回复量，正数为回复，负数为消耗
    stat_chance: float = 0.0  # 能力变化触发概率
    drain: float = 0.0  # 吸收伤害比例（百分比），用于吸血技能
    # 新增：连续攻击字段
    min_hits: int = 1  # 最少攻击次数
    max_hits: int = 1  # 最多攻击次数



@dataclass
class BattleContext:
    pokemon: Union[UserPokemonInfo, WildPokemonInfo]
    moves: List[BattleMoveInfo]
    types: List[str]
    current_hp: int
    is_user: bool



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
    is_pokemon_caught: bool = False  # 该宝可梦物种是否已被用户捕捉过

@dataclass
class BattleResult:
    user_pokemon: Dict[str, any]
    wild_pokemon: Dict[str, any]
    win_rates: Dict[str, float]
    result: str
    exp_details: Dict[str, any]
    battle_log: List[Dict[str, any]] = None  # 战斗日志，记录所有参与战斗的宝可梦及结果
    log_id: int = 0  # 战斗日志ID
    is_trainer_battle: bool = False  # 是否为训练家战斗
    money_reward: int = 0  # 金钱奖励
    user_battle_exp_result: Dict[str, any] = None  # 用户战斗经验奖励结果

