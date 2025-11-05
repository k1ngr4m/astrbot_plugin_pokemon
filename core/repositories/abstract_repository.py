from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ..domain.models import (
    User, Pokemon,
)



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

    # 获取用户的队伍配置
    @abstractmethod
    def get_user_team(self, user_id: str) -> Optional[str]: pass

    # 更新用户的队伍配置
    @abstractmethod
    def update_user_team(self, user_id: str, team_data: str) -> None: pass


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