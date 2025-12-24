from typing import Dict, Type, Any, Optional, List, TYPE_CHECKING
from .hook_manager import BattleHook
from .status_plugins import VolatileStatusPlugin
from .battle_config import battle_config

if TYPE_CHECKING:
    from .battle_engine import BattleState, BattleLogger

# ==========================================
# 破格 (Mold Breaker) 可无视的特性列表
# ==========================================
MOLD_BREAKER_IGNORABLE_IDS = set(battle_config.get_mold_breaker_ignorable_ids())

class AbilityPlugin(VolatileStatusPlugin):
    """特性插件基类 - 复用 VolatileStatusPlugin 的生命周期管理"""
    def __init__(self, owner: 'BattleState'):
        # 特性通常是永久的，设置 turns=999
        super().__init__(owner, turns=999)
        self.ability_id = 0
        self.ability_name = ""
        self.can_be_ignored = False  # 新增：标记该特性是否会被“破格”无视

    def on_apply(self):
        """在这里注册特性的钩子"""
        pass
    
    def on_entry(self, opponent: 'BattleState', logger_obj: 'BattleLogger', logic: Any = None):
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
        if plugin_class:
            plugin = plugin_class(owner)
            plugin.ability_id = ability_id
            if ability_id in MOLD_BREAKER_IGNORABLE_IDS:
                plugin.can_be_ignored = True
            return plugin
        return None


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
        hook = BattleHook(f"immune_{self.ability_id}", 5, self.check_immunity)
        hook.source_plugin = self
        self.owner.hooks.register("on_damage_calc", hook)

    def check_immunity(self, damage_info: dict, attacker, defender, move, logger_obj=None):
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
            
            # 增加日志反馈
            # 避免循环引用，通过类名判断是否为 NoOpBattleLogger (AI模拟)
            is_noop = logger_obj and logger_obj.__class__.__name__ == 'NoOpBattleLogger'
            if logger_obj and not is_noop:
                # 这里的 ability_name 可以通过 ID 从配置表获取，或在类中定义
                # 暂时用通用描述
                logger_obj.log(f"{defender.context.pokemon.name} 的特性使其免疫了 {move.move_name}！\n\n")
            
            # 如果定义了吸收逻辑，则执行
            if self.absorb_func:
                self.absorb_func(self, damage_info, attacker, defender, move)
            
        return damage_info

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
        hook = BattleHook(f"pinch_boost_{self.ability_id}", 15, self.damage_mod)
        hook.source_plugin = self
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params: dict, attacker, defender, move, logger_obj=None):
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
                
                # 增加日志反馈
                is_noop = logger_obj and logger_obj.__class__.__name__ == 'NoOpBattleLogger'
                if logger_obj and not is_noop:
                    logger_obj.log(f"{attacker.context.pokemon.name} 的特性使 {move.move_name} 的威力提升了！\n\n")
        
        return damage_params

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
            hook = BattleHook(f"{config['name']}_boost", 10, self.stat_mod)
            hook.source_plugin = self
            self.owner.hooks.register("on_stat_calc", hook)

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


