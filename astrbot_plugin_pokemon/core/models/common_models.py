from dataclasses import dataclass
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

@dataclass
class BaseResult(Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None