from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..models.adventure_models import BattleMoveInfo, BattleContext
from .battle_engine import BattleState, MoveOutcome, StatModifierService
from .battle_config import battle_config


class MoveStrategy(ABC):
    """技能策略接口"""

    @abstractmethod
    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        """执行技能效果"""
        pass


class BaseMoveStrategy(MoveStrategy):
    """基础技能策略类，提供公共方法"""

    def __init__(self):
        self.STAT_NAMES = battle_config.get_stat_names()
        self.AILMENT_MAP = battle_config.get_ailment_map()
        self.AILMENT_CHINESE_MAP = battle_config.get_ailment_chinese_map()
        self.stat_modifier_service = StatModifierService()


class DamageMoveStrategy(BaseMoveStrategy):
    """伤害类技能策略"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        # 伤害效果已经在其他地方处理，这里只返回空效果列表
        return []


class AilmentMoveStrategy(BaseMoveStrategy):
    """异常状态类技能策略"""

    def _get_ailment_chance(self, move: BattleMoveInfo) -> int:
        return move.ailment_chance if move.ailment_chance > 0 else 100

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        if outcome.damage <= 0:  # 只在造成伤害时才尝试附加异常状态
            return []

        # 如果有battle_logic，使用其辅助方法，这样可以处理免疫检查和概率判定
        if battle_logic:
            # ✅ 修复：根据 move.target_id 来决定异常状态的目标
            target_unit = battle_logic._get_target_by_target_id(attacker, defender, move.target_id)

            # 使用BattleLogic的辅助方法生成异常状态效果
            return battle_logic._gen_ailment_effect(target_unit, move)
        else:
            # 后备逻辑：基本的异常状态处理
            chance = self._get_ailment_chance(move)
            if outcome.damage <= 0 or outcome.missed:  # 简化判断
                return []

            if outcome.damage > 0:
                ailment_id = move.meta_ailment_id
                status_name = self.AILMENT_MAP.get(ailment_id, "unknown")
                if status_name != "unknown":
                    return [{"type": "ailment", "status": status_name, "status_id": ailment_id}]

        return []


class StatChangeMoveStrategy(BaseMoveStrategy):
    """能力变化类技能策略"""

    def __init__(self, target_type: str = "defender"):
        super().__init__()
        # target_type: "defender" (降低对手), "attacker" (提升自己)
        self.target_type = target_type

    def _get_stat_change_chance(self, move: BattleMoveInfo) -> int:
        raw_chance = int(move.stat_chance * 100) if move.stat_chance is not None else 0
        return raw_chance if raw_chance > 0 else 100

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        chance = self._get_stat_change_chance(move)
        if outcome.damage <= 0 or outcome.missed:
            return []

        effects = []

        # 确定能力变化应用的目标
        target = defender if self.target_type == "defender" else attacker

        if hasattr(move, 'stat_changes') and move.stat_changes:
            for change in move.stat_changes:
                # 兼容字典或对象访问
                sid = change.get('stat_id') if isinstance(change, dict) else getattr(change, 'stat_id', None)
                amt = change.get('change') if isinstance(change, dict) else getattr(change, 'change', 0)

                if sid is None or amt == 0:
                    continue

                # 计算实际变化 (对于降低目标，需要取负值)
                curr = target.stat_levels.get(sid, 0)
                # 对于提升自己的技能（如剑舞），amt 是正值；对于降低对手的技能，amt 是负值
                new_stage = max(-6, min(6, curr + amt))

                if new_stage != curr:
                    effects.append({
                        "type": "stat_change",
                        "stat_id": sid,
                        "stat_name": self.STAT_NAMES.get(str(sid), "stat"),
                        "change": new_stage - curr,
                        "new_stage": new_stage,
                        "target_obj": target  # 引用目标对象以便 execute 阶段修改
                    })
        return effects


class PureStatChangeMoveStrategy(BaseMoveStrategy):
    """纯能力变化类技能策略（如剑舞、防守等，不伴随伤害）"""

    def __init__(self, target_type: str = "attacker"):
        super().__init__()
        # target_type: "defender" (降低对手), "attacker" (提升自己)
        self.target_type = target_type

    def _get_stat_change_chance(self, move: BattleMoveInfo) -> int:
        raw_chance = int(move.stat_chance * 100) if move.stat_chance is not None else 0
        return raw_chance if raw_chance > 0 else 100

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        chance = self._get_stat_change_chance(move)
        # 纯能力变化技能不需要造成伤害

        effects = []

        # 确定能力变化应用的目标
        if battle_logic and hasattr(move, 'target_id'):
            # 使用BattleLogic的辅助方法根据target_id确定目标
            target = battle_logic._get_target_by_target_id(attacker, defender, move.target_id)
        else:
            # 使用默认目标选择逻辑
            target = defender if self.target_type == "defender" else attacker

        if hasattr(move, 'stat_changes') and move.stat_changes:
            for change in move.stat_changes:
                # 兼容字典或对象访问
                sid = change.get('stat_id') if isinstance(change, dict) else getattr(change, 'stat_id', None)
                amt = change.get('change') if isinstance(change, dict) else getattr(change, 'change', 0)

                if sid is None or amt == 0:
                    continue

                # 计算实际变化
                curr = target.stat_levels.get(sid, 0)
                new_stage = max(-6, min(6, curr + amt))

                if new_stage != curr:
                    effects.append({
                        "type": "stat_change",
                        "stat_id": sid,
                        "stat_name": self.STAT_NAMES.get(str(sid), "stat"),
                        "change": new_stage - curr,
                        "new_stage": new_stage,
                        "target_obj": target  # 引用目标对象以便 execute 阶段修改
                    })
        return effects


class HealMoveStrategy(BaseMoveStrategy):
    """回复类技能策略"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        ratio = move.healing
        if ratio == 0:
            return []

        if battle_logic:
            # ✅ 修复：根据 move.target_id 来决定回复效果的目标
            target_unit = battle_logic._get_target_by_target_id(attacker, defender, move.target_id)

            # 使用BattleLogic的辅助方法处理回复效果
            return battle_logic._gen_heal_effect(target_unit, move)
        else:
            # 后备逻辑
            max_hp = attacker.context.pokemon.stats.hp
            amt = int(max_hp * ratio)

            if amt > 0:
                return [{"type": "heal", "amount": amt}]
            elif amt < 0:
                return [{"type": "damage", "amount": -amt, "is_recoil": True}]  # 自残
            return []


