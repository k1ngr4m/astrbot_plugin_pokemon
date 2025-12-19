from typing import Dict, Type, Any, Optional, List, TYPE_CHECKING
from .hook_manager import BattleHook
from .status_plugins import VolatileStatusPlugin

if TYPE_CHECKING:
    from .battle_engine import BattleState, BattleLogger

class AbilityPlugin(VolatileStatusPlugin):
    """特性插件基类 - 复用 VolatileStatusPlugin 的生命周期管理"""
    def __init__(self, owner: 'BattleState'):
        # 特性通常是永久的，设置 turns=999
        super().__init__(owner, turns=999)
        self.ability_id = 0
        self.ability_name = ""

    def on_apply(self):
        """在这里注册特性的钩子"""
        pass
    
    def on_entry(self, opponent: 'BattleState', logger_obj: 'BattleLogger'):
        """登场时触发的效果"""
        pass

class AbilityRegistry:
    """特性插件注册中心"""
    _registry: Dict[int, Type[AbilityPlugin]] = {}

    @classmethod
    def register(cls, ability_id: int):
        def decorator(plugin_class: Type[AbilityPlugin]):
            cls._registry[ability_id] = plugin_class
            return plugin_class
        return decorator

    @classmethod
    def create_plugin(cls, ability_id: int, owner: 'BattleState') -> Optional[AbilityPlugin]:
        plugin_class = cls._registry.get(ability_id)
        return plugin_class(owner) if plugin_class else None

# ==========================================
# 1. 模板类 (Templates)
# ==========================================

class ImmunityAbility(AbilityPlugin):
    """通用属性免疫模板"""
    def __init__(self, owner: 'BattleState', target_type: str, 
                 msg: str = "由于特性，攻击无效了！", 
                 absorb_func = None):
        super().__init__(owner)
        self.target_type = target_type
        self.msg = msg
        self.absorb_func = absorb_func # 吸收成功后的回调逻辑

    def on_apply(self):
        # 注册伤害计算钩子，优先级设为 5 (高优先级，优先判定免疫)
        self.owner.hooks.register("on_damage_calc", BattleHook(f"immune_{self.ability_id}", 5, self.check_immunity))

    def check_immunity(self, damage_info: dict, attacker, defender, move):
        """
        damage_info 结构包含: power, effectiveness, stab, crit_mod, is_immune
        """
        # 只有当特性持有者是防御方时才生效
        if defender != self.owner:
            return damage_info
            
        # 检查技能属性是否匹配免疫目标
        if move.type_name == self.target_type:
            damage_info['effectiveness'] = 0.0
            damage_info['is_immune'] = True
            
            # 如果定义了吸收逻辑，则执行
            if self.absorb_func:
                self.absorb_func(self, damage_info, attacker, defender, move)
            
        return damage_info

# ==========================================
# 2. 数据驱动 (Data-Driven Configuration)
# ==========================================

# 配置表：ID -> {属性, 倍率, 名称}
STAT_MOD_CONFIG = {
    37: {"stat": "attack", "mult": 2.0, "name": "huge-power"},   # 大力士
    # 146: {"stat": "speed", "mult": 2.0, "name": "sand-rush"}, # 拨沙 (示例)
}

def _create_stat_mod_ability(ability_id: int, config: dict):
    """动态创建数值修正特性类"""
    stat_name = config['stat']
    multiplier = config['mult']
    
    class DynamicStatAbility(AbilityPlugin):
        def on_apply(self):
            self.owner.hooks.register("on_stat_calc", BattleHook(f"{config['name']}_boost", 10, self.stat_mod))

        def stat_mod(self, stats):
            current_val = getattr(stats, stat_name)
            setattr(stats, stat_name, int(current_val * multiplier))
            return stats

    AbilityRegistry.register(ability_id)(DynamicStatAbility)

for aid, cfg in STAT_MOD_CONFIG.items():
    _create_stat_mod_ability(aid, cfg)


