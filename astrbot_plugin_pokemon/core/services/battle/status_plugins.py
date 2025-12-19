from typing import Dict, Type, Any, Optional, TYPE_CHECKING
import random
from dataclasses import dataclass, field

from .hook_manager import BattleHook

if TYPE_CHECKING:
    from .battle_engine import BattleState, BattleLogger

class VolatileStatusPlugin:
    """挥发性状态插件基类"""
    def __init__(self, owner: 'BattleState', turns: int = 0):
        self.owner = owner
        self.turns = turns
        self.name = self.__class__.__name__.lower()

    def on_apply(self):
        """当状态被施加时，注册相关的钩子"""
        pass

    def on_remove(self):
        """当状态解除时，注销相关的钩子"""
        pass

class StatusRegistry:
    """异常状态注册中心：负责 ID 与 插件类 的映射"""
    _registry: Dict[int, Type['VolatileStatusPlugin']] = {}

    @classmethod
    def register(cls, status_id: int):
        """装饰器：用于注册状态插件"""
        def decorator(plugin_class: Type['VolatileStatusPlugin']):
            cls._registry[status_id] = plugin_class
            return plugin_class
        return decorator

    @classmethod
    def create_plugin(cls, status_id: int, owner: 'BattleState', **kwargs) -> Optional['VolatileStatusPlugin']:
        """根据 ID 创建插件实例"""
        plugin_class = cls._registry.get(status_id)
        if plugin_class:
            return plugin_class(owner, **kwargs)
        return None

# --- Non-Volatile Status Plugins (1-5) ---

@StatusRegistry.register(1)
class ParalysisStatus(VolatileStatusPlugin):
    def on_apply(self):
        self.owner.hooks.register("before_move", BattleHook("para_check", 5, self.before_move_check))
        self.owner.hooks.register("on_stat_calc", BattleHook("para_speed", 10, self.stat_mod))

    def before_move_check(self, attacker, move, logger_obj) -> bool:
        if random.random() < 0.25:
            logger_obj.log(f"{attacker.context.pokemon.name} 身体麻痹无法动弹！\n\n")
            return False
        return True

    def stat_mod(self, stats):
        stats.speed = int(stats.speed * 0.5)
        return stats

@StatusRegistry.register(2)
class SleepStatus(VolatileStatusPlugin):
    def on_apply(self):
        self.owner.hooks.register("before_move", BattleHook("sleep_check", 5, self.before_move_check))

    def before_move_check(self, attacker, move, logger_obj) -> bool:
        # 这里的 turns 对应 BattleState.status_turns，需要在 apply 时传入
        # 或者直接引用 attacker.status_turns (因为 BattleState 仍持有此字段用于同步)
        # 建议插件尽量自我管理，但为了与 context 同步，可能需要操作 owner
        
        if self.owner.status_turns > 0:
            self.owner.status_turns -= 1
            logger_obj.log(f"{attacker.context.pokemon.name} 正在熟睡。\n\n")
            return False
        else:
            self.owner.remove_status(2) # 自动移除
            logger_obj.log(f"{attacker.context.pokemon.name} 醒来了！\n\n")
            return True
            
    def on_remove(self):
         self.owner.non_volatile_status = None
         self.owner.hooks.unregister("before_move", "sleep_check")

@StatusRegistry.register(3)
class FreezeStatus(VolatileStatusPlugin):
    def on_apply(self):
        self.owner.hooks.register("before_move", BattleHook("freeze_check", 5, self.before_move_check))

    def before_move_check(self, attacker, move, logger_obj) -> bool:
        # 火系技能自我解冻
        if getattr(move, 'type_name', '') in ['fire', '火'] and getattr(move, 'power', 0) > 0:
            self.owner.remove_status(3)
            logger_obj.log(f"{attacker.context.pokemon.name} 的火焰融化了周围的冰！\n\n")
            return True

        if random.random() < 0.20:
            self.owner.remove_status(3)
            logger_obj.log(f"{attacker.context.pokemon.name} 的冰融化了！\n\n")
            return True
        
        logger_obj.log(f"{attacker.context.pokemon.name} 被冻结了！\n\n")
        return False
        
    def on_remove(self):
        self.owner.non_volatile_status = None
        self.owner.hooks.unregister("before_move", "freeze_check")

