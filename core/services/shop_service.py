from typing import Dict, List, Any
from ..repositories.abstract_repository import AbstractUserRepository, AbstractShopRepository


class ShopService:
    """处理商店业务逻辑"""

    def __init__(self, user_repo: AbstractUserRepository, shop_repo: AbstractShopRepository):
        self.user_repo = user_repo
        self.shop_repo = shop_repo

    def get_active_shops(self) -> List[Dict[str, Any]]:
        """
        获取所有当前活跃的商店
        Returns:
            活跃商店列表
        """
        shops = self.shop_repo.get_active_shops()
        return [shop.to_dict() for shop in shops]

    def get_shop_by_code(self, shop_code: str) -> Dict[str, Any]:
        """
        根据商店短码获取商店信息和商品列表
        Args:
            shop_code: 商店短码（如S001）
        Returns:
            包含商店信息和商品列表的字典
        """
        shop = self.shop_repo.get_shop_by_code(shop_code)
        if not shop:
            return {
                "success": False,
                "message": f"❌ 商店 {shop_code} 不存在或暂无商品出售！"
            }

        shop_info = shop.to_dict()

        items_list = self.shop_repo.get_shop_items_by_shop_id(shop_info["id"])

        if not items_list:
            return {
                "success": False,
                "message": f"❌ 商店 {shop_code} 当前没有商品出售！"
            }
        print(f"items_list: {items_list}")
        items = []
        for item in items_list:
            items.append({
                "price": item["price"],
                "stock": item["stock"],
                "name": item["name"],
                "type": item["type"],
                "description": item["description"],
                "rarity": item["rarity"]
            })

        shop_info["items"] = items

        return {
            "success": True,
            "shop": shop_info,
            "message": f"🏪 {shop_info['name']} - {shop_info['shop_code']}"
        }

    def purchase_item(self, user_id: str, shop_code: str, item_id: str, quantity: int) -> Dict[str, Any]:
        """
        购买商店商品
        Args:
            user_id: 用户ID
            shop_code: 商店短码
            item_id: 商品ID
            quantity: 购买数量
        Returns:
            购买结果
        """
        # 首先验证用户是否存在
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "message": "❌ 用户不存在，请先注册！"
            }

        # 检查数量是否合法
        if quantity <= 0:
            return {
                "success": False,
                "message": "❌ 购买数量必须大于0！"
            }

        shop = self.shop_repo.get_shop_by_code(shop_code)
        if not shop:
            return {
                "success": False,
                "message": f"❌ 商店 {shop_code} 不存在！"
            }
        shop_id = shop.id

        # 获取商店商品信息 -
        try:
            item_id_int = int(item_id)
        except ValueError:
            return {
                "success": False,
                "message": f"❌ 商品ID必须是数字！"
            }
        shop_item = self.shop_repo.get_a_shop_item_by_id(item_id_int, shop_id)
        if not shop_item:
            return {
                "success": False,
                "message": f"❌ 商品 {item_id} 在商店 {shop_code} 中不存在或已下架！"
            }

        shop_item_id = shop_item["shop_item_id"]
        unit_price = shop_item["price"]
        stock = shop_item["stock"]
        item_id = shop_item["item_id"]
        item_name = shop_item["name"]

        # 检查库存
        if stock != -1 and stock < quantity:
            return {
                "success": False,
                "message": f"❌ 商品 {item_name} 库存不足！当前库存: {stock}，需要: {quantity}"
            }

        # 计算总价
        total_price = unit_price * quantity

        # 检查用户金币是否足够
        if user.coins < total_price:
            return {
                "success": False,
                "message": f"❌ 金币不足！需要 {total_price} 金币，当前余额: {user.coins} 金币"
            }

        # 开始购买流程
        try:
            # 1. 更新用户金币
            new_coins = user.coins - total_price
            self.user_repo.update_user_coins(user_id, new_coins)

            # 2. 更新商店库存（如果库存有限）
            if stock != -1:
                new_stock = stock - quantity
                self.shop_repo.update_shop_item_stock(shop_item_id, new_stock)

            # 3. 添加用户道具
            self.user_repo.add_user_item(user_id, item_id, quantity)

            return {
                "success": True,
                "message": f"✅ 购买成功！花费 {total_price} 金币购买了 {quantity} 个 {item_name}",
                "item_name": item_name,
                "quantity": quantity,
                "total_price": total_price,
                "new_coins": new_coins
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 购买失败: {str(e)}"
            }