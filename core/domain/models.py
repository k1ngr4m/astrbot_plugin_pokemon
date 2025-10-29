import datetime
from typing import Optional

from dataclasses import dataclass

@dataclass
class User:
    """代表一个完整的用户领域模型"""
    user_id: str
    created_at: datetime
    nickname: Optional[str]

    # --- 有默认值的字段放后面 ---
    coins: int = 0