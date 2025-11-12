from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ..domain.models import (
    User, Pokemon,
)
from ..domain.area import AdventureArea, AreaPokemon



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

class AbstractItemTemplateRepository(ABC):
    """物品模板数据仓储接口"""
    # 获取Pokemon模板
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