class TwoTurnMoveStrategy(BaseMoveStrategy):
    """两回合技能策略"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        # 两回合技能的逻辑在BattleLogic中处理，这里返回空
        return []


class OHKOMoveStrategy(BaseMoveStrategy):
    """一击必杀类技能策略"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        # OHKO的逻辑在BattleLogic中处理
        if battle_logic:
            # 使用BattleLogic的辅助方法处理OHKO逻辑
            success, reason = battle_logic._check_ohko(attacker, defender, move, outcome.effectiveness)
            if success:
                outcome.damage = defender.current_hp  # 覆盖伤害
                return [{"type": "ohko", "success": True}]
            else:
                outcome.damage = 0
                return [{"type": "ohko", "success": False, "reason": reason}]
        else:
            # 后备逻辑
            return []


class DamageAilmentMoveStrategy(BaseMoveStrategy):
    """伤害+异常状态类技能策略"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        effects = []
        if outcome.damage > 0:  # 简化判定，实际应该看是否被免疫
            if battle_logic:
                # ✅ 修复：根据 move.target_id 来决定异常状态的目标
                target_unit = battle_logic._get_target_by_target_id(attacker, defender, move.target_id)

                # 使用BattleLogic的辅助方法处理异常状态，确保一致性
                ailment_effects = battle_logic._gen_ailment_effect(target_unit, move)
                effects.extend(ailment_effects)
            else:
                # 后备逻辑
                ailment_id = move.meta_ailment_id
                status_name = self.AILMENT_MAP.get(ailment_id, "unknown")
                if status_name != "unknown":
                    effects.append({"type": "ailment", "status": status_name, "status_id": ailment_id})
        return effects


class DamageLowerMoveStrategy(BaseMoveStrategy):
    """伤害+降低能力类技能策略"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        # 在 _execute_action 中已经通过 meta_category_id 分配了策略，这里主要处理能力降低
        if battle_logic:
            # ✅ 修复：根据 move.target_id 来决定副作用的目标
            # 例如"近身战" target_id=7 (User)，这里就会返回 attacker
            # 例如"岩石封锁" target_id=10 (Selected Pokemon)，这里就会返回 defender
            target_unit = battle_logic._get_target_by_target_id(attacker, defender, move.target_id)

            # 使用正确的 target_unit 生成效果
            stat_effects = battle_logic._gen_stat_change_effect(target_unit, move, default_target="opponent")
            return stat_effects
        else:
            # 后备逻辑
            return StatChangeMoveStrategy(target_type="defender").execute(attacker, defender, move, outcome, battle_logic)


