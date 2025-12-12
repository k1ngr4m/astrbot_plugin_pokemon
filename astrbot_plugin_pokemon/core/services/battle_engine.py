import random
from typing import List, Tuple, Dict, Any, Optional, Protocol
from dataclasses import dataclass

from astrbot.api import logger
from ..models.adventure_models import BattleContext, BattleMoveInfo
from .stat_modifier_service import StatModifierService, StatID


class BattleLogger(Protocol):
    def log(self, message: str):
        ...


class ListBattleLogger:
    def __init__(self, log_details: bool = False):
        self.logs = []
        self._log_details = log_details

    def log(self, message: str):
        self.logs.append(message)

    def should_log_details(self) -> bool:
        return self._log_details


class NoOpBattleLogger:
    def log(self, message: str):
        pass

    def should_log_details(self) -> bool:
        return False


@dataclass
class BattleState:
    """
    Holds the mutable state of a pokemon during a battle.
    This allows us to simulate battles without modifying the original pokemon objects,
    or to track real battle state separately.
    """
    context: BattleContext
    current_hp: int
    current_pps: List[int]
    stat_levels: Optional[Dict[int, int]] = None  # 状态等级字典，key为stat_id，value为等级变化

    @classmethod
    def from_context(cls, context: BattleContext) -> 'BattleState':
        return cls(
            context=context,
            current_hp=context.current_hp,
            current_pps=[m.current_pp for m in context.moves],
            stat_levels={}  # 初始化为空字典，表示所有状态等级为0
        )


class BattleLoggerWithDetailOption(Protocol):
    def log(self, message: str):
        ...
    def should_log_details(self) -> bool:
        """返回是否应该记录详细信息（如评分计算详情）"""
        ...


