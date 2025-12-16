"""宝可梦战斗状态修改服务"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from ...models.pokemon_models import PokemonStats


class StatID(Enum):
    """宝可梦状态ID枚举"""
    HP = 1
    ATTACK = 2
    DEFENSE = 3
    SP_ATTACK = 4
    SP_DEFENSE = 5
    SPEED = 6
    ACCURACY = 7
    EVASION = 8


@dataclass
class StatModifier:
    """状态修改器"""
    stat_id: int
    change: int  # 等级变化，范围 -6 到 +6


class StatModifierService:
    """状态修改服务，处理战斗中的状态变化"""

    def __init__(self):
        # 官方标准：等级→倍率完整映射表
        self._stat_level_multiplier_map = {
            -6: 1/3,   # 0.333...
            -5: 3/7,   # 0.428...
            -4: 1/2,   # 0.5
            -3: 3/5,   # 0.6
            -2: 2/3,   # 0.666...
            -1: 4/5,   # 0.8
             0: 1/1,   # 1.0
             1: 3/2,   # 1.5
             2: 2/1,   # 2.0
             3: 5/2,   # 2.5
             4: 3/1,   # 3.0
             5: 7/2,   # 3.5
             6: 4/1    # 4.0
        }

        # 统计ID到属性名的映射
        self._stat_id_to_attr = {
            StatID.ATTACK.value: 'attack',
            StatID.DEFENSE.value: 'defense',
            StatID.SP_ATTACK.value: 'sp_attack',
            StatID.SP_DEFENSE.value: 'sp_defense',
            StatID.SPEED.value: 'speed',
            StatID.ACCURACY.value: 'accuracy',  # 命中
            StatID.EVASION.value: 'evasion'     # 闪避
        }

    def get_stat_multiplier(self, level: int) -> float:
        """
        根据状态等级获取倍率

        Args:
            level: 状态等级 (-6 到 +6)

        Returns:
            对应的倍率
        """
        # 限制范围在 -6 到 +6 之间
        clamped_level = max(-6, min(6, level))
        return self._stat_level_multiplier_map.get(clamped_level, 1.0)

    def get_modified_stat_value(self, base_value: int, level: int) -> int:
        """
        根据基础值和状态等级计算修改后的值

        Args:
            base_value: 基础值
            level: 状态等级

        Returns:
            修改后的值（向下取整）
        """
        multiplier = self.get_stat_multiplier(level)
        modified_value = int(base_value * multiplier)
        return modified_value

    def apply_stat_changes(self,
                          base_stats: PokemonStats,
                          stat_changes: List[Dict[str, int]],
                          current_levels: Optional[Dict[int, int]] = None) -> Tuple[PokemonStats, Dict[int, int]]:
        """
        应用状态变化到基础状态

        Args:
            base_stats: 基础状态
            stat_changes: 状态变化列表，每个元素包含stat_id和change
            current_levels: 当前状态等级字典，如果为None则使用初始等级0

        Returns:
            (修改后的状态, 更新后的状态等级字典)
        """
        # 初始化状态等级字典
        if current_levels is None:
            current_levels = {}

        # 创建新的状态等级字典副本
        updated_levels = current_levels.copy()

        # 应用所有状态变化
        for change_data in stat_changes:
            stat_id = change_data['stat_id']
            change = change_data['change']

            # 获取当前等级，如果不存在则为0
            current_level = updated_levels.get(stat_id, 0)

            # 计算新等级并限制在范围内
            new_level = max(-6, min(6, current_level + change))
            updated_levels[stat_id] = new_level

        # 创建修改后的状态对象
        modified_stats = PokemonStats(
            hp=base_stats.hp,
            attack=self.get_modified_stat_value(base_stats.attack, updated_levels.get(StatID.ATTACK.value, 0)),
            defense=self.get_modified_stat_value(base_stats.defense, updated_levels.get(StatID.DEFENSE.value, 0)),
            sp_attack=self.get_modified_stat_value(base_stats.sp_attack, updated_levels.get(StatID.SP_ATTACK.value, 0)),
            sp_defense=self.get_modified_stat_value(base_stats.sp_defense, updated_levels.get(StatID.SP_DEFENSE.value, 0)),
            speed=self.get_modified_stat_value(base_stats.speed, updated_levels.get(StatID.SPEED.value, 0))
        )

        return modified_stats, updated_levels

    def get_target_pokemon_index(self,
                                attacker_index: int,
                                target_id: int,
                                total_pokemon_count: int) -> List[int]:
        """
        根据target_id获取目标宝可梦索引

        Args:
            attacker_index: 攻击方索引
            target_id: 目标ID (参考提供的target_id映射)
            total_pokemon_count: 总宝可梦数量

        Returns:
            目标宝可梦索引列表
        """
        # 计算对手索引（假设是2v2战斗，0和1为一方，2和3为另一方）
        # 但为了通用性，我们简单地认为0,1为一方，2,3为另一方
        opponent_start = 2 if attacker_index < 2 else 0

        targets = []

        # 简化处理，根据不同target_id返回不同的目标索引
        if target_id in [1, 9]:  # Specific move - 由技能决定（返回使用者）
            targets = [attacker_index]
        elif target_id == 2:  # Selected Pokémon - 由训练家选择（返回对手随机）
            targets = [opponent_start, opponent_start + 1]  # 对手方所有
        elif target_id == 3:  # Ally - 攻击方的队友
            ally_start = 0 if attacker_index == 0 else 1 if attacker_index == 1 else 2 if attacker_index == 2 else 3
            ally_indices = {0, 1} if attacker_index < 2 else {2, 3}
            targets = [i for i in ally_indices if i != attacker_index]
        elif target_id == 4:  # User's field - 攻击方场地
            targets = [i for i in range(4) if i == attacker_index or (i != opponent_start and i != opponent_start + 1)]
        elif target_id == 5:  # User or ally - 攻击方或队友
            # 返回使用者和队友
            ally_indices = {0, 1} if attacker_index < 2 else {2, 3}
            targets = list(ally_indices)
        elif target_id == 6:  # Opponent's field - 对手方场地
            targets = [opponent_start, opponent_start + 1]
        elif target_id == 7:  # User - 使用者自己
            targets = [attacker_index]
        elif target_id == 8:  # Random opponent - 随机对手
            opponents = [i for i in range(4) if (i < 2 and attacker_index >= 2) or (i >= 2 and attacker_index < 2)]
            if opponents:
                import random
                targets = [random.choice(opponents)]
        elif target_id == 10:  # Selected Pokémon - 由训练家选择（和target_id=2类似）
            targets = [opponent_start, opponent_start + 1]  # 对手方所有
        elif target_id == 11:  # All opponents - 所有对手
            targets = [opponent_start, opponent_start + 1]
        elif target_id == 12:  # Entire field - 整个场地
            targets = list(range(total_pokemon_count))
        elif target_id == 13:  # User and allies - 使用者和队友
            ally_indices = {0, 1} if attacker_index < 2 else {2, 3}
            targets = list(ally_indices)
        elif target_id == 14:  # All Pokémon - 所有宝可梦
            targets = list(range(total_pokemon_count))
        elif target_id == 15:  # All allies - 所有队友
            ally_indices = {0, 1} if attacker_index < 2 else {2, 3}
            targets = [i for i in ally_indices if i != attacker_index]  # 排除攻击者自己

        # 限制目标索引在有效范围内
        targets = [i for i in targets if 0 <= i < total_pokemon_count]

        return targets