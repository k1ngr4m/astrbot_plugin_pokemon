from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional


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
    move_1: int
    move_2: int
    move_3: int
    move_4: int

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
class PokemonTemplate:
    """代表一种Pokemon的模版信息"""
    id: int
    name_en: str
    name_cn: str
    generation: int
    base_stats: PokemonBaseStats
    height: float
    weight: float
    description: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name_en": self.name_en,
            "name_cn": self.name_cn,
            "generation": self.generation,
            "base_stats": self.base_stats.__dict__,
            "height": self.height,
            "weight": self.weight,
            "description": self.description,
        }

@dataclass
class PokemonDetail:
    base_pokemon: PokemonTemplate
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
    pokemon_species_id: int
    pokemon_name: str
    pokemon_level: int
    pokemon_info: WildPokemonInfo
    area_code: str
    area_name: str
    encounter_time: Optional[str] = None
    is_captured: Optional[int] = None
    is_battled: Optional[int] = None
    battle_result: Optional[str] = None
    encounter_rate: Optional[float] = None
    created_at: Optional[str] = None
    isdel: Optional[int] = 0

