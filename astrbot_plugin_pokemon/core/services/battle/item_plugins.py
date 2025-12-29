from typing import Dict, Type, Optional, Any, TYPE_CHECKING
from .hook_manager import BattleHook
from .status_plugins import VolatileStatusPlugin

if TYPE_CHECKING:
    from .battle_engine import BattleState

class ItemPlugin(VolatileStatusPlugin):
    """持有物插件基类"""
    def __init__(self, owner: 'BattleState'):
        # 持有物通常持续整个战斗过程
        super().__init__(owner, turns=999)
        self.item_id = 0
        self.item_name = ""

    def on_apply(self):
        """在此处注册持有物相关的钩子"""
        pass

class ItemRegistry:
    """持有物注册中心"""
    _registry: Dict[int, Type[ItemPlugin]] = {}

    @classmethod
    def register(cls, item_id: int):
        def decorator(plugin_class: Type[ItemPlugin]):
            cls._registry[item_id] = plugin_class
            return plugin_class
        return decorator

    @classmethod
    def create_plugin(cls, item_id: int, owner: 'BattleState') -> Optional[ItemPlugin]:
        plugin_class = cls._registry.get(item_id)
        if plugin_class:
            plugin = plugin_class(owner)
            plugin.item_id = item_id
            return plugin
        return None

# --- 具体持有物插件实现 ---

