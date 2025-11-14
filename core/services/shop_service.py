from typing import Dict, List, Any
from ..repositories.abstract_repository import AbstractUserRepository

class ShopService:
    """处理商店业务逻辑"""

    def __init__(self, user_repo: AbstractUserRepository):
        self.user_repo = user_repo

    def get_shop_by_code(self, shop_code: str) -> Dict[str, Any]:
        """
        根据商店短码获取商店信息和商品列表
        Args:
            shop_code: 商店短码（如S001）
        Returns:
            包含商店信息和商品列表的字典
        """
        with self.user_repo._get_connection() as conn:
            cursor = conn.cursor()

            # 获取商店基本信息
            shop_sql = """
                SELECT id, shop_code, name, description
                FROM shops
                WHERE shop_code = ? AND shops.id IN (
                    SELECT DISTINCT shop_id
                    FROM shop_items
                    WHERE is_active = 1
                )
            """
            cursor.execute(shop_sql, (shop_code,))
            shop_row = cursor.fetchone()

            if not shop_row:
                return {
                    "success": False,
                    "message": f"❌ 商店 {shop_code} 不存在或暂无商品出售！"
                }

            shop_info = dict(shop_row)

            # 获取商店的商品列表
            items_sql = """
                SELECT si.price, si.stock, i.name, i.type, i.description, i.rarity
                FROM shop_items si
                JOIN items i ON si.item_id = i.id
                WHERE si.shop_id = ? AND si.is_active = 1
                ORDER BY i.type, i.rarity DESC, i.name
            """
            cursor.execute(items_sql, (shop_info["id"],))
            items_rows = cursor.fetchall()

            if not items_rows:
                return {
                    "success": False,
                    "message": f"❌ 商店 {shop_code} 当前没有商品出售！"
                }

            items = []
            for row in items_rows:
                items.append({
                    "price": row[0],
                    "stock": row[1],
                    "name": row[2],
                    "type": row[3],
                    "description": row[4],
                    "rarity": row[5]
                })

            shop_info["items"] = items

            return {
                "success": True,
                "shop": shop_info,
                "message": f"🏪 {shop_info['name']} - {shop_info['shop_code']}"
            }

    def purchase_item(self, user_id: str, shop_code: str, item_name: str, quantity: int) -> Dict[str, Any]:
        """
        购买商店商品
        Args:
            user_id: 用户ID
            shop_code: 商店短码
            item_name: 商品名称
            quantity: 购买数量
        Returns:
            购买结果
        """
        # 首先验证用户是否存在
        user = self.user_repo.get_by_id(user_id)
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

        with self.user_repo._get_connection() as conn:
            cursor = conn.cursor()

            # 获取商店ID
            shop_sql = "SELECT id FROM shops WHERE shop_code = ?"
            cursor.execute(shop_sql, (shop_code,))
            shop_row = cursor.fetchone()
            if not shop_row:
                return {
                    "success": False,
                    "message": f"❌ 商店 {shop_code} 不存在！"
                }
            shop_id = shop_row[0]

            # 获取商店商品信息 - 现在按商品名称匹配
            item_sql = """
                SELECT si.id as shop_item_id, si.price, si.stock, i.id as item_id, i.name
                FROM shop_items si
                JOIN items i ON si.item_id = i.id
                WHERE si.shop_id = ? AND i.name = ? AND si.is_active = 1
            """
            cursor.execute(item_sql, (shop_id, item_name))
            item_row = cursor.fetchone()

            if not item_row:
                return {
                    "success": False,
                    "message": f"❌ 商品 {item_name} 在商店 {shop_code} 中不存在或已下架！"
                }

            shop_item_id = item_row[0]
            unit_price = item_row[1]
            stock = item_row[2]
            item_id = item_row[3]
            item_name = item_row[4]

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
                    cursor.execute(
                        "UPDATE shop_items SET stock = ? WHERE id = ?",
                        (new_stock, shop_item_id)
                    )

                # 3. 添加用户道具
                self.user_repo.add_user_item(user_id, item_id, quantity)

                conn.commit()

                return {
                    "success": True,
                    "message": f"✅ 购买成功！花费 {total_price} 金币购买了 {quantity} 个 {item_name}",
                    "item_name": item_name,
                    "quantity": quantity,
                    "total_price": total_price,
                    "new_coins": new_coins
                }

            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": f"❌ 购买失败: {str(e)}"
                }