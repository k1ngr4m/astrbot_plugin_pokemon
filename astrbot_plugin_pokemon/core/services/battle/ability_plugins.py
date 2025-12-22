from typing import Dict, Type, Any, Optional, List, TYPE_CHECKING
from .hook_manager import BattleHook
from .status_plugins import VolatileStatusPlugin

# ==========================================
# 破格 (Mold Breaker) 可无视的特性列表
# ==========================================
MOLD_BREAKER_IGNORABLE_IDS = {
    # 1. 属性吸收与免疫类 (Immunity)
    10,  # 蓄电 (Volt Absorb)
    11,  # 储水 (Water Absorb)
    18,  # 引火 (Flash Fire)
    26,  # 飘浮 (Levitate)
    31,  # 避雷针 (Lightning Rod)
    43,  # 隔音 (Soundproof)
    78,  # 电气引擎 (Motor Drive)
    87,  # 干燥皮肤 (Dry Skin)
    114, # 引水 (Storm Drain)
    157, # 食草 (Sap Sipper)
    171, # 防弹 (Bulletproof)
    270, # 热交换 (Thermal Exchange)
    272, # 净化之盐 (Purifying Salt)
    273, # 烤得恰到好处 (Well-Baked Body)
    297, # 食土 (Earth Eater)

    # 2. 伤害减免与生存类 (Defense & Survival)
    4,   # 战斗盔甲 (Battle Armor)
    5,   # 结实 (Sturdy)
    25,  # 神奇守护 (Wonder Guard)
    47,  # 厚脂肪 (Thick Fat)
    75,  # 硬壳盔甲 (Shell Armor)
    85,  # 耐热 (Heatproof)
    111, # 过滤 (Filter)
    116, # 坚硬岩石 (Solid Rock)
    136, # 多重鳞片 (Multiscale)
    209, # 画皮 (Disguise)
    218, # 毛茸茸 (Fluffy)
    244, # 庞克摇滚 (Punk Rock)
    246, # 冰鳞粉 (Ice Scales)

    # 3. 能力等级与状态保护类 (Status Protection)
    6,   # 湿气 (Damp)
    7,   # 柔软 (Limber)
    12,  # 迟钝 (Oblivious)
    15,  # 不眠 (Insomnia)
    17,  # 免疫 (Immunity)
    19,  # 鳞粉 (Shield Dust)
    20,  # 我行我素 (Own Tempo)
    21,  # 吸盘 (Suction Cups)
    29,  # 恒净之躯 (Clear Body)
    39,  # 精神力 (Inner Focus)
    40,  # 熔岩铠甲 (Magma Armor)
    41,  # 水幕 (Water Veil)
    51,  # 锐利目光 (Keen Eye)
    52,  # 怪力钳 (Hyper Cutter)
    60,  # 黏着 (Sticky Hold)
    72,  # 干劲 (Vital Spirit)
    73,  # 白色烟雾 (White Smoke)
    86,  # 单纯 (Simple)
    102, # 叶子防守 (Leaf Guard)
    109, # 纯朴 (Unaware)
    122, # 花之礼 (Flower Gift)
    126, # 唱反调 (Contrary)
    132, # 友情防守 (Friend Guard)
    140, # 心灵感应 (Telepathy)
    145, # 健壮胸肌 (Big Pecks)
    147, # 奇迹皮肤 (Wonder Skin)
    156, # 魔法镜 (Magic Bounce)
    165, # 芳香幕 (Aroma Veil)
    175, # 甜幕 (Sweet Veil)
    219, # 鲜艳之躯 (Dazzling)
    240, # 镜甲 (Mirror Armor)
    283, # 坚如磐石 (Good as Gold)
    296, # 鳞甲尾 (Armor Tail)

    # 4. 其他修正类 (Miscellaneous)
    8,   # 沙隐 (Sand Veil)
    63,  # 神奇鳞片 (Marvel Scale)
    77,  # 蹒跚 (Tangled Feet)
    81,  # 雪隐 (Snow Cloak)
    134, # 重金属 (Heavy Metal)
    135, # 轻金属 (Light Metal)
}

if TYPE_CHECKING:
    from .battle_engine import BattleState, BattleLogger

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

# --- 免疫类实现 ---

# 1. 飘浮 (Levitate) - ID: 26
@AbilityRegistry.register(26)
class LevitateAbility(ImmunityAbility):
    def __init__(self, owner):
        super().__init__(owner, target_type='ground', msg="由于飘浮特性，地面系招式无效！")


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