class DamageRaiseMoveStrategy(BaseMoveStrategy):
    """伤害+提升能力类技能策略"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        # 在 _execute_action 中已经通过 meta_category_id 分配了策略，这里主要处理能力提升
        if battle_logic:
            # ✅ 修复：根据 move.target_id 来决定副作用的目标
            # 例如"龙星群" target_id=7 (User)，这里就会返回 attacker
            target_unit = battle_logic._get_target_by_target_id(attacker, defender, move.target_id)

            # 使用正确的 target_unit 生成效果
            stat_effects = battle_logic._gen_stat_change_effect(target_unit, move, default_target="user")
            return stat_effects
        else:
            # 后备逻辑
            return StatChangeMoveStrategy(target_type="attacker").execute(attacker, defender, move, outcome, battle_logic)  # 提升攻击方能力


class DamageDrainMoveStrategy(BaseMoveStrategy):
    """伤害+吸血类技能策略"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        drain_pct = getattr(move, 'drain', 50) or 50
        heal_amt = int(outcome.damage * (drain_pct / 100.0))
        if heal_amt > 0:
            return [{"type": "heal", "amount": heal_amt, "from_drain": True, "damage_dealt": outcome.damage}]
        return []


class FieldEffectMoveStrategy(BaseMoveStrategy):
    """场地效果类技能策略（如场地变化、强制交换等）"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        """处理场地效果类技能，如Cat 10-13"""
        meta_category_id = move.meta_category_id
        map_type = {10: "field_effect", 11: "terrain", 12: "force_switch", 13: "unique"}
        effect_type = map_type.get(meta_category_id, "unique")
        return [{"type": effect_type, "effect": "active"}]


class SwaggerMoveStrategy(BaseMoveStrategy):
    """虚张声势类技能策略（混乱+提升攻击）"""

    def execute(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                outcome: MoveOutcome, battle_logic: 'BattleLogic' = None) -> List[Dict]:
        effects = []

        # 使用BattleLogic的辅助方法生成强制混乱效果
        if battle_logic:
            # ✅ 修复：根据 move.target_id 来决定混乱和能力变化的目标
            target_unit = battle_logic._get_target_by_target_id(attacker, defender, move.target_id)

            # 生成强制混乱效果（ID为6），应用到正确的目标
            force_ailment_effects = battle_logic._gen_ailment_effect(target_unit, move, force_status_id=6)
            effects.extend(force_ailment_effects)

            # 生成能力变化效果（对目标方进行能力变化），应用到正确的目标
            stat_effects = battle_logic._gen_stat_change_effect(target_unit, move, default_target="opponent")
            effects.extend(stat_effects)
        else:
            # 后备方案：如果battle_logic不可用，使用基本逻辑
            # 混乱效果
            ailment_id = 6  # 混乱
            status_name = self.AILMENT_MAP.get(ailment_id, "confusion")
            if status_name != "unknown":
                effects.append({"type": "ailment", "status": status_name, "status_id": ailment_id})

            # 能力变化效果
            stat_change_strategy = StatChangeMoveStrategy(target_type="defender")
            temp_effects = stat_change_strategy.execute(attacker, defender, move, outcome, battle_logic)
            effects.extend(temp_effects)

        return effects


# 策略工厂
class MoveStrategyFactory:
    """技能策略工厂"""

    @staticmethod
    def create_strategy(meta_category_id: int, config: Dict[str, Any] = None) -> MoveStrategy:
        if meta_category_id == 9:  # OHKO
            return OHKOMoveStrategy()
        elif meta_category_id == 1:  # 异常状态
            return AilmentMoveStrategy()
        elif meta_category_id == 2:  # 纯能力提升（如剑舞）
            return PureStatChangeMoveStrategy(target_type="attacker")
        elif meta_category_id == 3:  # 回复
            return HealMoveStrategy()
        elif meta_category_id == 4:  # 伤害+异常
            return DamageAilmentMoveStrategy()
        elif meta_category_id == 5:  # 虚张声势
            return SwaggerMoveStrategy()
        elif meta_category_id == 6:  # 伤害+降低
            return DamageLowerMoveStrategy()
        elif meta_category_id == 7:  # 伤害+提升
            return DamageRaiseMoveStrategy()
        elif meta_category_id == 8:  # 伤害+吸血
            return DamageDrainMoveStrategy()
        elif meta_category_id in [10, 11, 12, 13]:  # 场地效果等
            return FieldEffectMoveStrategy()
        else:  # 默认伤害类
            return DamageMoveStrategy()