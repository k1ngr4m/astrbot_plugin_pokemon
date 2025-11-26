from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PokemonStats:
    """代表一个宝可梦的基础数据"""
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int

    def __getitem__(self, item):
        return getattr(self, item)

    def model_dump_json(self):
        # 返回string字符串
        return json.dumps(self.__dict__)


@dataclass
class PokemonIVs:
    """代表一个宝可梦的个体值"""
    hp_iv: int
    attack_iv: int
    defense_iv: int
    sp_attack_iv: int
    sp_defense_iv: int
    speed_iv: int

    def __getitem__(self, item):
        return getattr(self, item)

@dataclass
class PokemonEVs:
    """代表一个宝可梦的环境值"""
    hp_ev: int
    attack_ev: int
    defense_ev: int
    sp_attack_ev: int
    sp_defense_ev: int
    speed_ev: int

    def __getitem__(self, item):
        return getattr(self, item)

@dataclass
class PokemonMoves:
    """代表一个宝可梦的技能"""
    move1_id: int
    move2_id: int
    move3_id: int
    move4_id: int

    def __getitem__(self, item):
        return getattr(self, item)

@dataclass
class PokemonBaseStats:
    base_hp: int
    base_attack: int
    base_defense: int
    base_sp_attack: int
    base_sp_defense: int
    base_speed: int

    def __getitem__(self, item):
        return getattr(self, item)

@dataclass
class PokemonSpecies:
    """代表一种Pokemon的模版信息"""
    id: int
    name_en: str
    name_zh: str
    generation_id: int
    base_stats: PokemonBaseStats
    height: float
    weight: float
    description: str
    base_experience: Optional[int] = None
    gender_rate: Optional[int] = None
    capture_rate: Optional[int] = None
    growth_rate_id: Optional[int] = None
    orders: Optional[int] = None
    isdel: Optional[int] = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name_en": self.name_en,
            "name_zh": self.name_zh,
            "generation_id": self.generation_id,
            "base_stats": self.base_stats.__dict__,
            "height": self.height,
            "weight": self.weight,
            "description": self.description,
            "base_experience": self.base_experience,
            "gender_rate": self.gender_rate,
            "capture_rate": self.capture_rate,
            "growth_rate_id": self.growth_rate_id,
            "orders": self.orders,
            "isdel": self.isdel,
        }

@dataclass
class PokemonDetail:
    base_pokemon: PokemonSpecies
    gender: str
    level: int
    exp: int
    stats: PokemonStats
    ivs: PokemonIVs
    evs: PokemonEVs
    moves: PokemonMoves | None

    def __getitem__(self, item):
        return getattr(self, item)

@dataclass
class PokemonCreateResult:
    success: bool
    message: str
    data: Optional[PokemonDetail] = None

    def __getitem__(self, item):
        return getattr(self, item)

@dataclass
class UserPokemonInfo:
    id: int
    species_id: int
    name: str
    gender: str
    level: int
    exp: int
    stats: PokemonStats
    ivs: PokemonIVs
    evs: PokemonEVs
    moves: PokemonMoves
    caught_time: Optional[str] = None

    def __getitem__(self, item):
        return getattr(self, item)

    def to_dict(self):
        def get_dict(obj):
            if obj is None:
                return None
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif hasattr(obj, '__dataclass_fields__'):
                # For dataclass objects
                return {f: getattr(obj, f) for f in obj.__dataclass_fields__}
            else:
                return vars(obj)

        return {
            "id": self.id,
            "species_id": self.species_id,
            "name": self.name,
            "gender": self.gender,
            "level": self.level,
            "exp": self.exp,
            "stats": get_dict(self.stats),
            "ivs": get_dict(self.ivs),
            "evs": get_dict(self.evs),
            "moves": get_dict(self.moves),
            "caught_time": self.caught_time,
        }

@dataclass
class WildPokemonInfo:
    id: int
    species_id: int
    name: str
    gender: str
    level: int
    exp: int
    stats: PokemonStats
    ivs: PokemonIVs
    evs: PokemonEVs
    moves: PokemonMoves | None

    def to_dict(self):
        def get_dict(obj):
            if obj is None:
                return None
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif hasattr(obj, '__dataclass_fields__'):
                # For dataclass objects
                return {f: getattr(obj, f) for f in obj.__dataclass_fields__}
            else:
                return vars(obj)

        return {
            "id": self.id,
            "species_id": self.species_id,
            "name": self.name,
            "gender": self.gender,
            "level": self.level,
            "exp": self.exp,
            "stats": get_dict(self.stats),
            "ivs": get_dict(self.ivs),
            "evs": get_dict(self.evs),
            "moves": get_dict(self.moves),
        }

    def model_dump_json(self):
        return self.to_dict()


@dataclass
class WildPokemonEncounterLog:
    id: int
    user_id: str
    wild_pokemon_id: int
    location_id: int
    encounter_time: Optional[str] = None
    is_captured: Optional[int] = None
    is_battled: Optional[int] = None
    battle_result: Optional[str] = None
    encounter_rate: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    isdel: Optional[int] = 0


@dataclass
class PokemonType:
    """宝可梦属性类型"""
    id: int
    name_en: str
    name_zh: str
    isdel: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name_en": self.name_en,
            "name_zh": self.name_zh,
            "isdel": self.isdel,
        }


@dataclass
class PokemonSpeciesType:
    """宝可梦种族与属性对应关系"""
    species_id: int
    type_id: int
    isdel: int = 0

    def to_dict(self) -> dict:
        return {
            "species_id": self.species_id,
            "type_id": self.type_id,
            "isdel": self.isdel,
        }


