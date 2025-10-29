from abc import ABC, abstractmethod
from typing import Optional
from ..domain.models import (
    User,
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