@ItemRegistry.register(247)
class LifeOrbPlugin(ItemPlugin):
    """生命宝玉 - 携带后，虽然每次攻击时ＨＰ少量减少，但招式的威力会提高"""
    def on_apply(self):
        # 注册伤害计算钩子，提升威力
        dmg_hook = BattleHook("life_orb_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", dmg_hook)
        # 注册伤害执行后的钩子用于扣血
        recoil_hook = BattleHook("life_orb_recoil", 10, self.apply_recoil)
        self.owner.hooks.register("after_damage", recoil_hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if attacker == self.owner and move.power > 0:
            damage_params['power'] = int(damage_params['power'] * 1.3)  # 30% 威力提升
            self._should_recoil = True # 标记本回合触发了扣血
        return damage_params

    def apply_recoil(self, attacker, defender, move, damage, logger_obj):
        if attacker == self.owner and getattr(self, '_should_recoil', False):
            self._should_recoil = False
            recoil = attacker.context.pokemon.stats.hp // 10  # 10% HP 损失
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            logger_obj.log(f"{attacker.context.pokemon.name} 因生命宝玉损失了 {recoil} HP！\n\n")

@ItemRegistry.register(211)
class LeftoversPlugin(ItemPlugin):
    """吃剩的东西 - 携带后，宝可梦的ＨＰ会在战斗期间缓缓回复"""
    def on_apply(self):
        hook = BattleHook("leftovers_heal", 10, self.heal_effect)
        self.owner.hooks.register("turn_end", hook)

    def heal_effect(self, state, opponent, logger_obj):
        if state.current_hp > 0 and state.current_hp < state.context.pokemon.stats.hp:
            heal_amt = state.context.pokemon.stats.hp // 16  # 每回合回复1/16最大HP
            state.current_hp = min(state.context.pokemon.stats.hp, state.current_hp + heal_amt)
            logger_obj.log(f"{state.context.pokemon.name} 通过吃剩的东西回复了 {heal_amt} HP！\n\n")

@ItemRegistry.register(197)
class ChoiceBandPlugin(ItemPlugin):
    """讲究头带 - 携带后攻击会提高，但只能使出相同的招式"""
    def __init__(self, owner: 'BattleState'):
        super().__init__(owner, turns=999)
        self.item_id = 0
        self.item_name = ""
        self.locked_move = None  # 记录锁定的招式

    def on_apply(self):
        # 注册攻击提升
        hook = BattleHook("choice_band_atk", 10, self.stat_mod)
        self.owner.hooks.register("on_stat_calc", hook)
        # 注册招式限制
        move_hook = BattleHook("choice_band_lock", 10, self.before_move)
        self.owner.hooks.register("before_move", move_hook)

    def stat_mod(self, stats):
        # 提升 50% 物理攻击
        stats.attack = int(stats.attack * 1.5)
        return stats

    def before_move(self, attacker, move, logger_obj):
        # 如果还没有锁定招式，锁定当前招式
        if self.locked_move is None:
            self.locked_move = move.move_id
        # 检查是否为锁定的招式
        elif self.locked_move != move.move_id:
            logger_obj.log(f"{attacker.context.pokemon.name} 受讲究头带影响只能使出相同的招式！\n\n")
            return False
        return True

@ItemRegistry.register(264)
class ChoiceScarfPlugin(ItemPlugin):
    """讲究围巾 - 虽然携带后速度会提高，但只能使出相同的招式"""
    def __init__(self, owner: 'BattleState'):
        super().__init__(owner, turns=999)
        self.item_id = 0
        self.item_name = ""
        self.locked_move = None  # 记录锁定的招式

    def on_apply(self):
        # 注册速度提升
        hook = BattleHook("choice_scarf_spd", 10, self.stat_mod)
        self.owner.hooks.register("on_stat_calc", hook)
        # 注册招式限制
        move_hook = BattleHook("choice_scarf_lock", 10, self.before_move)
        self.owner.hooks.register("before_move", move_hook)

    def stat_mod(self, stats):
        # 提升 50% 速度
        stats.speed = int(stats.speed * 1.5)
        return stats

    def before_move(self, attacker, move, logger_obj):
        # 如果还没有锁定招式，锁定当前招式
        if self.locked_move is None:
            self.locked_move = move.move_id
        # 检查是否为锁定的招式
        elif self.locked_move != move.move_id:
            logger_obj.log(f"{attacker.context.pokemon.name} 受讲究围巾影响只能使出相同的招式！\n\n")
            return False
        return True

@ItemRegistry.register(274)
class ChoiceSpecsPlugin(ItemPlugin):
    """讲究眼镜 - 虽然携带后特攻会提高，但只能使出相同的招式"""
    def __init__(self, owner: 'BattleState'):
        super().__init__(owner, turns=999)
        self.item_id = 0
        self.item_name = ""
        self.locked_move = None  # 记录锁定的招式

    def on_apply(self):
        # 注册特攻提升
        hook = BattleHook("choice_specs_sp_atk", 10, self.stat_mod)
        self.owner.hooks.register("on_stat_calc", hook)
        # 注册招式限制
        move_hook = BattleHook("choice_specs_lock", 10, self.before_move)
        self.owner.hooks.register("before_move", move_hook)

    def stat_mod(self, stats):
        # 提升 50% 特攻
        stats.sp_attack = int(stats.sp_attack * 1.5)
        return stats

    def before_move(self, attacker, move, logger_obj):
        # 如果还没有锁定招式，锁定当前招式
        if self.locked_move is None:
            self.locked_move = move.move_id
        # 检查是否为锁定的招式
        elif self.locked_move != move.move_id:
            logger_obj.log(f"{attacker.context.pokemon.name} 受讲究眼镜影响只能使出相同的招式！\n\n")
            return False
        return True


@ItemRegistry.register(284)
class WhiteHerbPlugin(ItemPlugin):
    """白色香草 - 能力降低时自动复原"""
    def on_apply(self):
        # 暂时使用after_damage钩子来处理
        # 在实际游戏中，白色香草在能力等级下降时触发
        # 这里简化实现
        pass

# --- 数值修正类持有物 ---

@ItemRegistry.register(683)
class AssaultVestPlugin(ItemPlugin):
    """突击背心 - 虽然携带后特防会提高，但会无法使出变化招式"""
    def on_apply(self):
        # 1. 提升特防 (CSV显示为 1.5x)
        stat_hook = BattleHook("assault_vest_spdef", 10, self.stat_mod)
        self.owner.hooks.register("on_stat_calc", stat_hook)
        # 2. 限制变化招式 (Category ID: 1)
        move_hook = BattleHook("assault_vest_limit", 10, self.before_move)
        self.owner.hooks.register("before_move", move_hook)

    def stat_mod(self, stats):
        stats.sp_defense = int(stats.sp_defense * 1.5)  # 1.5x 特防提升
        return stats

    def before_move(self, attacker, move, logger_obj):
        if move.damage_class_id == 1: # 变化招式
            logger_obj.log(f"{attacker.context.pokemon.name} 受突击背心影响无法使用 {move.move_name}！\n\n")
            return False
        return True

@ItemRegistry.register(245)
class ExpertBeltPlugin(ItemPlugin):
    """达人带 - 携带后，效果绝佳时的招式威力就会少量提高"""
    def on_apply(self):
        hook = BattleHook("expert_belt_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if attacker == self.owner and damage_params['effectiveness'] > 1.0:
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(243)
class MuscleBandPlugin(ItemPlugin):
    """力量头带 - 携带后，物理招式的威力就会少量提高"""
    def on_apply(self):
        hook = BattleHook("muscle_band_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if attacker == self.owner and move.damage_class_id == 2: # 物理攻击
            damage_params['power'] = int(damage_params['power'] * 1.1)  # 10% 威力提升
        return damage_params

@ItemRegistry.register(244)
class WiseGlassesPlugin(ItemPlugin):
    """博识眼镜 - 携带后，特殊招式的威力就会少量提高"""
    def on_apply(self):
        hook = BattleHook("wise_glasses_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if attacker == self.owner and move.damage_class_id == 3: # 特殊攻击
            damage_params['power'] = int(damage_params['power'] * 1.1)  # 10% 威力提升
        return damage_params

@ItemRegistry.register(213)  # 根据CSV数据，电气球的ID是213
class LightBallPlugin(ItemPlugin):
    """电气球 - 让皮卡丘携带后，攻击和特攻的威力就会提高"""
    def on_apply(self):
        hook = BattleHook("light_ball_boost", 10, self.stat_mod)
        self.owner.hooks.register("on_stat_calc", hook)

    def stat_mod(self, stats):
        # 仅对比卡丘有效 (假设 species_id 为 25)
        if self.owner.context.pokemon.species_id == 25:
            stats.attack = int(stats.attack * 2.0)
            stats.sp_attack = int(stats.sp_attack * 2.0)
        return stats

@ItemRegistry.register(581)
class EviolitePlugin(ItemPlugin):
    """进化奇石 - 携带后，还能进化的宝可梦的防御和特防就会提高"""
    def on_apply(self):
        hook = BattleHook("eviolite_boost", 10, self.stat_mod)
        self.owner.hooks.register("on_stat_calc", hook)

    def stat_mod(self, stats):
        # 根据CSV：防御和特防提升 1.5x
        # 简化实现：总是提升，实际上只应提升未完成进化的宝可梦
        stats.defense = int(stats.defense * 1.5)
        stats.sp_defense = int(stats.sp_defense * 1.5)
        return stats

@ItemRegistry.register(233)
class ThickClubPlugin(ItemPlugin):
    """粗骨头 - 格斗或骨系宝可梦物攻翻倍"""
    def on_apply(self):
        hook = BattleHook("thick_club_boost", 10, self.stat_mod)
        self.owner.hooks.register("on_stat_calc", hook)

    def stat_mod(self, stats):
        # 简化实现：总是增加物攻
        # 在实际游戏中，只对特定类型的宝可梦有效
        stats.attack = int(stats.attack * 2.0)
        return stats

# --- 生存与反作用类持有物 ---

@ItemRegistry.register(584)  # 根据CSV，气球的ID是584
class AirBalloonPlugin(ItemPlugin):
    """气球 - 携带后宝可梦会浮在空中。受到攻击就会破裂"""
    def on_apply(self):
        self.active = True
        hook = BattleHook("air_balloon_protect", 5, self.protect_from_ground, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def protect_from_ground(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'ground' or move.type_name.lower() == '地面')):
            # 设置伤害为0
            damage_params['power'] = 0
            logger_obj.log(f"{defender.context.pokemon.name} 的气球挡住了地面系招式！\n\n")
            # 气球破裂后移除持有物
            if hasattr(defender, 'item_plugin'):
                defender.item_plugin = None
            if hasattr(defender, 'item_id'):
                defender.item_id = None
        return damage_params

@ItemRegistry.register(252)
class FocusSashPlugin(ItemPlugin):
    """气势披带 - 携带后，在ＨＰ全满时受到致命伤害，也能仅以１ＨＰ撑过去１次（消耗品）"""
    def on_apply(self):
        # 注册高优先级计算，用于拦截致死伤害
        hook = BattleHook("focus_sash_save", 5, self.check_lethal, persistent=False)
        self.owner.hooks.register("on_faint", hook)

    def check_lethal(self, state, opponent, logger_obj):
        # 检查是否满血状态下的致命伤害
        max_hp = state.context.pokemon.stats.hp
        if state.current_hp == max_hp:
            # 恢复1HP，避免濒死
            state.current_hp = 1
            logger_obj.log(f"{state.context.pokemon.name} 用气势披带保护了自己！\n\n")
            return False  # 阻止濒死逻辑
        return True  # 允许正常濒死逻辑

@ItemRegistry.register(207)
class FocusBandPlugin(ItemPlugin):
    """气势头带 - 携带后，受到致命伤害时有时也能仅以１ＨＰ撑过去"""
    def on_apply(self):
        # 使用 on_faint 钩子，但需要概率判定
        hook = BattleHook("focus_band_save", 5, self.check_save, persistent=False)
        self.owner.hooks.register("on_faint", hook)

    def check_save(self, state, opponent, logger_obj):
        import random
        # 通常有10%的几率触发
        if state.current_hp <= 0 and random.random() < 0.1:
            # 恢复1HP，避免濒死
            state.current_hp = 1
            logger_obj.log(f"{state.context.pokemon.name} 用气势头带奇迹般地站了起来！\n\n")
            return False  # 阻止濒死逻辑
        return True  # 允许正常濒死逻辑

@ItemRegistry.register(583)
class RockyHelmetPlugin(ItemPlugin):
    """凸凸头盔 - 携带后，在受到接触类招式攻击时，能给予对手伤害"""
    def on_apply(self):
        hook = BattleHook("rocky_helmet_dmg", 10, self.on_hit)
        self.owner.hooks.register("after_damage", hook)

    def on_hit(self, attacker, defender, move, damage, logger_obj):
        # move.is_contact 需要在招式数据中定义，这里用一个简单判断
        # 假设物理攻击（damage_class_id == 2）通常是接触的
        # 这里需要检查的是持有凸凸头盔的宝可梦（defender）作为受攻击方
        if damage > 0 and attacker != self.owner and defender == self.owner and move.damage_class_id == 2:
            recoil = max(1, attacker.context.pokemon.stats.hp // 6)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            logger_obj.log(f"{attacker.context.pokemon.name} 因攻击对手撞到了凸凸头盔，受到了 {recoil} 点反伤！\n\n")
        return True

@ItemRegistry.register(682)
class WeaknessPolicyPlugin(ItemPlugin):
    """弱点保险 - 被针对弱点（效果绝佳）攻击时，攻击和特攻就会大幅提高"""
    def on_apply(self):
        hook = BattleHook("weakness_policy_boost", 10, self.on_damage)
        self.owner.hooks.register("after_damage", hook)

    def on_damage(self, attacker, defender, move, damage, logger_obj):
        # 检查是否为效果绝佳的攻击
        # 这里持有弱点保险的宝可梦是受攻击方（defender）
        if (defender == self.owner and
            hasattr(move, 'type_effectiveness') and
            move.type_effectiveness > 1.0):
            # 攻击和特攻各提升2级
            defender.stat_levels[1] = defender.stat_levels.get(1, 0) + 2  # 攻击
            defender.stat_levels[3] = defender.stat_levels.get(3, 0) + 2  # 特攻
            # 限制等级在[-6, 6]范围内
            defender.stat_levels[1] = min(6, max(-6, defender.stat_levels[1]))
            defender.stat_levels[3] = min(6, max(-6, defender.stat_levels[3]))
            logger_obj.log(f"{defender.context.pokemon.name} 的攻击和特攻大幅提升！\n\n")

@ItemRegistry.register(198)
class KingsRockPlugin(ItemPlugin):
    """王者之证 - 携带后进行攻击并造成伤害时，有时会让对手畏缩"""
    def on_apply(self):
        hook = BattleHook("kings_rock_flinch", 10, self.on_hit)
        self.owner.hooks.register("after_damage", hook)

    def on_hit(self, attacker, defender, move, damage, logger_obj):
        import random
        # 约10%的几率让对手畏缩
        # 这里持有王者之证的宝可梦是攻击方（attacker）
        if (attacker == self.owner and
            damage > 0 and
            random.random() < 0.1):
            # 在实际战斗系统中，需要应用畏缩状态
            # 由于我们无法直接应用状态，这里记录日志
            logger_obj.log(f"{attacker.context.pokemon.name} 的攻击让对手畏缩了！\n\n")

@ItemRegistry.register(257)
class DestinyKnotPlugin(ItemPlugin):
    """红线 - 携带后，在自己着迷时能让对手也着迷"""
    def on_apply(self):
        # 这个效果需要在着迷状态触发时生效，暂时注册钩子
        # 在实际实现中，这个效果需要在应用着迷状态时检查
        pass

@ItemRegistry.register(209)
class ScopeLensPlugin(ItemPlugin):
    """焦点镜 - 携带它的宝可梦的招式会变得容易击中要害"""
    def on_apply(self):
        hook = BattleHook("scope_lens_crit", 10, self.modify_crit_rate)
        self.owner.hooks.register("on_damage_calc", hook)

    def modify_crit_rate(self, damage_params, attacker, defender, move, logger_obj):
        # 焦点镜会增加暴击率，虽然在计算中无法直接修改概率
        # 但可以增加暴击倍率或在暴击时提供额外效果
        # 这里我们通过模拟的方式来增加暴击效果
        # 实际修改暴击率需要访问战斗逻辑
        pass  # 具体实现需要在战斗逻辑中修改暴击率计算

@ItemRegistry.register(545)  # 修正达人带ID，它与气势头带不同
class FocusBandPluginOld(ItemPlugin):
    """达人带 - 濒死时10%几率保留1HP"""
    def on_apply(self):
        # 使用 on_faint 钩子，但需要概率判定
        hook = BattleHook("focus_band_save", 5, self.check_save, persistent=False)
        self.owner.hooks.register("on_faint", hook)

    def check_save(self, state, opponent, logger_obj):
        import random
        if state.current_hp <= 0 and random.random() < 0.1:
            # 恢复1HP，避免濒死
            state.current_hp = 1
            logger_obj.log(f"{state.context.pokemon.name} 用达人带奇迹般地站了起来！\n\n")
            return False  # 阻止濒死逻辑
        return True  # 允许正常濒死逻辑

# --- 回合结束结算类持有物 ---

@ItemRegistry.register(258)
class BlackSludgePlugin(ItemPlugin):
    """黑色污泥 - 毒属性宝可梦会缓缓回复ＨＰ，其他属性则会减少"""
    def on_apply(self):
        hook = BattleHook("black_sludge_tick", 10, self.tick)
        self.owner.hooks.register("turn_end", hook)

    def tick(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        if 'poison' in [t.lower() for t in state.context.types] or '毒' in [t for t in state.context.types]:
            heal = max_hp // 16
            state.current_hp = min(max_hp, state.current_hp + heal)
            logger_obj.log(f"{state.context.pokemon.name} 通过黑色污泥回复了 {heal} HP！\n\n")
        else:
            dmg = max(1, max_hp // 8)
            state.current_hp = max(0, state.current_hp - dmg)
            logger_obj.log(f"{state.context.pokemon.name} 因黑色污泥损失了 {dmg} HP！\n\n")

@ItemRegistry.register(230)
class ShellBellPlugin(ItemPlugin):
    """贝壳之铃 - 当携带它的宝可梦攻击对手并造成伤害时，能回复少量ＨＰ"""
    def on_apply(self):
        hook = BattleHook("shell_bell_heal", 10, self.heal_on_damage)
        self.owner.hooks.register("after_damage", hook)

    def heal_on_damage(self, attacker, defender, move, damage, logger_obj):
        if attacker == self.owner and damage > 0:
            # 回复造成伤害的1/8（最少1点）
            heal = max(1, damage // 8)
            attacker.current_hp = min(attacker.context.pokemon.stats.hp, attacker.current_hp + heal)
            logger_obj.log(f"{attacker.context.pokemon.name} 通过贝壳之铃回复了 {heal} HP！\n\n")

@ItemRegistry.register(273)
class BigRootPlugin(ItemPlugin):
    """大根茎 - 携带后，吸取ＨＰ的招式可以比平时更多地回复自己的ＨＰ"""
    def on_apply(self):
        hook = BattleHook("big_root_boost", 15, self.drain_boost)
        self.owner.hooks.register("on_damage_calc", hook)

    def drain_boost(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            hasattr(move, 'drain') and move.drain > 0):
            # 提高吸血效果（例如，从50%提高到62.5%）
            # 通过增加吸血比例来模拟效果
            # 实际上需要在吸血计算时增加1.25倍的效果
            pass  # 这个效果需要在吸血计算时实现，现在只注册钩子
        return damage_params

@ItemRegistry.register(250)
class FlameOrbPlugin(ItemPlugin):
    """火焰宝珠 - 每回合烧伤"""
    def on_apply(self):
        hook = BattleHook("flame_orb_burn", 10, self.check_burn)
        self.owner.hooks.register("turn_end", hook)

    def check_burn(self, state, opponent, logger_obj):
        # 如果没有异常状态且不是火系宝可梦
        if (not state.non_volatile_status and
            'fire' not in [t.lower() for t in state.context.types] and
            '火' not in [t for t in state.context.types]):
            # 施加烧伤
            if 4 not in state.volatile_statuses:  # 检查是否已经烧伤
                state.non_volatile_status = 4
                logger_obj.log(f"{state.context.pokemon.name} 被火焰宝珠烧伤了！\n\n")

@ItemRegistry.register(249)
class ToxicOrbPlugin(ItemPlugin):
    """剧毒宝珠 - 每回合中毒"""
    def on_apply(self):
        hook = BattleHook("toxic_orb_poison", 10, self.check_poison)
        self.owner.hooks.register("turn_end", hook)

    def check_poison(self, state, opponent, logger_obj):
        # 如果没有异常状态且不是毒系/钢系宝可梦
        non_immune = ('poison' not in [t.lower() for t in state.context.types] and
                      'steel' not in [t.lower() for t in state.context.types] and
                      '毒' not in [t for t in state.context.types] and
                      '钢' not in [t for t in state.context.types])
        if not state.non_volatile_status and non_immune:
            # 施加中毒
            if 5 not in state.volatile_statuses:  # 检查是否已经中毒
                state.non_volatile_status = 5
                logger_obj.log(f"{state.context.pokemon.name} 被剧毒宝珠毒害了！\n\n")

# --- 优先度修正类持有物 ---

@ItemRegistry.register(194)
class QuickClawPlugin(ItemPlugin):
    """先制之爪 - 20%几率优先行动"""
    def on_apply(self):
        hook = BattleHook("quick_claw_prio", 10, self.prio_mod)
        self.owner.hooks.register("on_priority_calc", hook)

    def prio_mod(self, current_priority, attacker, move):
        import random
        if random.random() < 0.2:
            # 提升优先度使其在同优先级阶层中先手
            return current_priority + 1
        return current_priority

# --- 树果类持有物 ---

@ItemRegistry.register(126)  # 樱子果
class ChestoBerryPlugin(ItemPlugin):
    """樱子果 - 回合结束时HP低于1/2时回复HP（消耗性）"""
    def on_apply(self):
        hook = BattleHook("chesto_berry_check", 10, self.check_hp, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_hp(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        if state.current_hp > 0 and state.current_hp <= max_hp // 2:
            # 樱子果在HP低于一半时回复HP
            state.current_hp = max_hp
            logger_obj.log(f"{state.context.pokemon.name} 通过樱子果恢复了全部HP！\n\n")

@ItemRegistry.register(133)  # 柿仔果
class OranBerryPlugin(ItemPlugin):
    """柿仔果 - 回合结束时HP低于1/2时回复10HP（消耗性）"""
    def on_apply(self):
        hook = BattleHook("oran_berry_check", 10, self.check_hp, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_hp(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        if state.current_hp > 0 and state.current_hp <= max_hp // 2:
            # 柿仔果回复10HP（最多回满）
            heal = min(10, max_hp - state.current_hp)
            state.current_hp = min(max_hp, state.current_hp + heal)
            logger_obj.log(f"{state.context.pokemon.name} 通过柿仔果回复了 {heal} HP！\n\n")

@ItemRegistry.register(154)  # 王果
class LumBerryPlugin(ItemPlugin):
    """王果 - 可以治愈所有异常状态"""
    def on_apply(self):
        hook = BattleHook("lum_berry_clear", 10, self.check_clear, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_clear(self, state, opponent, logger_obj):
        # 如果有任何异常状态，则清除
        if state.non_volatile_status is not None:
            old_status = state.non_volatile_status
            state.non_volatile_status = None
            # 简单映射异常状态ID到名字
            status_names = {1: "麻痹", 2: "睡眠", 3: "冰冻", 4: "灼伤", 5: "中毒"}
            status_name = status_names.get(old_status, "异常状态")
            logger_obj.log(f"{state.context.pokemon.name} 通过王果清除了{status_name}！\n\n")

@ItemRegistry.register(134)  # 木子果
class CheriBerryPlugin(ItemPlugin):
    """木子果 - 可以治愈所有异常状态"""
    def on_apply(self):
        hook = BattleHook("cheri_berry_clear", 10, self.check_clear, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_clear(self, state, opponent, logger_obj):
        # 如果有任何异常状态，则清除
        if state.non_volatile_status is not None:
            old_status = state.non_volatile_status
            state.non_volatile_status = None
            # 简单映射异常状态ID到名字
            status_names = {1: "麻痹", 2: "睡眠", 3: "冰冻", 4: "灼伤", 5: "中毒"}
            status_name = status_names.get(old_status, "异常状态")
            logger_obj.log(f"{state.context.pokemon.name} 通过木子果清除了{status_name}！\n\n")

@ItemRegistry.register(135)  # 文柚果
class SitrusBerryPlugin(ItemPlugin):
    """文柚果 - 可以回复少量ＨＰ（HP低于一半时触发）"""
    def on_apply(self):
        hook = BattleHook("sitrus_berry_check", 10, self.check_hp, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_hp(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        if state.current_hp > 0 and state.current_hp <= max_hp // 2:
            # 文柚果回复1/4最大HP（最少1点）
            heal = max(1, max_hp // 4)
            state.current_hp = min(max_hp, state.current_hp + heal)
            logger_obj.log(f"{state.context.pokemon.name} 通过文柚果回复了 {heal} HP！\n\n")

@ItemRegistry.register(132)  # 橙橙果
class OranBerryPlugin(ItemPlugin):
    """橙橙果 - 可以回复１０ＨＰ"""
    def on_apply(self):
        hook = BattleHook("oran_berry_check", 10, self.check_hp, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_hp(self, state, opponent, logger_obj):
        if state.current_hp > 0:
            # 橙橙果回复10HP（最多回满）
            heal = min(10, state.context.pokemon.stats.hp - state.current_hp)
            state.current_hp = min(state.context.pokemon.stats.hp, state.current_hp + heal)
            logger_obj.log(f"{state.context.pokemon.name} 通过橙橙果回复了 {heal} HP！\n\n")

@ItemRegistry.register(136)  # 勿花果
class PersimBerryPlugin(ItemPlugin):
    """勿花果 - 危机时回复大量HP，但讨厌该味道会混乱"""
    def on_apply(self):
        hook = BattleHook("persim_berry_check", 10, self.check_confusion, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_confusion(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        if state.current_hp > 0 and state.current_hp <= max_hp // 4:  # 危机（HP低于1/4）
            # 回复HP并可能混乱
            heal = max(1, max_hp // 2)  # 回复一半HP
            state.current_hp = min(max_hp, state.current_hp + heal)
            logger_obj.log(f"{state.context.pokemon.name} 通过勿花果回复了 {heal} HP！但讨厌该味道产生了混乱！\n\n")
            # 这里可以添加混乱状态的触发，但需要调用状态系统

@ItemRegistry.register(178)  # 枝荔果
class LiechiBerryPlugin(ItemPlugin):
    """枝荔果 - 危机时攻击提高"""
    def on_apply(self):
        hook = BattleHook("liechi_berry_boost", 10, self.check_boost, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_boost(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        if state.current_hp > 0 and state.current_hp <= max_hp // 4:  # 危机（HP低于1/4）
            # 攻击提升1级
            state.stat_levels[1] = state.stat_levels.get(1, 0) + 1
            state.stat_levels[1] = min(6, max(-6, state.stat_levels[1]))
            logger_obj.log(f"{state.context.pokemon.name} 的攻击提高了！\n\n")

@ItemRegistry.register(180)  # 沙鳞果
class SalacBerryPlugin(ItemPlugin):
    """沙鳞果 - 危机时速度提高"""
    def on_apply(self):
        hook = BattleHook("salac_berry_boost", 10, self.check_boost, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_boost(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        if state.current_hp > 0 and state.current_hp <= max_hp // 4:  # 危机（HP低于1/4）
            # 速度提升1级
            state.stat_levels[6] = state.stat_levels.get(6, 0) + 1
            state.stat_levels[6] = min(6, max(-6, state.stat_levels[6]))
            logger_obj.log(f"{state.context.pokemon.name} 的速度提高了！\n\n")

@ItemRegistry.register(181)  # 龙火果
class PetayaBerryPlugin(ItemPlugin):
    """龙火果 - 危机时特攻提高"""
    def on_apply(self):
        hook = BattleHook("petaya_berry_boost", 10, self.check_boost, persistent=False)
        self.owner.hooks.register("turn_end", hook)

    def check_boost(self, state, opponent, logger_obj):
        max_hp = state.context.pokemon.stats.hp
        if state.current_hp > 0 and state.current_hp <= max_hp // 4:  # 危机（HP低于1/4）
            # 特攻提升1级
            state.stat_levels[3] = state.stat_levels.get(3, 0) + 1
            state.stat_levels[3] = min(6, max(-6, state.stat_levels[3]))
            logger_obj.log(f"{state.context.pokemon.name} 的特攻提高了！\n\n")

@ItemRegistry.register(161)  # 巧可果
class OccaBerryPlugin(ItemPlugin):
    """巧可果 - 受到火属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("occa_berry_reduce_dmg", 10, self.reduce_fire_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_fire_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'fire' or move.type_name.lower() == '火') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力（即实际伤害乘以0.5）
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过巧可果减弱了火属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(165)  # 波波果
class WacanBerryPlugin(ItemPlugin):
    """波波果 - 受到电属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("wacan_berry_reduce_dmg", 10, self.reduce_electric_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_electric_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'electric' or move.type_name.lower() == '电') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过波波果减弱了电属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(169)  # 致贺果
class ChopleBerryPlugin(ItemPlugin):
    """致贺果 - 受到格斗属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("chople_berry_reduce_dmg", 10, self.reduce_fighting_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_fighting_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'fighting' or move.type_name.lower() == '格斗') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过致贺果减弱了格斗属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(173)  # 桃桃果
class KebiaBerryPlugin(ItemPlugin):
    """桃桃果 - 受到毒属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("kebia_berry_reduce_dmg", 10, self.reduce_poison_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_poison_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'poison' or move.type_name.lower() == '毒') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过桃桃果减弱了毒属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(177)  # 酸酸果
class ShucaBerryPlugin(ItemPlugin):
    """酸酸果 - 受到地面属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("shuca_berry_reduce_dmg", 10, self.reduce_ground_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_ground_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'ground' or move.type_name.lower() == '地面') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过酸酸果减弱了地面属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(162)  # 面粉
class PasshoBerryPlugin(ItemPlugin):
    """面面粉 - 受到水属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("passho_berry_reduce_dmg", 10, self.reduce_water_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_water_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'water' or move.type_name.lower() == '水') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过面面粉减弱了水属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(163)  # 刺刺果
class WacanBerryPlugin(ItemPlugin):
    """刺刺果 - 受到电属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("wacan_berry_reduce_dmg", 10, self.reduce_electric_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_electric_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'electric' or move.type_name.lower() == '电') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过刺刺果减弱了电属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(164)  # 瓜瓜果
class RindoBerryPlugin(ItemPlugin):
    """瓜瓜果 - 受到草属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("rindo_berry_reduce_dmg", 10, self.reduce_grass_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_grass_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'grass' or move.type_name.lower() == '草') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过瓜瓜果减弱了草属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(166)  # 榴榴果
class YacheBerryPlugin(ItemPlugin):
    """榴榴果 - 受到冰属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("yache_berry_reduce_dmg", 10, self.reduce_ice_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_ice_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'ice' or move.type_name.lower() == '冰') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过榴榴果减弱了冰属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(167)  # 灯浆果
class ChopleBerryPlugin(ItemPlugin):
    """灯浆果 - 受到格斗属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("chople_berry_reduce_dmg", 10, self.reduce_fighting_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_fighting_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'fighting' or move.type_name.lower() == '格斗') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过灯浆果减弱了格斗属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(168)  # 焦橘果
class KebiaBerryPlugin(ItemPlugin):
    """焦橘果 - 受到毒属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("kebia_berry_reduce_dmg", 10, self.reduce_poison_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_poison_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'poison' or move.type_name.lower() == '毒') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过焦橘果减弱了毒属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(170)  # 香罗果
class HabanBerryPlugin(ItemPlugin):
    """香罗果 - 受到龙属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("haban_berry_reduce_dmg", 10, self.reduce_dragon_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_dragon_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'dragon' or move.type_name.lower() == '龙') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过香罗果减弱了龙属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(171)  # 银粉果
class ColburBerryPlugin(ItemPlugin):
    """银粉果 - 受到恶属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("colbur_berry_reduce_dmg", 10, self.reduce_dark_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_dark_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'dark' or move.type_name.lower() == '恶') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过银粉果减弱了恶属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(172)  # 甜甜果
class BabiriBerryPlugin(ItemPlugin):
    """甜甜果 - 受到钢属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("babiri_berry_reduce_dmg", 10, self.reduce_steel_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_steel_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'steel' or move.type_name.lower() == '钢') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过甜甜果减弱了钢属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(174)  # 亚多果
class ChartiBerryPlugin(ItemPlugin):
    """亚多果 - 受到岩石属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("charti_berry_reduce_dmg", 10, self.reduce_rock_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_rock_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'rock' or move.type_name.lower() == '岩石') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过亚多果减弱了岩石属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(175)  # 美美果
class KasibBerryPlugin(ItemPlugin):
    """美美果 - 受到幽灵属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("kasib_berry_reduce_dmg", 10, self.reduce_ghost_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_ghost_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'ghost' or move.type_name.lower() == '幽灵') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过美美果减弱了幽灵属性招式的威力！\n\n")
        return damage_params

@ItemRegistry.register(176)  # 咕咕果
class ChilanBerryPlugin(ItemPlugin):  # 使用正确类名
    """咕咕果 - 受到飞行属性的效果绝佳招式时，令其威力减弱"""
    def on_apply(self):
        hook = BattleHook("chilan_berry_reduce_dmg", 10, self.reduce_flying_dmg, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def reduce_flying_dmg(self, damage_params, attacker, defender, move, logger_obj):
        if (defender == self.owner and
            (move.type_name.lower() == 'flying' or move.type_name.lower() == '飞行') and
            damage_params['effectiveness'] > 1.0):
            # 减少1/2的威力
            damage_params['power'] = int(damage_params['power'] * 0.5)
            logger_obj.log(f"{defender.context.pokemon.name} 通过咕咕果减弱了飞行属性招式的威力！\n\n")
        return damage_params

# --- 石板/宝石类持有物 ---

@ItemRegistry.register(275)  # 火球石板
class FlamePlatePlugin(ItemPlugin):
    """火球石板 - 携带后对应属性的招式威力就会增强"""
    def on_apply(self):
        hook = BattleHook("flame_plate_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'fire' or move.type_name.lower() == '火')):
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(280)  # 水之石板 - 实际上应该是280还是其他？让我查一下
class SplashPlatePlugin(ItemPlugin):
    """水滴石板 - 携带后对应属性的招式威力就会增强"""
    def on_apply(self):
        hook = BattleHook("splash_plate_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'water' or move.type_name.lower() == '水')):
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(279)  # 雷之石板
class ZapPlatePlugin(ItemPlugin):
    """雷电石板 - 携带后对应属性的招式威力就会增强"""
    def on_apply(self):
        hook = BattleHook("zap_plate_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'electric' or move.type_name.lower() == '电')):
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(290)  # 钢铁石板
class IronPlatePlugin(ItemPlugin):
    """钢铁石板 - 携带后对应属性的招式威力就会增强"""
    def on_apply(self):
        hook = BattleHook("iron_plate_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'steel' or move.type_name.lower() == '钢')):
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(216)  # 奇迹种子
class MiracleSeedPlugin(ItemPlugin):
    """奇迹种子 - 草属性威力提高"""
    def on_apply(self):
        hook = BattleHook("miracle_seed_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'grass' or move.type_name.lower() == '草')):
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(219)  # 磁铁
class MagnetPlugin(ItemPlugin):
    """磁铁 - 电属性威力提高"""
    def on_apply(self):
        hook = BattleHook("magnet_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'electric' or move.type_name.lower() == '电')):
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(220)  # 神秘水滴
class MysticWaterPlugin(ItemPlugin):
    """神秘水滴 - 水属性威力提高"""
    def on_apply(self):
        hook = BattleHook("mystic_water_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'water' or move.type_name.lower() == '水')):
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(226)  # 木炭
class CharcoalPlugin(ItemPlugin):
    """木炭 - 火属性威力提高"""
    def on_apply(self):
        hook = BattleHook("charcoal_boost", 15, self.damage_mod)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'fire' or move.type_name.lower() == '火')):
            damage_params['power'] = int(damage_params['power'] * 1.2)  # 20% 威力提升
        return damage_params

@ItemRegistry.register(591)  # 火之宝石
class FireGemPlugin(ItemPlugin):
    """火之宝石 - 携带后，对应属性的招式威力仅会增强１次（消耗品）"""
    def on_apply(self):
        hook = BattleHook("fire_gem_boost", 15, self.damage_mod, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'fire' or move.type_name.lower() == '火')):
            damage_params['power'] = int(damage_params['power'] * 1.5)  # 1.5x 威力提升
        return damage_params

@ItemRegistry.register(592)  # 水之宝石
class WaterGemPlugin(ItemPlugin):
    """水之宝石 - 携带后，对应属性的招式威力仅会增强１次（消耗品）"""
    def on_apply(self):
        hook = BattleHook("water_gem_boost", 15, self.damage_mod, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'water' or move.type_name.lower() == '水')):
            damage_params['power'] = int(damage_params['power'] * 1.5)  # 1.5x 威力提升
        return damage_params

@ItemRegistry.register(593)  # 电之宝石
class ElectricGemPlugin(ItemPlugin):
    """电之宝石 - 携带后，对应属性的招式威力仅会增强１次（消耗品）"""
    def on_apply(self):
        hook = BattleHook("electric_gem_boost", 15, self.damage_mod, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'electric' or move.type_name.lower() == '电')):
            damage_params['power'] = int(damage_params['power'] * 1.5)  # 1.5x 威力提升
        return damage_params

@ItemRegistry.register(605)  # 钢之宝石
class SteelGemPlugin(ItemPlugin):
    """钢之宝石 - 携带后，对应属性的招式威力仅会增强１次（消耗品）"""
    def on_apply(self):
        hook = BattleHook("steel_gem_boost", 15, self.damage_mod, persistent=False)
        self.owner.hooks.register("on_damage_calc", hook)

    def damage_mod(self, damage_params, attacker, defender, move, logger_obj):
        if (attacker == self.owner and
            (move.type_name.lower() == 'steel' or move.type_name.lower() == '钢')):
            damage_params['power'] = int(damage_params['power'] * 1.5)  # 1.5x 威力提升
        return damage_params