@dataclass
class PokemonMove:
    """宝可梦技能定义"""
    id: int
    name: str
    type_id: Optional[int] = None
    category: Optional[str] = None
    power: Optional[int] = None
    accuracy: Optional[int] = None
    pp: Optional[int] = None
    description: Optional[str] = None
    isdel: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type_id": self.type_id,
            "category": self.category,
            "power": self.power,
            "accuracy": self.accuracy,
            "pp": self.pp,
            "description": self.description,
            "isdel": self.isdel,
        }


@dataclass
class Item:
    """道具定义"""
    id: int
    name: str
    rarity: int = 1
    price: int = 0
    type: str = "Misc"
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    isdel: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "rarity": self.rarity,
            "price": self.price,
            "type": self.type,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "isdel": self.isdel,
        }


@dataclass
class PokemonEvolution:
    """宝可梦进化关系"""
    id: int
    evolved_species_id: int
    pre_species_id: Optional[int] = None
    evolution_trigger_id: Optional[int] = None
    trigger_item_id: Optional[int] = None
    minimum_level: int = 0
    gender_id: Optional[int] = None
    location_id: Optional[int] = None
    held_item_id: Optional[int] = None
    time_of_day: Optional[str] = None
    known_move_id: Optional[int] = None
    known_move_type_id: Optional[int] = None
    minimum_happiness: int = 0
    minimum_beauty: int = 0
    minimum_affection: int = 0
    relative_physical_stats: Optional[int] = None
    party_species_id: Optional[int] = None
    party_type_id: Optional[int] = None
    trade_species_id: Optional[int] = None
    needs_overworld_rain: int = 0
    turn_upside_down: int = 0
    region_id: Optional[int] = None
    base_form_id: Optional[int] = None
    isdel: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "evolved_species_id": self.evolved_species_id,
            "pre_species_id": self.pre_species_id,
            "evolution_trigger_id": self.evolution_trigger_id,
            "trigger_item_id": self.trigger_item_id,
            "minimum_level": self.minimum_level,
            "gender_id": self.gender_id,
            "location_id": self.location_id,
            "held_item_id": self.held_item_id,
            "time_of_day": self.time_of_day,
            "known_move_id": self.known_move_id,
            "known_move_type_id": self.known_move_type_id,
            "minimum_happiness": self.minimum_happiness,
            "minimum_beauty": self.minimum_beauty,
            "minimum_affection": self.minimum_affection,
            "relative_physical_stats": self.relative_physical_stats,
            "party_species_id": self.party_species_id,
            "party_type_id": self.party_type_id,
            "trade_species_id": self.trade_species_id,
            "needs_overworld_rain": self.needs_overworld_rain,
            "turn_upside_down": self.turn_upside_down,
            "region_id": self.region_id,
            "base_form_id": self.base_form_id,
            "isdel": self.isdel,
        }


@dataclass
class PokemonSpeciesMove:
    """宝可梦种族-技能学习关系"""
    species_id: int
    move_id: int
    learn_method: str
    learn_value: str
    isdel: int = 0

    def to_dict(self) -> dict:
        return {
            "species_id": self.species_id,
            "move_id": self.move_id,
            "learn_method": self.learn_method,
            "learn_value": self.learn_value,
            "isdel": self.isdel,
        }


@dataclass
class Location:
    """冒险地点"""
    id: int
    name: str
    description: Optional[str] = None
    min_level: int = 1
    max_level: int = 100
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    isdel: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "isdel": self.isdel,
        }


@dataclass
class PokemonLocation:
    """地点宝可梦关联"""
    id: int
    location_id: int
    pokemon_species_id: int
    encounter_rate: float = 10.0
    min_level: int = 1
    max_level: int = 10
    isdel: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "location_id": self.location_id,
            "pokemon_species_id": self.pokemon_species_id,
            "encounter_rate": self.encounter_rate,
            "min_level": self.min_level,
            "max_level": self.max_level,
            "isdel": self.isdel,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Pokemon:
    """完整的宝可梦信息"""
    id: int
    name_en: str
    name_zh: str
    generation: int
    base_stats: PokemonBaseStats
    height: float
    weight: float
    description: str
    base_experience: Optional[int] = None
    gender_rate: Optional[int] = None
    capture_rate: Optional[int] = None
    growth_rate_id: Optional[int] = None
    types: List[PokemonType] = None
    evolutions_from: List[PokemonEvolution] = None  # 它可以进化的形式
    evolutions_to: List[PokemonEvolution] = None    # 它可以从前一个形态进化而来
    isdel: int = 0

    def __post_init__(self):
        if self.types is None:
            self.types = []
        if self.evolutions_from is None:
            self.evolutions_from = []
        if self.evolutions_to is None:
            self.evolutions_to = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name_en": self.name_en,
            "name_zh": self.name_zh,
            "generation": self.generation,
            "base_stats": self.base_stats.__dict__ if self.base_stats else None,
            "height": self.height,
            "weight": self.weight,
            "description": self.description,
            "base_experience": self.base_experience,
            "gender_rate": self.gender_rate,
            "capture_rate": self.capture_rate,
            "growth_rate_id": self.growth_rate_id,
            "types": [t.to_dict() for t in self.types] if self.types else [],
            "evolutions_from": [e.to_dict() for e in self.evolutions_from] if self.evolutions_from else [],
            "evolutions_to": [e.to_dict() for e in self.evolutions_to] if self.evolutions_to else [],
            "isdel": self.isdel,
        }


@dataclass
class PokemonGrowthRate:
    """宝可梦升级速率组"""
    id: int
    name: str
    formula: str
    isdel: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "formula": self.formula,
            "isdel": self.isdel,
        }

