from dataclasses import dataclass

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