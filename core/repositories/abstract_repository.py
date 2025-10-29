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


class AbstractItemTemplateRepository(ABC):
    """物品模板数据仓储接口"""
    # 获取Pokemon模板
    @abstractmethod
    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[Pokemon]: pass
    # 获取所有Pokemon模板
    @abstractmethod
    def get_all_pokemon(self) -> List[Pokemon]: pass

    @abstractmethod
    def add_pokemon_template(self, pokemon_data: Dict[str, Any]) -> Pokemon: pass