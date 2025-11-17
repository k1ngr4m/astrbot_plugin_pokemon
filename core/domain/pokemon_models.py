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

@dataclass
class PokemonIVs:
    """代表一个宝可梦的个体值"""
    hp_iv: int
    attack_iv: int
    defense_iv: int
    sp_attack_iv: int
    sp_defense_iv: int
    speed_iv: int

@dataclass
class PokemonEVs:
    """代表一个宝可梦的环境值"""
    hp_ev: int
    attack_ev: int
    defense_ev: int
    sp_attack_ev: int
    sp_defense_ev: int
    speed_ev: int

@dataclass
class PokemonMoves:
    """代表一个宝可梦的技能"""
    move_1: int
    move_2: int
    move_3: int
    move_4: int

@dataclass
class PokemonBaseStats(PokemonStats):
    pass
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
    is_shiny: int
    stats: PokemonStats
    ivs: PokemonIVs
    evs: PokemonEVs
    moves: PokemonMoves | None

@dataclass
class PokemonCreateResult:
    success: bool
    message: str
    data: Optional[PokemonDetail] = None

    def __getitem__(self, item):
        return getattr(self, item)

@dataclass
class UserPokemonInfo:
    species_id: int
    name: str
    gender: str
    level: int
    exp: int
    is_shiny: int
    stats: PokemonStats
    ivs: PokemonIVs
    evs: PokemonEVs
    moves: PokemonMoves

    def __getitem__(self, item):
        return getattr(self, item)

@dataclass
class WildPokemonInfo:
    species_id: int
    name: str
    gender: str
    level: int
    exp: int
    is_shiny: int
    stats: PokemonStats
    ivs: PokemonIVs
    evs: PokemonEVs
    moves: PokemonMoves
    encounter_rate: float