# ==========================================
# 3. 手动实现 / 特定模板实现 (Manual)
# ==========================================

# 1. 飘浮 (Levitate) - ID: 26
@AbilityRegistry.register(26)
class LevitateAbility(ImmunityAbility):
    def __init__(self, owner):
        super().__init__(owner, target_type='ground', msg="由于飘浮特性，地面系招式无效！")

# 2. 蓄电 (Volt Absorb) - ID: 10 (免疫并回血)
@AbilityRegistry.register(10)
class VoltAbsorbAbility(ImmunityAbility):
    def __init__(self, owner):
        def _volt_absorb_logic(ability_instance, dmg_info, atk, dfd, move):
            # 触发回血逻辑 (1/4 最大 HP)
            max_hp = ability_instance.owner.context.pokemon.stats.hp
            heal_amt = max_hp // 4
            ability_instance.owner.current_hp = min(max_hp, ability_instance.owner.current_hp + heal_amt)
            
        super().__init__(owner, target_type='electric', absorb_func=_volt_absorb_logic)

# 3. 引火 (Flash Fire) - ID: 18
@AbilityRegistry.register(18)
class FlashFireAbility(ImmunityAbility):
    def __init__(self, owner):
        super().__init__(owner, target_type='fire')


@AbilityRegistry.register(22) # 威吓 (Intimidate)
class IntimidateAbility(AbilityPlugin):
    def on_entry(self, opponent: 'BattleState', logger_obj: 'BattleLogger'):
        logger_obj.log(f"{self.owner.context.pokemon.name} 的威吓发动了！\n\n")
        current_stage = opponent.stat_levels.get(1, 0)
        if current_stage > -6:
            opponent.stat_levels[1] = current_stage - 1
            logger_obj.log(f"{opponent.context.pokemon.name} 的攻击降低了！\n\n")
        else:
            logger_obj.log(f"{opponent.context.pokemon.name} 的攻击无法再降低了！\n\n")

class PinchAbility(AbilityPlugin):
    """
    低 HP 触发威力提升的通用模板 (如猛火、激流、茂盛)
    """
    def __init__(self, owner: 'BattleState', boost_types: List[str], multiplier: float = 1.5):
        super().__init__(owner)
        self.boost_types = boost_types
        self.multiplier = multiplier

    def on_apply(self):
        # 注册到伤害计算钩子，通常优先级设为 15 (在基础修正之后)
        self.owner.hooks.register("on_damage_calc", BattleHook(f"pinch_boost_{self.ability_id}", 15, self.damage_mod))

    def damage_mod(self, damage_params: dict, attacker, defender, move):
        """
        damage_params 结构包含: power, effectiveness, stab, crit_mod, is_immune
        """
        # 只有当特性持有者是攻击方时才生效
        if attacker != self.owner:
            return damage_params

        # 1. 检查当前 HP 是否低于 1/3
        max_hp = self.owner.context.pokemon.stats.hp
        if self.owner.current_hp * 3 <= max_hp:
            
            # 2. 检查使用的招式属性是否匹配
            if move.type_name in self.boost_types:
                # 3. 修正威力参数
                damage_params['power'] = int(damage_params['power'] * self.multiplier)
        
        return damage_params

# ==========================================
# 2. 数据驱动 (Data-Driven Configuration)
# ==========================================

# ... (Previous Data Driven Config code remains, assuming it's above this section or unrelated to replacement area) ...
# Actually, the file structure has Templates section first. I will append PinchAbility to Templates section.
# But replacing `BlazeAbility` at the end of the file implies I should putting all manual/template implementations there?
# The user wants structure: 1. Templates 2. Data-Driven 3. Implementations.
# I'll just append PinchAbility to Templates and replace BlazeAbility with new style.

# Wait, the replace block needs to be continuous or I should use multi_replace.
# PinchAbility should go under ImmunityAbility.
# Then BlazeAbility replacement.
# Let's use multi_replace to be safe and clean.

