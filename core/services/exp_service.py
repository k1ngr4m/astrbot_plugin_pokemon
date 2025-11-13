from typing import Dict, Any
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractItemTemplateRepository, AbstractTeamRepository,
)

class ExpService:
    """经验系统服务类，处理用户和宝可梦的经验值逻辑"""

    def __init__(
        self,
        user_repo: AbstractUserRepository,
        item_template_repo: AbstractItemTemplateRepository,
        team_repo: AbstractTeamRepository,
        config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.item_template_repo = item_template_repo
        self.team_repo = team_repo
        self.config = config

    def get_required_exp_for_level(self, level: int) -> int:
        """
        计算达到指定等级所需的总经验值（基于n³公式）
        """
        if level <= 1:
            return 1
        return level ** 3

    def get_exp_needed_for_next_level(self, current_level: int) -> int:
        """
        计算从当前等级升到下一级所需的经验值
        """
        if current_level < 1:
            return 1
        return self.get_required_exp_for_level(current_level + 1) - self.get_required_exp_for_level(current_level)

    def calculate_pokemon_exp_gain(self, wild_pokemon_level: int, battle_result: str) -> int:
        """
        根据野生宝可梦等级和战斗结果计算经验值获取
        胜利时获得经验，失败时不获得经验
        公式：(基础经验 × 野生宝可梦等级) ÷ 7
        """
        # 基础经验固定为50
        base_exp = 50

        # 如果胜利，获得经验值；如果失败，不获得经验值
        if battle_result == "胜利":
            exp_gained = (base_exp * wild_pokemon_level) // 7
            return max(1, exp_gained)  # 确保至少获得1点经验
        else:
            return 0  # 失败时不获得经验

    def calculate_user_exp_gain(self, wild_pokemon_level: int, battle_result: str) -> int:
        """
        计算用户在战斗后获得的经验值
        根据新规则，玩家不获得经验
        """
        # 根据新规则，玩家不获得经验
        return 0

    def check_pokemon_level_up(self, current_level: int, current_exp: int) -> Dict[str, Any]:
        """
        检查宝可梦是否升级
        返回包含升级信息的字典
        """
        levels_gained = 0
        new_level = current_level
        remaining_exp = current_exp

        # 检查是否能升级多级
        while new_level < 100 and remaining_exp >= self.get_required_exp_for_level(new_level + 1):
            new_level += 1
            levels_gained += 1
            # 扣除升级所需的经验
            remaining_exp = remaining_exp - self.get_exp_needed_for_next_level(new_level - 1)

        new_level = min(100, new_level)

        return {
            "should_level_up": levels_gained > 0,
            "levels_gained": levels_gained,
            "new_level": new_level,
            "new_exp": remaining_exp,
            "required_exp_for_next": self.get_required_exp_for_level(new_level + 1) if new_level < 100 else 0
        }

    def update_pokemon_after_battle(self, user_id: str, pokemon_id: str, exp_gained: int) -> Dict[str, Any]:
        """
        战斗后更新宝可梦的经验值和等级
        """
        # 获取用户宝可梦信息
        pokemon_data = self.user_repo.get_user_pokemon_by_id(pokemon_id)
        if not pokemon_data:
            return {"success": False, "message": "宝可梦不存在"}

        current_level = pokemon_data['level']
        current_exp = pokemon_data.get('exp', 0)  # 使用现有的经验值
        new_total_exp = current_exp + exp_gained

        # 检查是否升级
        level_up_info = self.check_pokemon_level_up(current_level, new_total_exp)

        # 更新宝可梦数据
        with self.user_repo._get_connection() as conn:
            cursor = conn.cursor()

            # 更新经验和等级
            cursor.execute("""
                UPDATE user_pokemon
                SET level = ?, exp = ?
                WHERE id = ? AND user_id = ?
            """, (level_up_info["new_level"], level_up_info["new_exp"], int(pokemon_id), user_id))

            conn.commit()

        return {
            "success": True,
            "exp_gained": exp_gained,
            "level_up_info": level_up_info,
            "pokemon_name": pokemon_data.get('nickname', '未知宝可梦')
        }

    def update_team_pokemon_after_battle(self, user_id: str, team_pokemon_ids: list, exp_gained: int) -> list:
        """
        战斗后更新队伍中所有宝可梦的经验值和等级
        """
        results = []
        for pokemon_id in team_pokemon_ids:
            result = self.update_pokemon_after_battle(user_id, str(pokemon_id), exp_gained)
            results.append(result)
        return results

    def update_user_after_battle(self, user_id: str, exp_gained: int) -> Dict[str, Any]:
        """
        战斗后更新用户的经验值和等级
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 计算新的总经验
        new_total_exp = user.exp + exp_gained
        current_level = user.level

        # 检查用户可以升到多少级
        new_level = current_level
        while new_level < 100 and new_total_exp >= self.get_required_exp_for_level(new_level + 1):
            new_level += 1

        levels_gained = new_level - current_level

        # 计算剩余经验（升级后剩余的经验）
        if new_level > current_level:
            # 如果升级了，计算升级后的剩余经验
            remaining_exp = new_total_exp - self.get_required_exp_for_level(new_level)
        else:
            # 没有升级，保留原来的逻辑
            remaining_exp = new_total_exp

        # 更新用户数据
        with self.user_repo._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET level = ?, exp = ?
                WHERE user_id = ?
            """, (new_level, remaining_exp, user_id))

            conn.commit()

        return {
            "success": True,
            "exp_gained": exp_gained,
            "levels_gained": max(0, levels_gained),
            "new_level": new_level,
            "new_exp": remaining_exp
        }