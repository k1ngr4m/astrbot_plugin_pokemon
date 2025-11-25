
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Shop:
    """代表一个商店领域模型"""
    id: int
    name: str
    description: str
    shop_type: str
    is_active: int
    created_at: datetime
    updated_at: datetime

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "shop_type": self.shop_type,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
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