class BattleLogic:
    # --- 常量 ---
    TRAINER_ENCOUNTER_RATE = 0.3
    CRIT_RATE = 0.0625
    STRUGGLE_MOVE_ID = -1

    # 中文类型名到英文类型名的映射
    TYPE_NAME_MAPPING = {
        '一般': 'normal', 'normal': 'normal',
        '火': 'fire', 'fire': 'fire',
        '水': 'water', 'water': 'water',
        '电': 'electric', 'electric': 'electric',
        '草': 'grass', 'grass': 'grass',
        '冰': 'ice', 'ice': 'ice',
        '格斗': 'fighting', 'fighting': 'fighting',
        '毒': 'poison', 'poison': 'poison',
        '地面': 'ground', 'ground': 'ground',
        '飞行': 'flying', 'flying': 'flying',
        '超能力': 'psychic', 'psychic': 'psychic',
        '虫': 'bug', 'bug': 'bug',
        '岩石': 'rock', 'rock': 'rock',
        '幽灵': 'ghost', 'ghost': 'ghost',
        '龙': 'dragon', 'dragon': 'dragon',
        '恶': 'dark', 'dark': 'dark',
        '钢': 'steel', 'steel': 'steel',
        '妖精': 'fairy', 'fairy': 'fairy'
    }

    TYPE_CHART = {
        'normal': {'rock': 0.5, 'ghost': 0.0, 'steel': 0.5},
        'fire': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 2.0, 'bug': 2.0, 'rock': 0.5, 'dragon': 0.5,
                 'steel': 2.0},
        'water': {'fire': 2.0, 'water': 0.5, 'grass': 0.5, 'ground': 2.0, 'rock': 2.0, 'dragon': 0.5},
        'electric': {'water': 2.0, 'electric': 0.5, 'grass': 0.5, 'ground': 0.0, 'flying': 2.0, 'dragon': 0.5},
        'grass': {'fire': 0.5, 'water': 2.0, 'grass': 0.5, 'poison': 0.5, 'ground': 2.0, 'flying': 0.5, 'bug': 0.5,
                  'rock': 2.0, 'dragon': 0.5, 'steel': 0.5},
        'ice': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 0.5, 'ground': 2.0, 'flying': 2.0, 'dragon': 2.0,
                'steel': 0.5},
        'fighting': {'normal': 2.0, 'ice': 2.0, 'poison': 0.5, 'flying': 0.5, 'psychic': 0.5, 'bug': 0.5, 'rock': 2.0,
                     'ghost': 0.0, 'dark': 2.0, 'steel': 2.0, 'fairy': 0.5},
        'poison': {'grass': 2.0, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'ghost': 0.5, 'steel': 0.0, 'fairy': 2.0},
        'ground': {'fire': 2.0, 'electric': 2.0, 'grass': 0.5, 'poison': 2.0, 'flying': 0.0, 'bug': 0.5, 'rock': 2.0,
                   'steel': 2.0},
        'flying': {'electric': 0.5, 'grass': 2.0, 'fighting': 2.0, 'bug': 2.0, 'rock': 0.5, 'steel': 0.5},
        'psychic': {'fighting': 2.0, 'poison': 2.0, 'psychic': 0.5, 'dark': 0.0, 'steel': 0.5},
        'bug': {'fire': 0.5, 'grass': 2.0, 'fighting': 0.5, 'poison': 0.5, 'flying': 0.5, 'psychic': 2.0, 'ghost': 0.5,
                'dark': 2.0, 'steel': 0.5, 'fairy': 0.5},
        'rock': {'fire': 2.0, 'ice': 2.0, 'fighting': 0.5, 'ground': 0.5, 'flying': 2.0, 'bug': 2.0, 'steel': 0.5},
        'ghost': {'normal': 0.0, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5},
        'dragon': {'dragon': 2.0, 'steel': 0.5, 'fairy': 0.0},
        'dark': {'fighting': 0.5, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5, 'fairy': 0.5},
        'steel': {'fire': 0.5, 'water': 0.5, 'electric': 0.5, 'ice': 2.0, 'rock': 2.0, 'steel': 0.5, 'fairy': 2.0},
        'fairy': {'fighting': 2.0, 'poison': 0.5, 'bug': 0.5, 'dragon': 2.0, 'dark': 2.0, 'steel': 0.5}
    }

    def __init__(self, move_repo=None):
        self.stat_modifier_service = StatModifierService()
        self.move_repo = move_repo  # move_repo，用于获取技能状态变化
        # 兼容性处理：如果传递的是 move_service（有 move_repo 属性），则使用它
        if move_repo and hasattr(move_repo, 'move_repo'):
            self.move_service = move_repo
        else:
            self.move_service = None
        self._struggle_move = self._create_struggle_move()

    def _create_struggle_move(self) -> BattleMoveInfo:
        return BattleMoveInfo(
            power=40, accuracy=100.0, type_name='normal', damage_class_id=2,
            priority=0, type_effectiveness=1.0, stab_bonus=1.0,
            max_pp=10, current_pp=10, move_id=self.STRUGGLE_MOVE_ID, move_name="挣扎"
        )

    def get_struggle_move(self) -> BattleMoveInfo:
        return self._struggle_move

    def _get_modified_stats(self, battle_state: BattleState):
        """获取修改后的宝可梦状态"""
        # 如果没有状态等级，则直接返回原始状态
        if not battle_state.stat_levels:
            return battle_state.context.pokemon.stats

        # 使用stat modifier service来计算修改后的状态
        modified_stats, _ = self.stat_modifier_service.apply_stat_changes(
            battle_state.context.pokemon.stats,
            [],  # 空的变化列表，因为我们只是应用现有的等级
            battle_state.stat_levels
        )
        return modified_stats

    def _get_english_type_name(self, type_name: str) -> str:
        """将类型名称转换为英文"""
        return self.TYPE_NAME_MAPPING.get(type_name, type_name.lower())

    def calculate_type_effectiveness(self, attacker_types: List[str], defender_types: List[str]) -> float:
        effectiveness = 1.0
        for atk_type in attacker_types:
            # 将攻击方类型转换为英文
            atk_english = self._get_english_type_name(atk_type)
            atk_dict = self.TYPE_CHART.get(atk_english)
            if not atk_dict: continue
            for def_type in defender_types:
                # 将防御方类型转换为英文
                def_english = self._get_english_type_name(def_type)
                effectiveness *= atk_dict.get(def_english, 1.0)
        return effectiveness

    def _get_atk_def_ratio(self, attacker_state: BattleState, defender_state: BattleState, move: BattleMoveInfo) -> float:
        # 使用修改后的状态值
        attacker_stats = self._get_modified_stats(attacker_state)
        defender_stats = self._get_modified_stats(defender_state)

        atk_stat = attacker_stats.attack if move.damage_class_id == 2 else attacker_stats.sp_attack
        def_stat = defender_stats.defense if move.damage_class_id == 2 else defender_stats.sp_defense
        return atk_stat / max(1, def_stat)

    def _execute_self_destruct_move(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo, logger_obj: BattleLogger) -> bool:
        """执行自爆技能的特殊逻辑"""
        logger_obj.log(f"{attacker.context.pokemon.name} 使用了自爆！\n\n")

        # Calculate damage to defender (normal damage calculation)
        dmg, effects = self._calculate_damage_core(attacker, defender, move)
        defender.current_hp -= dmg

        # Log the damage
        logger_obj.log(f"造成 {dmg} 点伤害。\n\n")

        if effects["missed"]:
            logger_obj.log("没有击中目标！\n\n")
        else:
            if effects["is_crit"]:
                logger_obj.log("击中要害！\n\n")
            eff = effects["type_effectiveness"]
            if eff > 1.0:
                logger_obj.log("效果绝佳！\n\n")
            elif eff == 0.0:
                logger_obj.log("似乎没有效果！\n\n")
            elif eff < 1.0:
                logger_obj.log("效果不佳！\n\n")

            # Process special effects
            meta_effects = effects.get("meta_effects", [])
            self._log_meta_effects(attacker, defender, meta_effects, logger_obj)

        # Make the attacker faint (self-destruct effect)
        attacker.current_hp = 0
        logger_obj.log(f"{attacker.context.pokemon.name} 发生了爆炸，因此倒下了！\n\n")

        # Check if both Pokemon fainted
        if defender.current_hp <= 0:
            logger_obj.log(f"{defender.context.pokemon.name} 也倒下了！\n\n")
        else:
            logger_obj.log(f"{defender.context.pokemon.name} 还在继续战斗！\n\n")

        # Battle ends if attacker fainted
        return True

    def _calculate_self_destruct_score(self, attacker_state: BattleState, defender_state: BattleState, move: BattleMoveInfo, logger_obj: Optional[BattleLogger] = None) -> float:
        """计算自爆技能的评分"""
        # 自爆技能的评分基于：能否击败对手 + 自身当前血量状况
        hypothetical_damage, _ = self._calculate_damage_core(attacker_state, defender_state, move, simulate=True)

        # 如果自爆能击败对手，大幅加分
        base_score = self._calculate_unified_move_score(attacker_state, defender_state, move, logger_obj)
        if hypothetical_damage >= defender_state.current_hp:
            base_score += 500.0  # 非常高的奖励，因为可以同归于尽
        else:
            # 如果不能击败对手，但可以造成大量伤害，也给予一定奖励
            damage_ratio = hypothetical_damage / defender_state.context.pokemon.stats.hp
            base_score += damage_ratio * 100.0

        # 如果自身血量很低，使用自爆的倾向应该更高（反正快死了）
        attacker_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
        if attacker_hp_ratio < 0.3:
            base_score += (1.0 - attacker_hp_ratio) * 200.0  # 血量越低，自爆倾向越高

        return base_score

    def _calculate_damage_core(self, attacker_state: BattleState, defender_state: BattleState, move: BattleMoveInfo, simulate: bool = False) -> Tuple[int, Dict[str, Any]]:
        # For OHKO moves, skip the regular accuracy check since they have special rules
        if move.meta_category_id != 9:  # not OHKO
            if random.random() * 100 > move.accuracy:
                return 0, {"missed": True, "type_effectiveness": 1.0, "is_crit": False, "meta_effects": []}

        attacker_stats = self._get_modified_stats(attacker_state)
        defender_stats = self._get_modified_stats(defender_state)

        atk_stat = attacker_stats.attack if move.damage_class_id == 2 else attacker_stats.sp_attack
        def_stat = defender_stats.defense if move.damage_class_id == 2 else defender_stats.sp_defense
        level = attacker_state.context.pokemon.level

        base_damage = ((2 * level / 5 + 2) * move.power * atk_stat / max(1, def_stat)) / 50 + 2

        is_crit = random.random() < self.CRIT_RATE
        crit_multiplier = 1.5 if is_crit else 1.0
        random_multiplier = random.uniform(0.85, 1.0)

        eff = self.calculate_type_effectiveness([move.type_name], defender_state.context.types)
        stab = 1.5 if move.type_name in attacker_state.context.types else 1.0

        final_damage = base_damage * eff * stab * crit_multiplier * random_multiplier

        # 处理特殊meta类别的效果
        meta_effects = []

        # 根据meta_category_id处理特殊逻辑
        if move.meta_category_id == 0:  # damage: 纯粹的攻击招式（无附加效果）
            # 现有逻辑不变
            pass

        elif move.meta_category_id == 1:  # ailment: 造成异常状态 (如: 电磁波, 鬼火)
            # 1. 获取招式的状态几率
            # 注意: 如果是变化类招式(Status Move)，ailment_chance 为 0 通常代表必中(100%)
            # 但如果是攻击招式(Category 4)，0 就是 0%。这里我们处理 Category 1。
            chance = move.ailment_chance
            if chance == 0:
                chance = 100  # Category 1 默认为必中（命中判定由 accuracy 决定）

            # 2. 判断是否触发状态 (几率判定)
            # random.randint(1, 100) 生成 1~100 的整数
            if defender_state.context.pokemon.stats.hp > 0 and random.randint(1, 100) <= chance:

                # 3. 获取具体的状态 ID (关键步骤)
                ailment_id = move.meta_ailment_id

                # 4. 检查类型免疫 (关键增强)
                # 获取防御方的类型
                defender_types = [t.lower() for t in defender_state.context.types]

                # 检查是否免疫此异常状态
                is_immune = False
                if ailment_id == 1:  # paralysis (麻痹)
                    # 电系宝可梦免疫麻痹
                    if 'electric' in defender_types:
                        is_immune = True
                elif ailment_id == 5:  # poison (中毒)
                    # 毒系和钢系宝可梦免疫中毒
                    if 'poison' in defender_types or 'steel' in defender_types:
                        is_immune = True
                elif ailment_id == 4:  # burn (灼伤)
                    # 火系宝可梦免疫灼伤
                    if 'fire' in defender_types:
                        is_immune = True
                elif ailment_id == 3:  # freeze (冰冻)
                    # 冰系宝可梦免疫冰冻
                    if 'ice' in defender_types:
                        is_immune = True
                elif ailment_id == 2:  # sleep (睡眠)
                    # 没有类型免疫，但这里提供扩展点
                    pass  # 某些情况下可能有免疫，如携带特定道具

                # 如果免疫，则跳过效果
                if is_immune:
                    # 可以添加日志记录免疫情况
                    logger.info(f"[DEBUG] 防御方宝可梦免疫了异常状态: ID={ailment_id}")
                    pass
                else:
                    # 5. (可选) 将 ID 映射为代码内部使用的字符串
                    # 这种映射关系最好定义在常量文件里，而不是写死在这里
                    # 这里参考 PokeAPI 的标准 ID 映射：
                    ailment_map = {
                        1: "paralysis",  # 麻痹
                        2: "sleep",  # 睡眠
                        3: "freeze",  # 冰冻
                        4: "burn",  # 灼伤
                        5: "poison",  # 中毒
                        6: "confusion",  # 混乱
                        7: "infatuation",  # 着迷
                        8: "trap",  # 束缚
                        9: "nightmare",  # 噩梦
                        12: "torment",  # 折磨
                        13: "disable",  # 禁用
                        14: "yawn",  # 困倦
                        15: "heal block",  # 回复阻断
                        17: "no type immunity",  # 无类型免疫
                        18: "leech seed",  # 吸血
                        19: "embargo",  #  embargo
                        20: "perish song",  # 灭亡
                        21: "ingrain",  # 同化
                        24: "silence",  # 沉默
                        42: "tar shot",  # 焦油射门
                    }

                    status_effect = ailment_map.get(ailment_id, "unknown")

                    if status_effect != "unknown":
                        # 6. 添加效果
                        # 建议把 ID 也存进去，方便前端显示或后续逻辑判断
                        meta_effects.append({
                            "type": "ailment",
                            "status": status_effect,
                            "status_id": ailment_id
                        })

                        # 日志记录 (可选)
                        logger.info(f"[DEBUG] 招式触发了异常状态: ID={ailment_id} ({status_effect})")

        elif move.meta_category_id == 2:  # net-good-stats: 提升能力 (如: 剑舞, 铁壁, 高速移动)
        # 确保 attacker_state.stat_levels 已初始化
            if attacker_state.stat_levels is None:
                attacker_state.stat_levels = {}
            # 检查 move 对象中是否包含 stat_changes 数据
            # (这需要在 adventure_service.py 中确保传递了该字段)
            if hasattr(move, 'stat_changes') and move.stat_changes:
                changes_applied = False
                for change_data in move.stat_changes:
                    # 1. 解析数据 (兼容字典或对象属性)
                    # stat_id: 1=Attack, 2=Defense, etc. (取决于您的数据库定义)
                    # change: +1, +2, -1, etc.
                    stat_id = change_data.get('stat_id') if isinstance(change_data, dict) else getattr(change_data, 'stat_id', None)
                    change_amount = change_data.get('change') if isinstance(change_data, dict) else getattr(change_data, 'change', 0)

                    if stat_id is None or change_amount == 0:
                        continue
                    # 2. 获取当前能力等级 (默认为 0)
                    current_stage = attacker_state.stat_levels.get(stat_id, 0)
                    # 3. 计算新等级 (限制在 -6 到 +6 之间)
                    # 如果是提升能力，不能超过 6；如果是降低，不能低于 -6 (虽然 Category 2 通常是提升)
                    new_stage = current_stage + change_amount
                    new_stage = max(-6, min(6, new_stage))
                    # 4. 如果等级发生了实际变化，更新状态并记录
                    if new_stage != current_stage:
                        if not simulate:
                            attacker_state.stat_levels[stat_id] = new_stage
                        changes_applied = True
                        # 记录具体的提升效果
                        # 建议有一个 stat_id 到 名称 的映射工具
                        stat_names = {
                            1: "hp", 2: "attack", 3: "defense",
                            4: "special-attack", 5: "special-defense",
                            6: "speed", 7: "accuracy", 8: "evasion"
                        }
                        stat_name = stat_names.get(stat_id, f"stat_{stat_id}")
                        meta_effects.append({
                            "type": "stat_raise",
                            "stat": stat_name,  # 用于前端显示名称
                            "stat_id": stat_id,  # 用于逻辑判断
                            "change": new_stage - current_stage,  # 实际变化量 (比如虽然+2，但只剩+1空间)
                            "current_stage": new_stage
                        })
                if not changes_applied:
                    # 如果所有能力都已经满级 (+6)，可以记录一个“能力无法再提升”的效果
                    meta_effects.append({"type": "message", "message": "能力没有变化"})
            else:
                # Fallback: 如果数据库缺失数据，可以用日志警告
                # logger.warning(f"Move {move.name} (ID: {move.move_id}) corresponds to Category 2 but has no stat_changes defined.")
                pass

        elif move.meta_category_id == 3:  # heal: 回复
            # 根据 move.healing 字段计算回复量
            # healing 为比例值（如0.5表示回复最大HP的50%，-0.25表示消耗最大HP的25%）
            heal_ratio = move.healing
            max_hp = attacker_stats.hp
            heal_amount = int(max_hp * heal_ratio)

            if heal_amount > 0:  # 正数为回复HP
                # 只记录效果，让 _execute_action 通过 meta_effects 来处理
                meta_effects.append({"type": "heal", "amount": heal_amount, "heal_ratio": heal_ratio})
            elif heal_amount < 0:  # 负数为消耗HP（如替身、诅咒等）
                # 记录消耗效果
                meta_effects.append({"type": "damage", "amount": -heal_amount, "damage_ratio": -heal_ratio})

        elif move.meta_category_id == 4:  # damage+ailment: 攻击并造成异常状态
            # 先计算基础伤害
            final_damage = base_damage * eff * stab * crit_multiplier * random_multiplier
            # 在造成伤害后，如果目标还存活，尝试施加异常状态
            if defender_state.current_hp > 0 and defender_state.current_hp - final_damage > 0:
                # 使用数据库中的实际几率和异常状态ID
                chance = move.ailment_chance
                ailment_id = move.meta_ailment_id

                # 检查是否命中 (几率判定)
                if chance > 0 and random.randint(1, 100) <= chance:
                    # 检查类型免疫 (关键增强)
                    # 获取防御方的类型
                    defender_types = [t.lower() for t in defender_state.context.types]

                    # 检查是否免疫此异常状态
                    is_immune = False
                    if ailment_id == 1:  # paralysis (麻痹)
                        # 电系宝可梦免疫麻痹
                        if 'electric' in defender_types:
                            is_immune = True
                    elif ailment_id == 5:  # poison (中毒)
                        # 毒系和钢系宝可梦免疫中毒
                        if 'poison' in defender_types or 'steel' in defender_types:
                            is_immune = True
                    elif ailment_id == 4:  # burn (灼伤)
                        # 火系宝可梦免疫灼伤
                        if 'fire' in defender_types:
                            is_immune = True
                    elif ailment_id == 3:  # freeze (冰冻)
                        # 冰系宝可梦免疫冰冻
                        if 'ice' in defender_types:
                            is_immune = True

                    # 如果不免疫，则应用异常状态
                    if not is_immune:
                        # 将 ID 映射为代码内部使用的字符串
                        ailment_map = {
                            1: "paralysis",  # 麻痹
                            2: "sleep",  # 睡眠
                            3: "freeze",  # 冰冻
                            4: "burn",  # 灼伤
                            5: "poison",  # 中毒
                            6: "confusion",  # 混乱
                            7: "infatuation",  # 着迷
                            8: "trap",  # 束缚
                            9: "nightmare",  # 噩梦
                            12: "torment",  # 折磨
                            13: "disable",  # 禁用
                            14: "yawn",  # 困倦
                            15: "heal block",  # 回复阻断
                            17: "no type immunity",  # 无类型免疫
                            18: "leech seed",  # 吸血
                            19: "embargo",  #  embargo
                            20: "perish song",  # 灭亡
                            21: "ingrain",  # 同化
                            24: "silence",  # 沉默
                            42: "tar shot",  # 焦油射门
                        }

                        status_effect = ailment_map.get(ailment_id, "unknown")
                        if status_effect != "unknown":
                            meta_effects.append({
                                "type": "ailment",
                                "status": status_effect,
                                "status_id": ailment_id
                            })
        elif move.meta_category_id == 5:  # swagger: 虚张声势类 (如: Swagger, Flatter)
            # 目标是对手 (Defender)

            # --- 1. 处理异常状态 (通常是混乱) ---
            # 获取几率 (通常是 0 或 100，代表必中)
            chance = move.ailment_chance
            if chance == 0:
                chance = 100

            applied_ailment = False

            # 判定几率
            if defender_state.current_hp > 0 and random.randint(1, 100) <= chance:
                # 获取状态 ID (混乱 ID 通常是 6)
                ailment_id = move.meta_ailment_id

                # 简单映射 (建议封装)
                ailment_map = {6: "confusion", 1: "paralysis"}  # 这里主要针对混乱
                status_name = ailment_map.get(ailment_id, "confusion")

                # 免疫判断 (例如：已经混乱了，或者有神秘面纱)
                # 这里做个简单检查：如果已经有该状态则失败
                # (注：这里假设 battle_state 里有个地方存混乱状态，通常是 volatile_status)
                # 简单起见，我们先假设它能中

                meta_effects.append({
                    "type": "ailment",
                    "status": status_name,
                    "status_id": ailment_id,
                    "target": "defender"
                })
                applied_ailment = True

            # --- 2. 处理能力提升 (Stat Raise) ---
            # 注意：在第7世代后，如果混乱未生效(例如免疫)，能力提升也不会生效。
            # 这里我们做一个简单判定：只有尝试施加了状态(无论是否被免疫)，才去加状态，或者根据游戏世代设定独立处理。
            # 考虑到通用性，我们先独立处理，或者仅当命中时处理。

            if applied_ailment:  # 或者直接无条件执行，取决于你想模拟哪个世代
                if defender_state.stat_levels is None:
                    defender_state.stat_levels = {}

                # 动态读取提升的能力 (Attack vs Special Attack)
                if hasattr(move, 'stat_changes') and move.stat_changes:
                    for change_data in move.stat_changes:
                        # 解析数据
                        stat_id = change_data.get('stat_id') if isinstance(change_data,
                                                                           dict) else getattr(
                            change_data, 'stat_id', None)
                        change_amount = change_data.get('change') if isinstance(change_data,
                                                                                dict) else getattr(
                            change_data, 'change', 0)

                        if stat_id is not None and change_amount != 0:
                            current_stage = defender_state.stat_levels.get(stat_id, 0)

                            # 计算新等级 (上限 +6)
                            new_stage = min(6, current_stage + change_amount)

                            if new_stage != current_stage:
                                defender_state.stat_levels[stat_id] = new_stage

                                # 记录效果
                                # 映射 stat_id 到名称 (建议提取为公共常量)
                                stat_names = {2: "attack", 4: "special-attack"}
                                stat_name = stat_names.get(stat_id, "stat")

                                meta_effects.append({
                                    "type": "stat_raise",
                                    "stat": stat_name,
                                    "change": change_amount,
                                    "target": "defender"  # 标记是给对手加的
                                })

        elif move.meta_category_id == 6:  # damage+lower: 攻击并降低能力
            # 先计算基础伤害
            final_damage = base_damage * eff * stab * crit_multiplier * random_multiplier
            # 然后尝试降低目标能力
            if defender_state.stat_levels is None:
                defender_state.stat_levels = {}

            # 使用数据库中的实际几率
            actual_chance = int(move.stat_chance * 100) if move.stat_chance is not None else 0
            if random.randint(1, 100) <= actual_chance:
                # 使用实际的stat_changes数据，而不是硬编码
                if hasattr(move, 'stat_changes') and move.stat_changes:
                    for change_data in move.stat_changes:
                        stat_id = change_data.get('stat_id') if isinstance(change_data, dict) else getattr(change_data, 'stat_id', None)
                        change_amount = change_data.get('change') if isinstance(change_data, dict) else getattr(change_data, 'change', 0)

                        if stat_id is not None and change_amount != 0:
                            current_stage = defender_state.stat_levels.get(stat_id, 0)
                            # 计算新等级，限制在-6到+6之间（这里是降低，所以要确保不低于-6）
                            new_stage = current_stage + change_amount  # change_amount should be negative for lowering
                            new_stage = max(-6, min(6, new_stage))

                            # 如果实际变化量与原值不同（比如已经到-6了），记录实际变化
                            actual_change = new_stage - current_stage
                            if actual_change != 0:
                                # Only update stat levels if not simulating
                                if not simulate:
                                    defender_state.stat_levels[stat_id] = new_stage
                                # 映射stat_id到名称
                                stat_names = {
                                    1: "hp", 2: "attack", 3: "defense",
                                    4: "special-attack", 5: "special-defense",
                                    6: "speed", 7: "accuracy", 8: "evasion"
                                }
                                stat_name = stat_names.get(stat_id, f"stat_{stat_id}")
                                meta_effects.append({
                                    "type": "stat_lower",
                                    "stat": stat_name,
                                    "stat_id": stat_id,
                                    "change": actual_change,  # 实际变化量
                                    "current_stage": new_stage
                                })
        elif move.meta_category_id == 7:  # damage+raise: 攻击并提升能力
            # 先计算基础伤害
            final_damage = base_damage * eff * stab * crit_multiplier * random_multiplier
            # 然后提升自身能力
            if attacker_state.stat_levels is None:
                attacker_state.stat_levels = {}

            # 使用数据库中的实际几率
            actual_chance = int(move.stat_chance * 100) if move.stat_chance is not None else 0
            if random.randint(1, 100) <= actual_chance:
                # 使用实际的stat_changes数据，而不是硬编码
                if hasattr(move, 'stat_changes') and move.stat_changes:
                    for change_data in move.stat_changes:
                        stat_id = change_data.get('stat_id') if isinstance(change_data, dict) else getattr(change_data, 'stat_id', None)
                        change_amount = change_data.get('change') if isinstance(change_data, dict) else getattr(change_data, 'change', 0)

                        if stat_id is not None and change_amount != 0:
                            current_stage = attacker_state.stat_levels.get(stat_id, 0)
                            # 计算新等级，限制在-6到+6之间（这里是提升，所以要确保不超过+6）
                            new_stage = current_stage + change_amount  # change_amount should be positive for raising
                            new_stage = max(-6, min(6, new_stage))

                            # 如果实际变化量与原值不同（比如已经到+6了），记录实际变化
                            actual_change = new_stage - current_stage
                            if actual_change != 0:
                                # Only update stat levels if not simulating
                                if not simulate:
                                    attacker_state.stat_levels[stat_id] = new_stage
                                # 映射stat_id到名称
                                stat_names = {
                                    1: "hp", 2: "attack", 3: "defense",
                                    4: "special-attack", 5: "special-defense",
                                    6: "speed", 7: "accuracy", 8: "evasion"
                                }
                                stat_name = stat_names.get(stat_id, f"stat_{stat_id}")
                                meta_effects.append({
                                    "type": "stat_raise",
                                    "stat": stat_name,
                                    "stat_id": stat_id,
                                    "change": actual_change,  # 实际变化量
                                    "current_stage": new_stage
                                })


        elif move.meta_category_id == 8:  # damage+heal: 攻击并回复
            # 先计算基础伤害
            final_damage = base_damage * eff * stab * crit_multiplier * random_multiplier
            # drain字段通常表示回复比例的百分比值（如50, 75, 100）
            raw_drain = getattr(move, 'drain', 0)
            drain_percent = raw_drain if raw_drain and raw_drain > 0 else 50
            # drain_percent = move.drain if hasattr(move, 'drain') and move.drain is not None else 50  # 默认50%如果未设置
            drain_ratio = drain_percent / 100.0

            # 将部分伤害转换为回复
            heal_amount = int(final_damage * drain_ratio)
            # Only update HP if not simulating (this was a mistake - healing should be handled in _execute_action)
            # Remove direct HP modification, healing will be handled in _execute_action based on meta_effects
            meta_effects.append({
                "type": "heal",
                "amount": heal_amount,
                "heal_ratio": drain_ratio,
                "from_drain": True,  # 标记是通过吸收伤害回复，便于前端区分显示
                "damage_dealt": int(final_damage)
            })
        elif move.meta_category_id == 9:  # ohko: 一击必杀
            # 一击必杀技能，遵循Gen 3+标准规则
            attacker_lv = attacker_state.context.pokemon.level
            defender_lv = defender_state.context.pokemon.level

            # 检查等级检测：如果攻击者等级 < 防御者等级，招式必定失败
            if attacker_lv < defender_lv:
                # 招式失败，不造成伤害
                final_damage = 0
                meta_effects.append({"type": "ohko", "success": False, "reason": "等级不足"})
            else:
                # 计算特殊命中率：30 + (攻击者等级 - 防御者等级)
                base_accuracy = 30
                accuracy_bonus = attacker_lv - defender_lv
                calculated_accuracy = base_accuracy + accuracy_bonus

                # 检查基础命中判定
                if random.randint(1, 100) <= calculated_accuracy:
                    # 检查属性有效性（即使是一击必杀也受属性克制影响）
                    eff = self.calculate_type_effectiveness([move.type_name], defender_state.context.types)

                    # 如果效果为0（免疫），招式失败
                    if eff == 0.0:
                        final_damage = 0
                        meta_effects.append({"type": "ohko", "success": False, "reason": "属性免疫"})
                    else:
                        # 招式成功，造成目标当前HP的伤害（直接秒杀）
                        final_damage = defender_state.current_hp
                        meta_effects.append({
                            "type": "ohko",
                            "success": True,
                            "damage": defender_state.current_hp,
                            "accuracy": calculated_accuracy
                        })
                else:
                    # 命中失败
                    final_damage = 0
                    meta_effects.append({
                        "type": "ohko",
                        "success": False,
                        "reason": "未命中",
                        "calculated_accuracy": calculated_accuracy
                    })
        elif move.meta_category_id == 10:  # whole-field-effect: 全场效果
            # 全场效果，如天气变化（此处简化处理）
            meta_effects.append({"type": "field_effect", "effect": "weather", "duration": 5})
        elif move.meta_category_id == 11:  # field-effect: 场地效果
            # 场地效果，如钉子、光墙（此处简化处理）
            meta_effects.append({"type": "terrain", "effect": "reflect", "duration": 5})
        elif move.meta_category_id == 12:  # force-switch: 强制替换
            # 标记强制替换（简化处理，实际需要替换逻辑）
            meta_effects.append({"type": "force_switch", "target": "defender"})
        elif move.meta_category_id == 13:  # unique: 特殊/独特
            # 独特效果（根据具体技能处理）
            meta_effects.append({"type": "unique", "effect": "special"})

        return int(final_damage), {
            "missed": False,
            "type_effectiveness": eff,
            "is_crit": is_crit,
            "stab_bonus": stab,
            "meta_effects": meta_effects
        }

    def _is_user_first(self, user_state: BattleState, wild_state: BattleState,
                       u_move: BattleMoveInfo, w_move: BattleMoveInfo) -> bool:
        u_prio, w_prio = u_move.priority, w_move.priority
        if u_prio != w_prio:
            return u_prio > w_prio

        u_spd = self._get_modified_stats(user_state).speed
        w_spd = self._get_modified_stats(wild_state).speed
        if u_spd != w_spd:
            return u_spd > w_spd

        return random.random() < 0.5

    def process_turn(self, user_state: BattleState, wild_state: BattleState,
                     logger_obj: BattleLogger) -> bool:
        """
        Process a single turn. Returns True if the battle ended (one side fainted).
        """
        u_move = self.get_best_move(user_state, wild_state, logger_obj)
        w_move = self.get_best_move(wild_state, user_state, logger_obj)

        user_first = self._is_user_first(user_state, wild_state, u_move, w_move)

        first_unit = (user_state, wild_state, u_move) if user_first else (wild_state, user_state, w_move)
        second_unit = (wild_state, user_state, w_move) if user_first else (user_state, wild_state, u_move)

        # First action
        if self._execute_action(first_unit[0], first_unit[1], first_unit[2], logger_obj):
            return True # Battle ended
        
        # Second action
        if self._execute_action(second_unit[0], second_unit[1], second_unit[2], logger_obj):
            return True # Battle ended
            
        return False

    def _log_meta_effects(self, attacker, defender, meta_effects, logger_obj):
        """记录特殊meta效果的日志"""
        for meta_effect in meta_effects:
            effect_type = meta_effect.get("type", "")
            if effect_type == "ailment":
                status = meta_effect.get("status", "unknown")
                logger_obj.log(f"{defender.context.pokemon.name}陷入{status}状态！\n\n")
            elif effect_type == "stat_raise":
                stat = meta_effect.get("stat", "unknown")
                change = meta_effect.get("change", 0)
                logger_obj.log(f"{attacker.context.pokemon.name}的{stat}提升了！\n\n")
            elif effect_type == "stat_lower":
                stat = meta_effect.get("stat", "unknown")
                logger_obj.log(f"{defender.context.pokemon.name}的{stat}降低了！\n\n")
            elif effect_type == "heal":
                amount = meta_effect.get("amount", 0)
                from_drain = meta_effect.get("from_drain", False)
                if from_drain:
                    damage_dealt = meta_effect.get("damage_dealt", 0)
                    logger_obj.log(f"{attacker.context.pokemon.name}通过攻击吸收了{amount}点HP！\n\n")
                else:
                    logger_obj.log(f"{attacker.context.pokemon.name}回复了{amount}点HP！\n\n")
            elif effect_type == "damage":
                amount = meta_effect.get("amount", 0)
                logger_obj.log(f"{attacker.context.pokemon.name}损失了{amount}点HP！\n\n")
            elif effect_type == "swagger":
                logger_obj.log(f"{defender.context.pokemon.name}陷入混乱！攻击力提升！\n\n")
            elif effect_type == "damage_heal":
                heal = meta_effect.get("heal", 0)
                logger_obj.log(f"{attacker.context.pokemon.name}通过攻击回复了{heal}点HP！\n\n")
            elif effect_type == "ohko":
                success = meta_effect.get("success", False)
                reason = meta_effect.get("reason", "")
                if success:
                    logger_obj.log(f"一击必杀！直接击败了对手！\n\n")
                else:
                    if reason == "等级不足":
                        logger_obj.log(f"一击必杀失败！等级低于对手！\n\n")
                    elif reason == "属性免疫":
                        logger_obj.log(f"一击必杀失败！对手属性免疫！\n\n")
                    elif reason == "未命中":
                        calculated_accuracy = meta_effect.get("calculated_accuracy", 0)
                        logger_obj.log(f"一击必杀失败！未命中（计算命中率: {calculated_accuracy}%）\n\n")
                    else:
                        logger_obj.log(f"一击必杀失败！\n\n")
            elif effect_type == "field_effect":
                effect = meta_effect.get("effect", "unknown")
                logger_obj.log(f"全场{effect}效果开始！\n\n")
            elif effect_type == "terrain":
                effect = meta_effect.get("effect", "unknown")
                logger_obj.log(f"场地{effect}效果开始！\n\n")
            elif effect_type == "force_switch":
                target = meta_effect.get("target", "unknown")
                logger_obj.log(f"强制替换{target}的宝可梦！\n\n")
            elif effect_type == "unique":
                logger_obj.log(f"特殊效果触发！\n\n")

    def _execute_action(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                        logger_obj: BattleLogger) -> bool:
        """
        执行单个动作。如果防御方宝可梦倒下则返回 True。
        """
        is_struggle = (move.move_id == self.STRUGGLE_MOVE_ID)

        # 1. 消耗 PP
        if not is_struggle:
            try:
                # 尝试找到当前技能在上下文中的位置以扣除PP
                idx = attacker.context.moves.index(move)
                if attacker.current_pps[idx] > 0:
                    attacker.current_pps[idx] -= 1
            except ValueError:
                pass

                # 2. 特殊技能拦截 (自爆)
        if move.move_id == 120:
            return self._execute_self_destruct_move(attacker, defender, move, logger_obj)

        # 准备日志显示用的 PP 信息
        try:
            current_pp = attacker.current_pps[attacker.context.moves.index(move)]
        except ValueError:
            current_pp = move.current_pp
        pp_info = f" (PP: {current_pp}/{move.max_pp})"

        # 3. 执行技能核心逻辑 (计算伤害 + 获取效果)
        effects = {}
        if move.power == 0:
            logger_obj.log(f"{attacker.context.pokemon.name} 使用了 {move.move_name}{pp_info}！\n\n")
            _, effects = self._calculate_damage_core(attacker, defender, move)
        else:
            dmg, effects = self._calculate_damage_core(attacker, defender, move)
            defender.current_hp -= dmg

            desc = f"{attacker.context.pokemon.name} 使用了 {move.move_name}{pp_info}！\n\n"
            if is_struggle:
                desc = f"{attacker.context.pokemon.name} 使用了挣扎！（PP耗尽）\n\n"

            logger_obj.log(f"{desc} 造成 {dmg} 点伤害。\n\n")

        # 4. 处理通用结果 (命中/未命中/暴击/效果拔群)
        if effects.get("missed"):
            logger_obj.log("没有击中目标！\n\n")
        else:
            # 仅攻击技能需要显示暴击/属性克制 (Power > 0 时 effects 里才有这些key，或者 calculate_damage_core 统一返回默认值)
            if move.power > 0:
                if effects.get("is_crit"): logger_obj.log("击中要害！\n\n")
                eff = effects.get("type_effectiveness", 1.0)
                if eff > 1.0:
                    logger_obj.log("效果绝佳！\n\n")
                elif eff == 0.0:
                    logger_obj.log("似乎没有效果！\n\n")
                elif eff < 1.0:
                    logger_obj.log("效果不佳！\n\n")

            # 5. 统一处理 Meta Effects (日志 + HP变更)
            meta_effects = effects.get("meta_effects", [])

            # (A) 先记录日志 (调用 helper 函数)
            self._log_meta_effects(attacker, defender, meta_effects, logger_obj)

            # (B) 后应用数值变更 (吸血/反伤) -> 【合并了原本重复的代码】
            for meta_effect in meta_effects:
                effect_type = meta_effect.get("type", "")

                if effect_type == "heal":
                    heal_amount = meta_effect.get("amount", 0)
                    attacker.current_hp = min(attacker.context.pokemon.stats.hp, attacker.current_hp + heal_amount)
                    attacker.current_hp = max(0, attacker.current_hp)

                elif effect_type == "damage" and meta_effect.get("damage_ratio", 0) != 0:
                    damage_amount = meta_effect.get("amount", 0)
                    attacker.current_hp = max(0, attacker.current_hp - damage_amount)

        # 6. 处理非 Meta Category 定义的额外 Stat Changes
        # (例如某些普通攻击带有不在 Meta Category 2/6/7 定义中的特殊能力变化)
        if move.move_id > 0 and move.stat_changes and move.meta_category_id not in [2, 6, 7]:
            self._apply_residual_stat_changes(attacker, defender, move, logger_obj)

        # 7. 挣扎反伤
        if is_struggle:
            recoil = max(1, attacker.context.pokemon.stats.hp // 4)
            attacker.current_hp -= recoil
            logger_obj.log(f"{attacker.context.pokemon.name} 因挣扎受到 {recoil} 点反作用伤害！\n\n")
            if attacker.current_hp <= 0:
                logger_obj.log(f"{attacker.context.pokemon.name} 倒下了！\n\n")
                return True

                # 8. 判定胜负
        if defender.current_hp <= 0:
            logger_obj.log(f"{defender.context.pokemon.name} 倒下了！\n\n")
            return True

        return False

    def _apply_residual_stat_changes(self, attacker, defender, move, logger_obj):
        """处理不在主要 Meta Category 中的剩余属性变化"""
        stat_changes = move.stat_changes
        target_id = move.target_id

        # 确定目标
        target_unit = None
        # 2: Opponent, 8: All Opponents... (简化判断)
        if target_id in [2, 8, 10, 11, 14]:
            target_unit = defender
        elif target_id in [3, 4, 5, 7, 13, 15]:  # User
            target_unit = attacker
        else:
            # 智能判断：负面给对手，正面给自己
            has_positive = any(c['change'] > 0 for c in stat_changes)
            target_unit = attacker if has_positive else defender

        # 应用变化
        if target_unit:
            target_unit.stat_levels = target_unit.stat_levels or {}
            _, new_levels = self.stat_modifier_service.apply_stat_changes(
                target_unit.context.pokemon.stats, stat_changes, target_unit.stat_levels)
            target_unit.stat_levels = new_levels

            # 记录日志 (这里依然需要手动记录，因为 StatMod Service 只返回结果)
            for change in stat_changes:
                if change['change'] != 0:
                    stat_name = self._get_stat_name_by_id(change['stat_id'])
                    action = "提升" if change['change'] > 0 else "降低"
                    logger_obj.log(f"{target_unit.context.pokemon.name}的{stat_name}{action}了！\n\n")

    def _get_stat_name_by_id(self, stat_id: int) -> str:
        """根据stat_id获取状态名称"""
        stat_names = {
            StatID.HP.value: "HP",
            StatID.ATTACK.value: "攻击",
            StatID.DEFENSE.value: "防御",
            StatID.SP_ATTACK.value: "特攻",
            StatID.SP_DEFENSE.value: "特防",
            StatID.SPEED.value: "速度",
            StatID.ACCURACY.value: "命中",
            StatID.EVASION.value: "闪避"
        }
        return stat_names.get(stat_id, "未知状态")

    def get_best_move(self, attacker_state: BattleState, defender_state: BattleState,
                      logger_obj: Optional[BattleLogger] = None) -> BattleMoveInfo:
        """
        智能选择最佳技能（合并逻辑版）
        """
        attacker_ctx = attacker_state.context
        current_pps = attacker_state.current_pps

        available_moves = []
        for i, move in enumerate(attacker_ctx.moves):
            if current_pps[i] > 0:
                available_moves.append(move)

        if not available_moves:
            if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                logger.info("[DEBUG] 没有可用招式，使用挣扎")
            return self.get_struggle_move()

        best_move = None
        best_score = -999.0

        # 遍历所有可用技能，使用统一评分函数
        for move in available_moves:
            current_score = self._calculate_unified_move_score(attacker_state, defender_state, move, logger_obj)

            # [新增] 随机因子：防止评分完全一致时死板
            current_score += random.uniform(0, 3)

            if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                logger.info(f"[DEBUG] 技能 {move.move_name} (Cat:{move.meta_category_id}) 评分: {current_score:.2f}")

            if current_score > best_score:
                best_score = current_score
                best_move = move

        # 检查自爆逻辑 (独立检查，或者也可以整合进 unified_score，这里保留原逻辑作为特殊覆盖)
        for move in available_moves:
            if move.move_id == 120:  # 自爆技能
                self_destruct_score = self._calculate_self_destruct_score(attacker_state, defender_state, move,
                                                                          logger_obj)
                if self_destruct_score > best_score:
                    best_score = self_destruct_score
                    best_move = move

        if best_move is None:
            return random.choice(available_moves)

        if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
            logger.info(f"[DEBUG] 最终选择: {best_move.move_name} (综合评分: {best_score:.2f})")

        return best_move

    def _calculate_unified_move_score(self, attacker_state: BattleState, defender_state: BattleState,
                                      move: BattleMoveInfo, logger_obj: Optional[BattleLogger] = None) -> float:
        """
        统一的技能评分函数，根据 meta_category_id 区分处理
        """
        score = 0.0
        cat_id = move.meta_category_id

        # 定义伤害类 meta_category_id (即使 power=0 数据有误，逻辑上也属于攻击招式)
        # 0: Damage, 4: Dmg+Ailment, 6: Dmg+Lower, 7: Dmg+Raise, 8: Dmg+Heal, 9: OHKO
        DAMAGING_CATEGORIES = [0, 4, 6, 7, 8, 9]
        is_damaging_move = cat_id in DAMAGING_CATEGORIES

        # --- 1. 基础伤害评分 (仅针对伤害类技能) ---
        expected_damage = 0
        if is_damaging_move:
            # 基础伤害计算公式
            attacker_stats = self._get_modified_stats(attacker_state)
            defender_stats = self._get_modified_stats(defender_state)

            atk_def_ratio = self._get_atk_def_ratio(attacker_state, defender_state, move)
            level = attacker_state.context.pokemon.level

            eff = self.calculate_type_effectiveness([move.type_name], defender_state.context.types)
            stab = 1.5 if move.type_name in attacker_state.context.types else 1.0

            # 估算基础伤害 (不含随机数和暴击)
            base_damage = ((2 * level / 5 + 2) * move.power * atk_def_ratio) / 50 + 2
            expected_damage = base_damage * (move.accuracy / 100.0) * eff * stab

            score += expected_damage

            # [斩杀奖励]：如果预期伤害能击败对手，给予巨额加分
            # 注意：这里使用 expected_damage 作为近似，实际扣血可能略有不同
            if expected_damage >= defender_state.current_hp:
                score += 1000.0

        # --- 2. 效果/战术评分 (根据 Category 分流) ---

        # Cat 0: 纯伤害 (已在上面计算)
        if cat_id == 0:
            pass

        # Cat 1: 纯异常状态 (如电磁波、鬼火)
        elif cat_id == 1:
            base_score = 15.0
            chance_multiplier = (move.ailment_chance / 100.0) if move.ailment_chance > 0 else 1.0
            score += base_score * chance_multiplier

            # 特殊状态加分
            if move.meta_ailment_id in [1, 4, 5]:  # 麻痹/灼伤/中毒
                score *= 1.4
            elif move.meta_ailment_id in [2, 3]:  # 睡眠/冰冻
                score *= 1.2

            # 对手血量健康时，异常状态价值更高
            hp_ratio = defender_state.current_hp / defender_state.context.pokemon.stats.hp
            if hp_ratio > 0.7:
                score *= 1.3

        # Cat 2: 纯能力提升 (如剑舞)
        elif cat_id == 2:
            # 基础分较低，避免无脑强化
            score += 5.0

            # 使用原逻辑：根据当前强化等级判断是否还需要强化
            if hasattr(move, 'stat_changes') and move.stat_changes:
                for change in move.stat_changes:
                    if change.get('change', 0) > 0:
                        stat_id = change.get('stat_id', 0)
                        current_stage = attacker_state.stat_levels.get(stat_id, 0) if attacker_state.stat_levels else 0

                        # 如果还没强化满，且等级越低，强化意愿越高
                        if current_stage < 6:
                            # 递减收益：0级时加分多，3级时加分少
                            score += 10.0 * (0.7 ** max(0, current_stage))

        # Cat 3: 回复 (如自我再生)
        elif cat_id == 3:
            current_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
            heal_ratio = move.healing

            if heal_ratio > 0:  # 回复
                score += heal_ratio * 100.0
                if current_hp_ratio < 0.5:  # 半血以下急需回复
                    score *= 2.0
            elif heal_ratio < 0:  # 自残/替身
                if current_hp_ratio > 0.8:  # 血量健康时才考虑替身
                    score += 20.0

        # Cat 4: 伤害 + 异常 (如火焰拳)
        elif cat_id == 4:
            # 已经有伤害分了，这里加额外特效分
            ailment_value = 8.0
            if move.meta_ailment_id in [1, 4, 5]:  # 强力状态
                ailment_value = 15.0
            elif move.meta_ailment_id in [2, 3]:  # 限制状态
                ailment_value = 12.0

            chance = (move.ailment_chance / 100.0) if move.ailment_chance > 0 else 1.0
            score += ailment_value * chance

        # Cat 5: 虚张声势类 (混乱但提升对手攻击)
        elif cat_id == 5:
            score += 12.0
            # 如果对手攻击已经很高，风险太大，降低评分
            opp_atk_lvl = defender_state.stat_levels.get(1, 0) if defender_state.stat_levels else 0
            if opp_atk_lvl > 1:
                score *= 0.5

        # Cat 6: 伤害 + 降低能力 (如咬碎)
        elif cat_id == 6:
            if hasattr(move, 'stat_changes'):
                for change in move.stat_changes:
                    if change.get('change', 0) < 0:
                        # 降低对手能力的价值
                        score += 5.0 + abs(change.get('change', 0)) * 2

        # Cat 7: 伤害 + 提升能力 (如原始之力)
        elif cat_id == 7:
            if hasattr(move, 'stat_changes'):
                for change in move.stat_changes:
                    if change.get('change', 0) > 0:
                        # 提升自己能力的价值
                        score += 5.0 + change.get('change', 0) * 3

        # Cat 8: 伤害 + 吸血 (如吸取拳)
        elif cat_id == 8:
            drain_ratio = getattr(move, 'drain', 50) / 100.0
            heal_value = expected_damage * drain_ratio * 0.8
            current_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
            if current_hp_ratio < 0.5:
                heal_value *= 2.0  # 残血时吸血价值极高
            score += heal_value

        # Cat 9: 一击必杀
        elif cat_id == 9:
            score += 10.0  # 基础分
            # 命中率通常只有30%，且对高等级无效，这里的期望伤害计算可能不准，给予额外修正
            if attacker_state.context.pokemon.level < defender_state.context.pokemon.level:
                score = 0  # 无效

        # Cat 10-13: 场地/全场/特殊
        elif cat_id in [10, 11, 12, 13]:
            score += 15.0  # 简单的战术加分

        # --- 3. 战术修正 (Contextual Penalties) ---
        # 这些修正主要用于“如果不造成伤害，这回合是否浪费了”的判断
        # 因此，通常只对【纯变化技能】(非伤害类) 应用严苛的惩罚

        if not is_damaging_move:
            # 3.1 斩杀线检查：如果我有其他技能可以直接打死对手，就不要用变化技能磨叽了
            defender_hp = defender_state.current_hp
            max_other_damage = 0

            # 简单估算一下其他技能的伤害 (只看最大威力的那个)
            # 为了性能，这里不做完整的 simulate，只做粗略估算
            for other_move in attacker_state.context.moves:
                if other_move.power > 0 and other_move.meta_category_id in DAMAGING_CATEGORIES:
                    # 复用上面的估算逻辑简化版
                    atk_def_ratio = self._get_atk_def_ratio(attacker_state, defender_state, other_move)
                    raw_dmg = ((
                                       2 * attacker_state.context.pokemon.level / 5 + 2) * other_move.power * atk_def_ratio) / 50 + 2
                    eff = self.calculate_type_effectiveness([other_move.type_name], defender_state.context.types)
                    if raw_dmg * eff >= defender_hp:
                        max_other_damage = raw_dmg * eff
                        break

            if max_other_damage >= defender_hp:
                score = -100.0  # 绝对不选，直接打死
                if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                    logger.info(f"[DEBUG] {move.move_name} 被惩罚: 能直接斩杀时不使用变化技")

            # 3.2 自身状态检查：如果我快死了 (HP < 40%)，别强化了，赶紧输出
            attacker_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
            if attacker_hp_ratio < 0.4 and cat_id not in [3, 8]:  # 排除回血技
                score *= 0.1

            # 3.3 对手状态检查：对手快死了，也别用变化技
            defender_hp_ratio = defender_state.current_hp / defender_state.context.pokemon.stats.hp
            if defender_hp_ratio < 0.25:
                score *= 0.1

        return score
