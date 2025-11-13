import random
from typing import Dict, Any
from ..repositories.abstract_repository import AbstractUserRepository
from ..utils import get_today


class CheckinService:
    """处理用户签到业务逻辑"""

    def __init__(self, user_repo: AbstractUserRepository):
        self.user_repo = user_repo

    def checkin(self, user_id: str) -> Dict[str, Any]:
        """
        用户签到
        Args:
            user_id: 用户ID
        Returns:
            包含签到结果的字典
        """
        # 获取今天的日期
        today = get_today().strftime("%Y-%m-%d")

        # 检查用户今天是否已经签到
        if self.user_repo.has_user_checked_in_today(user_id, today):
            return {
                "success": False,
                "message": "❌ 今天您已经签到过了，请明天再来！"
            }

        # 检查用户是否存在
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {
                "success": False,
                "message": "❌ 用户不存在，请先注册！"
            }

        # 生成随机金币奖励（100-300之间）
        gold_reward = random.randint(100, 300)

        # 道具奖励：普通精灵球（ID=1），数量=1
        item_reward_id = 1
        item_quantity = 1

        # 更新用户金币
        new_coins = user.coins + gold_reward
        self.user_repo.update_user_coins(user_id, new_coins)

        # 为用户添加道具
        self.user_repo.add_user_item(user_id, item_reward_id, item_quantity)

        # 记录签到信息
        self.user_repo.add_user_checkin(user_id, today, gold_reward, item_reward_id, item_quantity)

        return {
            "success": True,
            "message": f"✅ 签到成功！\n获得了 {gold_reward} 金币 💰\n获得了 普通精灵球 x{item_quantity} 🎒\n当前金币总数：{new_coins}",
            "gold_reward": gold_reward,
            "item_reward": {
                "id": item_reward_id,
                "quantity": item_quantity
            }
        }