@StatusRegistry.register(4)
class BurnStatus(VolatileStatusPlugin):
    def on_apply(self):
        self.owner.hooks.register("on_stat_calc", BattleHook("burn_atk", 10, self.stat_mod))
        self.owner.hooks.register("turn_end", BattleHook("burn_dmg", 10, self.turn_end_dmg))

    def stat_mod(self, stats):
        stats.attack = int(stats.attack * 0.5)
        return stats

    def turn_end_dmg(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        dmg = max(1, int(max_hp / 16))
        state.current_hp -= dmg
        logger_obj.log(f"{state.context.pokemon.name} 因烧伤受到 {dmg} 点伤害！\n\n")

@StatusRegistry.register(5)
class PoisonStatus(VolatileStatusPlugin):
    def on_apply(self):
        self.owner.hooks.register("turn_end", BattleHook("poison_dmg", 10, self.turn_end_dmg))

    def turn_end_dmg(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        dmg = max(1, int(max_hp / 8))
        state.current_hp -= dmg
        logger_obj.log(f"{state.context.pokemon.name} 因中毒受到 {dmg} 点伤害！\n\n")

# --- Volatile Status Plugins ---

@StatusRegistry.register(6)
class ConfusionStatus(VolatileStatusPlugin):
    def on_apply(self):
        # 初始 turns 将在 create_plugin 时传入
        # 如果未传入，这里可以使用默认值，但通常应由外部控制
        self.owner.hooks.register("before_move", BattleHook("confusion_check", 5, self.before_move_check))

    def before_move_check(self, attacker, move, logger_obj) -> bool:
        self.turns -= 1
        # 同时更新原始字典以保持同步
        if 6 in attacker.volatile_statuses:
             attacker.volatile_statuses[6] = self.turns

        if self.turns <= 0:
            self.owner.remove_status(6)
            logger_obj.log(f"{attacker.context.pokemon.name} 的混乱解除了！\n\n")
            return True

        logger_obj.log(f"{attacker.context.pokemon.name} 混乱了！\n\n")
        if random.random() < 0.33: # Gen 7+ 33%
            # 自伤逻辑
            level = attacker.context.pokemon.level
            attack = attacker.context.pokemon.stats.attack
            defense = attacker.context.pokemon.stats.defense
            damage = int((((2 * level / 5 + 2) * 40 * attack / defense) / 50) + 2)
            attacker.current_hp -= damage
            logger_obj.log(f"在混乱中攻击了自己！(扣除 {damage} HP)\n\n")
            return False 
        return True

    def on_remove(self):
        if 6 in self.owner.volatile_statuses:
            del self.owner.volatile_statuses[6]
        self.owner.hooks.unregister("before_move", "confusion_check")

@StatusRegistry.register(7)
class InfatuationStatus(VolatileStatusPlugin):
    def on_apply(self):
        self.owner.hooks.register("before_move", BattleHook("infatuation_check", 5, self.before_move_check))

    def before_move_check(self, attacker, move, logger_obj) -> bool:
        logger_obj.log(f"{attacker.context.pokemon.name} 着迷了！\n\n")
        if random.random() < 0.5:
            logger_obj.log(f"{attacker.context.pokemon.name} 因为着迷而无法行动！\n\n")
            return False
        return True
    
    def on_remove(self):
        if 7 in self.owner.volatile_statuses:
            del self.owner.volatile_statuses[7]
        self.owner.hooks.unregister("before_move", "infatuation_check")

@StatusRegistry.register(8)
class TrapStatus(VolatileStatusPlugin):
    def on_apply(self):
        self.owner.hooks.register("turn_end", BattleHook("trap_dmg", 10, self.turn_end_dmg))

    def turn_end_dmg(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        dmg = max(1, int(max_hp / 8))
        state.current_hp -= dmg
        logger_obj.log(f"{state.context.pokemon.name} 因束缚受到了 {dmg} 点伤害！\n\n")
        
        self.turns -= 1
        if 8 in state.volatile_statuses:
            state.volatile_statuses[8] = self.turns

        if self.turns <= 0:
            state.remove_status(8)
            logger_obj.log(f"{state.context.pokemon.name} 摆脱了束缚！\n\n")

    def on_remove(self):
        if 8 in self.owner.volatile_statuses:
            del self.owner.volatile_statuses[8]
        self.owner.hooks.unregister("turn_end", "trap_dmg")

@StatusRegistry.register(18)
class LeechSeedStatus(VolatileStatusPlugin):
    def __init__(self, owner, turns=999, opponent=None):
        super().__init__(owner, turns)
        self.opponent = opponent

    def on_apply(self):
        self.owner.hooks.register("turn_end", BattleHook("leech_seed_drain", 20, self.drain_effect))

    def drain_effect(self, state, opponent_state, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        dmg = max(1, int(max_hp / 8))
        state.current_hp -= dmg
        logger_obj.log(f"{state.context.pokemon.name} 的体力被寄生种子夺走了 {dmg} 点！\n\n")
        
        target = self.opponent or opponent_state
        if target and target.current_hp > 0:
            heal = dmg
            target.current_hp = min(target.context.pokemon.stats.hp, target.current_hp + heal)
            # logger_obj.log(f"{target.context.pokemon.name} 回复了体力！\n\n")

    def on_remove(self):
        if 18 in self.owner.volatile_statuses:
            del self.owner.volatile_statuses[18]
        self.owner.hooks.unregister("turn_end", "leech_seed_drain")
