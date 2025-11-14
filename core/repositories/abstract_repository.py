from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ..domain.models import (
    User, Pokemon, Shop, ShopItem
)
from ..domain.models import AdventureArea, AreaPokemon



class AbstractUserRepository(ABC):
    """用户数据仓储接口"""
    # 根据ID获取用户
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]: pass

    # 检查用户是否存在
    @abstractmethod
    def check_exists(self, user_id: str) -> bool: pass

    # 新增一个用户
    @abstractmethod
    def add(self, user: User) -> None: pass

    # 创建用户宝可梦记录
    @abstractmethod
    def create_user_pokemon(self, user_id: str, species_id: int, nickname: Optional[str] = None) -> int: pass

    # 更新用户的初始选择状态
    @abstractmethod
    def update_init_select(self, user_id: str, pokemon_id: int) -> None: pass

    # 获取用户的所有宝可梦
    @abstractmethod
    def get_user_pokemon(self, user_id: str) -> List[Dict[str, Any]]: pass

    @abstractmethod
    def get_user_pokemon_by_id(self, pokemon_id: str) -> Optional[Dict[str, Any]]: pass

    @abstractmethod
    def get_user_pokemon_by_shortcode(self, shortcode: str) -> Optional[Dict[str, Any]]: pass

    @abstractmethod
    def get_user_pokemon_by_numeric_id(self, pokemon_numeric_id: int) -> Optional[Dict[str, Any]]: pass

    @abstractmethod
    def update_user_exp(self, level: int, exp: int, user_id: str) -> None: pass

    # 检查用户今日是否已签到
    @abstractmethod
    def has_user_checked_in_today(self, user_id: str, today: str) -> bool: pass

    # 为用户添加签到记录
    @abstractmethod
    def add_user_checkin(self, user_id: str, checkin_date: str, gold_reward: int, item_reward_id: int = 1, item_quantity: int = 1) -> None: pass

    # 更新用户的金币数量
    @abstractmethod
    def update_user_coins(self, user_id: str, coins: int) -> None: pass

    # 为用户添加物品
    @abstractmethod
    def add_user_item(self, user_id: str, item_id: int, quantity: int) -> None: pass

    # 获取用户的所有物品
    @abstractmethod
    def get_user_items(self, user_id: str) -> list: pass

class AbstractPokemonRepository(ABC):
    """宝可梦数据仓储接口"""
    # 获取宝可梦模板
    @abstractmethod
    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[Pokemon]: pass
    # 获取所有Pokemon模板
    @abstractmethod
    def get_all_pokemon(self) -> List[Pokemon]: pass

    @abstractmethod
    def add_pokemon_template(self, pokemon_data: Dict[str, Any]) -> None: pass

    @abstractmethod
    def add_pokemon_type_template(self, type_data: Dict[str, Any]) -> None: pass

    @abstractmethod
    def add_pokemon_species_type_template(self, species_type_data: Dict[str, Any]) -> None: pass

    @abstractmethod
    def add_pokemon_evolution_template(self, evolution_data: Dict[str, Any]) -> None: pass

    @abstractmethod
    def add_item_template(self, item_data: Dict[str, Any]) -> None: pass

    @abstractmethod
    def add_pokemon_move_template(self, move_data: Dict[str, Any]) -> None: pass

    @abstractmethod
    def add_pokemon_species_move_template(self, species_move_data: Dict[str, Any]) -> None: pass

    @abstractmethod
    def get_pokemon_types(self, species_id: int) -> List[str]: pass

    @abstractmethod
    def update_pokemon_exp(self, level: int, exp: int, pokemon_id: int, user_id: str) -> None: pass

    @abstractmethod
    def update_pokemon_attributes(self, attributes: Dict[str, int], pokemon_id: int, user_id: str) -> None: pass

class AbstractTeamRepository(ABC):
    """队伍数据仓储接口"""
    # 获取用户的队伍配置
    @abstractmethod
    def get_user_team(self, user_id: str) -> Optional[str]: pass

    # 更新用户的队伍配置
    @abstractmethod
    def update_user_team(self, user_id: str, team_data: str) -> None: pass

class AbstractAreaRepository(ABC):
    """冒险区域数据仓储接口"""
    @abstractmethod
    def get_all_areas(self) -> List[AdventureArea]: pass

    @abstractmethod
    def get_area_by_code(self, area_code: str) -> Optional[AdventureArea]: pass

    @abstractmethod
    def get_area_pokemon_by_area_id(self, area_id: int) -> List[AreaPokemon]: pass

    @abstractmethod
    def get_area_pokemon_by_area_code(self, area_code: str) -> List[AreaPokemon]: pass

    @abstractmethod
    def add_area(self, area: AdventureArea) -> int: pass

    @abstractmethod
    def add_area_pokemon(self, area_pokemon: AreaPokemon) -> int: pass

class AbstractShopRepository(ABC):
    """商店数据仓储接口"""
    @abstractmethod
    def add_shop(self, shop: Shop) -> None: pass

    @abstractmethod
    def add_shop_item(self, shop_item: ShopItem) -> None: pass

    @abstractmethod
    def get_shop_by_code(self, shop_code: str) -> Optional[Dict[str, Any]]: pass

    @abstractmethod
    def get_shop_items_by_shop_id(self, shop_id: int) -> List[Dict[str, Any]]: pass

    @abstractmethod
    def check_shop_exists_by_code(self, shop_code: str) -> bool: pass