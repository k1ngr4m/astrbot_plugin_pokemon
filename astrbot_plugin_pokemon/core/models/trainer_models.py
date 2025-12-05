"""训练家相关的数据模型"""

from dataclasses import dataclass
from typing import List, Optional
from .pokemon_models import PokemonSpecies, UserPokemonInfo

@dataclass
class Trainer:
    """训练家数据模型"""
    id: int
    name: str
    trainer_class: str  # 训练家职业 (如: 短裤小子, 捕虫少年, 道馆馆主等)
    base_payout: int = 0  # 基础赏金
    description: Optional[str] = None
    isdel: int = 0

@dataclass
class TrainerPokemon:
    """训练家拥有的宝可梦数据模型"""
    id: int
    trainer_id: int
    pokemon_species_id: int
    level: int
    position: int = 0  # 在队伍中的位置 (0-2)
    isdel: int = 0
    pokemon_species: Optional[PokemonSpecies] = None  # 关联的宝可梦种类信息

@dataclass
class TrainerEncounter:
    """玩家与训练家遭遇记录数据模型"""
    id: int
    user_id: str
    trainer_id: int
    encounter_time: str
    battle_result: Optional[str] = None  # 'win', 'lose', 'not_fought'
    isdel: int = 0

@dataclass
class TrainerLocation:
    """训练家位置数据模型"""
    id: int
    trainer_id: int
    location_id: int
    encounter_rate: float = 0.1  # 遭遇概率
    isdel: int = 0

@dataclass
class TrainerDetail:
    """训练家详细信息数据模型"""
    trainer: Trainer
    pokemon_list: List[TrainerPokemon]
    location_ids: List[int]

@dataclass
class BattleTrainer:
    """用于战斗的训练家数据模型"""
    trainer: Trainer
    pokemon_list: List[UserPokemonInfo]  # 训练家的宝可梦队伍，已经实例化为UserPokemonInfo