# 9. 粗糙皮肤 (Rough Skin) - ID: 24
@AbilityRegistry.register(24)
class RoughSkinAbility(AbilityPlugin):
    def on_apply(self):
        # 注册受击后的事件钩子
        hook = BattleHook("rough_skin_dmg", 10, self.on_hit)
        hook.source_plugin = self
        self.owner.hooks.register("after_damage", hook)

    def on_hit(self, owner, attacker, move, damage, logger_obj):
        # 仅在招式为接触类时触发
        if getattr(move, 'is_contact', False):
            # 扣除 1/8 最大 HP
            # 这里 attacker.context.pokemon.stats.hp 是最大HP基础值，或者是current battle stat max hp?
            # 应该用 max_hp derived from context usually.
            max_hp = attacker.context.pokemon.stats.hp
            recoil = max(1, max_hp // 8)
            
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            logger_obj.log(f"{attacker.context.pokemon.name} 碰到了 {owner.context.pokemon.name} 的粗糙皮肤，受到了伤害！\n\n")

# 10. 静电 (Static) - ID: 9
@AbilityRegistry.register(9)
class StaticAbility(AbilityPlugin):
    def on_apply(self):
        hook = BattleHook("static_trigger", 10, self.on_hit)
        hook.source_plugin = self
        self.owner.hooks.register("after_damage", hook)

    def on_hit(self, owner, attacker, move, damage, logger_obj):
        import random
        # 接触类招式判定 且 30% 几率
        if getattr(move, 'is_contact', False) and random.random() < 0.3:
            # 使用现有的状态系统施加麻痹 (Status ID: 1, 假设1是麻痹，根据 battle_engine/context)
            # 检查 attacker 状态
            if attacker.non_volatile_status is None:
                attacker.non_volatile_status = 1 # 1: 麻痹
                logger_obj.log(f"{attacker.context.pokemon.name} 因 {owner.context.pokemon.name} 的静电特性麻痹了！\n\n")



# 3. 恶作剧之心 (Prankster) - ID: 158
@AbilityRegistry.register(158)
class PranksterAbility(AbilityPlugin):
    def on_apply(self):
        # 注册优先级计算钩子
        hook = BattleHook("prankster_prio", 10, self.priority_mod)
        hook.source_plugin = self
        self.owner.hooks.register("on_priority_calc", hook)

    def priority_mod(self, current_priority, attacker, move):
        """如果是变化招式，优先级 +1"""
        # 判定变化招式
        # damage_class_id: 1=Status, 2=Physical, 3=Special
        if move.damage_class_id == 1:
            return current_priority + 1
        return current_priority


# 4. 疾风之翼 (Gale Wings) - ID: 177
@AbilityRegistry.register(177)
class GaleWingsAbility(AbilityPlugin):
    def on_apply(self):
        hook = BattleHook("gale_wings_prio", 10, self.priority_mod)
        hook.source_plugin = self
        self.owner.hooks.register("on_priority_calc", hook)

    def priority_mod(self, current_priority, attacker, move):
        # 检查是否满血且为飞行系招式
        # 注意：这里需要考虑是否应该用 max_hp, 有些实现可能用百分比
        # Gen 7+: 只有满血才有效
        max_hp = attacker.context.pokemon.stats.hp
        is_full_hp = attacker.current_hp >= max_hp 
        is_flying_move = self.check_flying_move(move)
        
        if is_full_hp and is_flying_move:
            return current_priority + 1
        return current_priority

    def check_flying_move(self, move):
        # 简单检查属性名称，兼容中文
        return move.type_name in ['flying', '飞行']


# 5. 自信过度 (Moxie) - ID: 153
@AbilityRegistry.register(153) 
class MoxieAbility(AbilityPlugin):
    def on_apply(self):
        # 注册击败对手时的事件钩子
        hook = BattleHook("moxie_trigger", 10, self.on_kill)
        hook.source_plugin = self
        self.owner.hooks.register("on_opponent_faint", hook)

    def on_kill(self, attacker, defender, logger_obj):
        """当击败对手时触发"""
        # 获取当前物理攻击等级 (1)
        curr_lvl = attacker.stat_levels.get(1, 0)
        if curr_lvl < 6:
            attacker.stat_levels[1] = curr_lvl + 1
            logger_obj.log(f"{attacker.context.pokemon.name} 充满了自信！攻击力提升了！\n\n")

# 6. 异兽提升 (Beast Boost) - ID: 224
@AbilityRegistry.register(224)
class BeastBoostAbility(AbilityPlugin):
    def on_apply(self):
        hook = BattleHook("beast_boost_trigger", 10, self.on_kill)
        hook.source_plugin = self
        self.owner.hooks.register("on_opponent_faint", hook)

    def on_kill(self, attacker, defender, logger_obj):
        # 1. 获取当前所有实战数值 (攻击、防御、特攻、特防、速度)
        stats = self.owner.context.pokemon.stats # 注意：应该从 context 取基础值，或者 get_modified_stats?
        # 异兽提升通常计算的是“实战数值”（含能力等级、道具等修正，但不含麻痹等状态降低？）
        # 官方规则：判定的是“能力变化后的最大值”。
        # 这里简化处理：直接读取 BattleState 计算后的数值（如果不方便就取基础值）
        # self.owner 是 BattleState，有 hooks 和 context
        # 为了准确，应该调用 stats_helper 计算当前面板。但 BattleEngine 在外部。
        # 这里简化：使用基础种族值+个体努力值+能力等级计算 (stat_levels 已在 state 中)
        # 为避免复杂依赖，暂时只比较 raw stats (不含等级)，或简单取基础 stats。
        # 用户需求中示例直接使用了 stats，这里沿用，但尽可能精确如果能获取。
        
        # 修正：直接读取 context.pokemon.stats 是基础值。
        # 若要精确，需结合 stat_levels。
        # 简单实现：仅比较面板数值 (context.pokemon.stats) 加上等级修正？
        # BattleLogic 不在这里，无法调用 _get_modified_stats。
        # 妥协：仅比较 context.pokemon.stats (假设性格努力值已计算在内)。
        
        stats = attacker.context.pokemon.stats
        stat_values = {
            1: stats.attack,
            2: stats.defense,
            3: stats.sp_attack,
            4: stats.sp_defense,
            5: stats.speed
        }
        
        # 2. 找出最高项 (取 ID 最小的最高项)
        # sort by value desc, then by id asc
        sorted_stats = sorted(stat_values.items(), key=lambda x: (-x[1], x[0]))
        best_stat_id = sorted_stats[0][0]
        
        stat_names = {1: "攻击", 2: "防御", 3: "特攻", 4: "特防", 5: "速度"}
        stat_name = stat_names.get(best_stat_id, "属性")
        
        # 3. 提升该等级
        curr_lvl = attacker.stat_levels.get(best_stat_id, 0)
        if curr_lvl < 6:
            attacker.stat_levels[best_stat_id] = curr_lvl + 1
            logger_obj.log(f"{attacker.context.pokemon.name} 的异兽提升发动了！{stat_name}提升了！\n\n")


# 7. 碎裂铠甲 (Weak Armor) - ID: 144
@AbilityRegistry.register(144)
class WeakArmorAbility(AbilityPlugin):
    def on_apply(self):
        # 注册受击后的事件钩子
        hook = BattleHook("weak_armor_trigger", 10, self.on_hit)
        hook.source_plugin = self
        self.owner.hooks.register("after_damage", hook)

    def on_hit(self, owner, attacker, move, damage_dealt, logger_obj):
        """受击后的回调"""
        # 1. 判断是否为物理攻击 (damage_class_id == 2)
        if move.damage_class_id == 2:
            logger_obj.log(f"{owner.context.pokemon.name} 的碎裂铠甲发动了！\n\n")
            
            # 2. 物理防御降低 1 级
            def_lvl = owner.stat_levels.get(2, 0)
            if def_lvl > -6:
                owner.stat_levels[2] = def_lvl - 1
                logger_obj.log(f"{owner.context.pokemon.name} 的防御降低了！\n\n")
            
            # 3. 速度提升 2 级
            spd_lvl = owner.stat_levels.get(5, 0)
            if spd_lvl < 6:
                owner.stat_levels[5] = min(6, spd_lvl + 2)
                logger_obj.log(f"{owner.context.pokemon.name} 的速度大幅提升了！\n\n")

# 8. 正义之心 (Justified) - ID: 154
@AbilityRegistry.register(154)
class JustifiedAbility(AbilityPlugin):
    def on_apply(self):
        hook = BattleHook("justified_trigger", 10, self.on_hit)
        hook.source_plugin = self
        self.owner.hooks.register("after_damage", hook)

    def on_hit(self, owner, attacker, move, damage_dealt, logger_obj):
        # 检查是否受到恶属性招式攻击
        if move.type_name in ['dark', '恶']:
            curr_atk = owner.stat_levels.get(1, 0)
            if curr_atk < 6:
                owner.stat_levels[1] = curr_atk + 1
                logger_obj.log(f"{owner.context.pokemon.name} 的正义之心发动了！攻击力提升！\n\n")





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


# --- 登场类实现 ---

@AbilityRegistry.register(2) # 降雨 (Drizzle)
class DrizzleAbility(AbilityPlugin):
    def on_entry(self, opponent: 'BattleState', logger_obj: 'BattleLogger', logic: Any = None):
        if logic:
            from .weather_service import WeatherService
            WeatherService.apply_rain(logic, logger_obj)

@AbilityRegistry.register(22) # 威吓 (Intimidate)
class IntimidateAbility(AbilityPlugin):
    def on_entry(self, opponent: 'BattleState', logger_obj: 'BattleLogger', logic: Any = None):
        logger_obj.log(f"{self.owner.context.pokemon.name} 的威吓发动了！\n\n")
        current_stage = opponent.stat_levels.get(1, 0)
        if current_stage > -6:
            opponent.stat_levels[1] = current_stage - 1
            logger_obj.log(f"{opponent.context.pokemon.name} 的攻击降低了！\n\n")
        else:
            logger_obj.log(f"{opponent.context.pokemon.name} 的攻击无法再降低了！\n\n")

# --- 危机类实现 (Pinch) ---

@AbilityRegistry.register(65) # 茂盛 (Overgrow)
class OvergrowAbility(PinchAbility):
    def __init__(self, owner):
        super().__init__(owner, boost_types=['grass', '草'])

@AbilityRegistry.register(66) # 猛火 (Blaze)
class BlazeAbility(PinchAbility):
    def __init__(self, owner):
        super().__init__(owner, boost_types=['fire', '火'])

@AbilityRegistry.register(67) # 激流 (Torrent)
class TorrentAbility(PinchAbility):
    def __init__(self, owner):
        super().__init__(owner, boost_types=['water', '水'])

@AbilityRegistry.register(68) # 虫之预感 (Swarm)
class SwarmAbility(PinchAbility):
    def __init__(self, owner):
        super().__init__(owner, boost_types=['bug', '虫'])
