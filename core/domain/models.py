import datetime
from typing import Optional, TypedDict, Dict

from dataclasses import dataclass

@dataclass
class Pokemon:
    """代表一种Pokemon的模版信息"""
    id: int
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

    # 兼容旧代码，保持 species_id 作为 id 的别名
    @property
    def species_id(self) -> int:
        return self.id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name_en": self.name_en,
            "name_cn": self.name_cn,
            "generation": self.generation,
            "base_hp": self.base_hp,
            "base_attack": self.base_attack,
            "base_defense": self.base_defense,
            "base_sp_attack": self.base_sp_attack,
            "base_sp_defense": self.base_sp_defense,
            "base_speed": self.base_speed,
            "height": self.height,
            "weight": self.weight,
            "description": self.description,
        }

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
    init_selected: Optional[int] = 0
    last_adventure_time: Optional[float] = None

@dataclass
class Shop:
    """代表一个商店领域模型"""
    id: int
    shop_code: str
    name: str
    description: str

    def to_dict(self):
        return {
            "id": self.id,
            "shop_code": self.shop_code,
            "name": self.name,
            "description": self.description
        }


@dataclass
class ShopItem:
    """代表一个商店物品领域模型"""
    id: int
    shop_id: int
    item_id: int
    price: int
    stock: int
    is_active: int = 1

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


class WildPokemonInfo(TypedDict):
    species_id: int
    name: str
    level: int
    encounter_rate: float
    hp: int
    attack: int
    defense: int
    sp_attack: int
    defense: int
    sp_defense: int
    speed: int
    ivs: Dict[str, int]
    evs: Dict[str, int]

class AreaInfo(TypedDict):
    area_code: str
    name: str

class AdventureResult(TypedDict):
    success: bool
    message: str
    wild_pokemon: WildPokemonInfo | None
    area: AreaInfo | None

class PokemonCreateResult(TypedDict):
    success: bool
    message: str
    base_stats: Dict[str, int] | None
    base_pokemon: Pokemon | None
    stats: Dict[str, int] | None
    ivs: Dict[str, int] | None
    evs: Dict[str, int] | None
    gender: str | None
    level: int | None
    exp: int | None
    moves: str | None
    is_shiny: int | None