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
        # logger.info(f"calculate_type_effectiveness: {attacker_types} vs {defender_types} = {effectiveness}")
        return effectiveness

    def _get_atk_def_ratio(self, attacker_state: BattleState, defender_state: BattleState, move: BattleMoveInfo) -> float:
        # 使用修改后的状态值
        attacker_stats = self._get_modified_stats(attacker_state)
        defender_stats = self._get_modified_stats(defender_state)

        atk_stat = attacker_stats.attack if move.damage_class_id == 2 else attacker_stats.sp_attack
        def_stat = defender_stats.defense if move.damage_class_id == 2 else defender_stats.sp_defense
        return atk_stat / max(1, def_stat)

    def _calculate_move_score(self, attacker_state: BattleState, defender_state: BattleState,
                              move: BattleMoveInfo, logger_obj: Optional[BattleLogger] = None) -> float:
        attacker_ctx = attacker_state.context
        defender_ctx = defender_state.context

        eff = self.calculate_type_effectiveness([move.type_name], defender_ctx.types)
        stab = 1.5 if move.type_name in attacker_ctx.types else 1.0

        # Note: We don't cache eff/stab on the move object here to avoid side effects during simulation if possible,
        # but the original code did. For now, let's calculate it fresh.
        # 获取等级 (假设从 context 获取)
        level = attacker_state.context.pokemon.level
        atk_def_ratio = self._get_atk_def_ratio(attacker_state, defender_state, move)
        # score = move.power * (move.accuracy / 100.0) * eff * stab * atk_def_ratio
        # 使用真实的伤害公式估算分数
        base_damage = ((2 * level / 5 + 2) * move.power * atk_def_ratio) / 50 + 2
        score = base_damage * (move.accuracy / 100.0) * eff * stab

        # [新增] 为有追加效果的攻击技能添加额外评分
        # 如果是伤害+异常状态类技能 (meta_category_id == 4)，则加上异常状态的价值评分
        if move.meta_category_id == 4:  # damage+ailment: 攻击并造成异常状态
            # 评估异常状态的追加价值
            ailment_value = 0

            # 根据异常状态类型调整评分
            ailment_id = move.meta_ailment_id
            # 不同异常状态的价值不同： paralysis(1), sleep(2), freeze(3), burn(4), poison(5)
            if ailment_id in [1, 4, 5]:  # paralysis, burn, poison - 持续性影响
                ailment_value = 15.0
            elif ailment_id in [2, 3]:  # sleep, freeze - 行动限制
                ailment_value = 12.0
            else:
                ailment_value = 8.0  # 其他异常状态

            # 根据异常状态触发几率调整评分
            ailment_chance = move.ailment_chance / 100.0
            if ailment_chance == 0:  # 如果几率为0，假设为100%
                ailment_chance = 1.0
            ailment_value *= ailment_chance

            # 如果对手HP较高，异常状态技能更有价值
            hp_ratio = defender_state.current_hp / defender_state.context.pokemon.stats.hp
            if hp_ratio > 0.7:
                ailment_value *= 1.3  # 高HP时异常值更高

            score += ailment_value

        # [新增] 为有追加效果的其他攻击技能也添加额外评分
        elif move.meta_category_id == 6:  # damage+lower: 攻击并降低能力
            # 评估降低对手能力的价值
            if hasattr(move, 'stat_changes') and move.stat_changes:
                for change in move.stat_changes:
                    if change.get('change', 0) < 0:  # 负数表示降低对手能力
                        # 根据降低能力的幅度和当前等级调整评分
                        change_amount = abs(change.get('change', 0))
                        current_stage = defender_state.stat_levels.get(change.get('stat_id', 0), 0) if defender_state.stat_levels else 0
                        # 如果对手当前能力等级较高，降低更有价值
                        value = 5.0 + (max(0, current_stage) * 3) * change_amount
                        score += value
        elif move.meta_category_id == 7:  # damage+raise: 攻击并提升能力
            # 评估提升自己能力的价值
            if hasattr(move, 'stat_changes') and move.stat_changes:
                for change in move.stat_changes:
                    if change.get('change', 0) > 0:  # 正数表示提升自己能力
                        change_amount = change.get('change', 0)
                        current_stage = attacker_state.stat_levels.get(change.get('stat_id', 0), 0) if attacker_state.stat_levels else 0
                        # 如果当前能力等级不是太高，提升更有价值
                        value = 5.0 + (min(6 - current_stage, change_amount) * 15)
                        score += value
        elif move.meta_category_id == 8:  # damage+heal: 攻击并回复
            # 评估回复效果的价值
            drain_percent = move.drain if hasattr(move, 'drain') and move.drain is not None else 50
            drain_ratio = drain_percent / 100.0
            # 根据回复比例调整
            heal_value = base_damage * drain_ratio * 0.8  # 按伤害的一定比例计算回复价值
            current_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
            if current_hp_ratio < 0.5:  # 如果HP较低，回复更有价值
                heal_value *= 2.0
            score += heal_value

        if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
            logger.info(
                f"评分计算详情 - {move.move_name}: "
                f"基础伤害({move.power}) * 命中率({move.accuracy/100.0:.2f}) * "
                f"克制({eff}) * STAB({stab}) * 攻防比({atk_def_ratio:.2f}) = {score:.2f}"
            )
        return score

    def get_best_move(self, attacker_state: BattleState, defender_state: BattleState,
                      logger_obj: Optional[BattleLogger] = None) -> BattleMoveInfo:
        """
        智能选择最佳技能（包含攻击和变化）
        """
        attacker_ctx = attacker_state.context
        current_pps = attacker_state.current_pps

        available_moves = []
        for i, move in enumerate(attacker_ctx.moves):
            if current_pps[i] > 0:
                available_moves.append(move)

        if not available_moves:
            if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                logger.info("没有可用招式，使用挣扎")
            return self.get_struggle_move()

        best_move = None
        best_score = -999.0

        # 遍历所有可用技能
        for move in available_moves:
            current_score = 0.0

            if move.power > 0:
                # 攻击技能评分：基于预期伤害
                current_score = self._calculate_move_score(attacker_state, defender_state, move, logger_obj)

                # [新增] 斩杀奖励：如果这一击能直接击败对手，给予巨额加分，确保 AI 优先收割
                # 需要根据 calculate_damage_core 估算伤害，这里简化处理：
                # 如果 伤害分 > 对手当前HP，这就很高了，因为 _calculate_move_score 返回的大致是伤害期望值
                if current_score >= defender_state.current_hp:
                    current_score += 1000.0

            else:
                # 变化技能评分：基于战术价值
                current_score = self._calculate_status_move_score(attacker_state, defender_state, move, logger_obj)

                # [新增] 随机因子：让 AI 稍微不可预测一点，也防止两个评分完全一样时死板
                current_score += random.uniform(0, 5)

            if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                logger.info(f"技能 {move.move_name} 评分: {current_score:.2f}")

            if current_score > best_score:
                best_score = current_score
                best_move = move

        # 如果所有技能评分都很低（例如：攻击打不动，变化技能已加满），可能随机选一个或者还是选最高的
        if best_move is None:
            # 兜底：随机选一个
            return random.choice(available_moves)

        if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
            logger.info(f"最终选择: {best_move.move_name} (综合评分: {best_score:.2f})")

        return best_move

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
                    # logger.info(f"防御方宝可梦免疫了异常状态: ID={ailment_id}")
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
                        # logger.info(f"招式触发了异常状态: ID={ailment_id} ({status_effect})")

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
            drain_percent = move.drain if hasattr(move, 'drain') and move.drain is not None else 50  # 默认50%如果未设置
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
                    logger_obj.log(f"{attacker.context.pokemon.name}通过攻击吸收了{amount}点HP！（造成伤害{damage_dealt}）\n\n")
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
        Execute a single action. Returns True if defender fainted.
        """
        is_struggle = (move.move_id == self.STRUGGLE_MOVE_ID)

        # Deduct PP
        if not is_struggle:
            # Find index of move in context to update state pps
            try:
                # We assume the move object is one of the objects in attacker.context.moves
                # However, get_best_move returns the object from context.moves
                idx = attacker.context.moves.index(move)
                if attacker.current_pps[idx] > 0:
                    attacker.current_pps[idx] -= 1
            except ValueError:
                pass # Should not happen if logic is correct

        # Find the move index to show PP information
        try:
            move_idx = attacker.context.moves.index(move)
            current_pp = attacker.current_pps[move_idx]
            max_pp = move.max_pp
            pp_info = f" (PP: {current_pp}/{max_pp})"
        except ValueError:
            # If move is not found in context.moves (shouldn't happen), use basic info
            pp_info = f" (PP: {move.current_pp}/{move.max_pp})"

        # Log the move usage first
        if move.power == 0:
            logger_obj.log(f"{attacker.context.pokemon.name} 使用了 {move.move_name}{pp_info}！\n\n")
            # 即使是变化技能也要执行效果计算，以处理异常状态、能力变化等特殊效果
            _, effects = self._calculate_damage_core(attacker, defender, move)

            # 检查是否命中
            if effects["missed"]:
                logger_obj.log("没有击中目标！\n\n")
            else:
                # 处理特殊meta效果并记录
                meta_effects = effects.get("meta_effects", [])
                self._log_meta_effects(attacker, defender, meta_effects, logger_obj)

                # Apply healing effects from meta_effects (e.g., drain moves)
                for meta_effect in meta_effects:
                    effect_type = meta_effect.get("type", "")
                    if effect_type == "heal":
                        heal_amount = meta_effect.get("amount", 0)
                        attacker.current_hp = min(attacker.context.pokemon.stats.hp, attacker.current_hp + heal_amount)
                    # 2. ✅ 新增：处理自残/消耗 (Category 3 负数 healing)
                    elif effect_type == "damage" and meta_effect.get("damage_ratio", 0) != 0:
                        # 注意：普通攻击的伤害也是 type="damage"，但通常由 calculate_damage_core 返回值直接扣除
                        # 这里主要是为了处理 status move 的自我损伤
                        damage_amount = meta_effect.get("amount", 0)
                        attacker.current_hp = max(0, attacker.current_hp - damage_amount)
        else:
            dmg, effects = self._calculate_damage_core(attacker, defender, move)
            defender.current_hp -= dmg

            desc = f"{attacker.context.pokemon.name} 使用了 {move.move_name}{pp_info}！\n\n"
            if is_struggle:
                desc = f"{attacker.context.pokemon.name} 使用了挣扎！（PP耗尽）\n\n"

            # For attack moves, log the damage after move usage
            logger_obj.log(f"{desc} 造成 {dmg} 点伤害。\n\n")

            if effects["missed"]:
                logger_obj.log("没有击中目标！\n\n")
            else:
                if effects["is_crit"]: logger_obj.log("击中要害！\n\n")
                eff = effects["type_effectiveness"]
                if eff > 1.0: logger_obj.log("效果绝佳！\n\n")
                elif eff == 0.0: logger_obj.log("似乎没有效果！\n\n")
                elif eff < 1.0: logger_obj.log("效果不佳！\n\n")

                # 处理特殊meta效果并记录
                meta_effects = effects.get("meta_effects", [])
                self._log_meta_effects(attacker, defender, meta_effects, logger_obj)

                # Apply healing effects from meta_effects (e.g., drain moves)
                for meta_effect in meta_effects:
                    effect_type = meta_effect.get("type", "")
                    if effect_type == "heal":
                        heal_amount = meta_effect.get("amount", 0)
                        attacker.current_hp = min(attacker.context.pokemon.stats.hp, attacker.current_hp + heal_amount)
                    elif effect_type == "damage" and meta_effect.get("damage_ratio", 0) != 0:
                        # 注意：普通攻击的伤害也是 type="damage"，但通常由 calculate_damage_core 返回值直接扣除
                        # 这里主要是为了处理 status move 的自我损伤
                        damage_amount = meta_effect.get("amount", 0)
                        attacker.current_hp = max(0, attacker.current_hp - damage_amount)

        # Process stat changes from pre-loaded move data (avoiding database queries in combat loop)
        # This should happen after the move usage is logged
        # ⚠️ Check if this is a meta category that's already handled in _calculate_damage_core (2, 6, 7)
        # to avoid double effect issues
        if move.move_id > 0 and move.stat_changes and move.meta_category_id not in [2, 6, 7]:
            # Use pre-loaded stat changes and target_id instead of querying database
            stat_changes = move.stat_changes
            target_id = move.target_id

            # Apply stat changes to the target(s) based on target_id
            # For now, we'll apply stat changes to the defender by default for offensive moves
            # and to the attacker for stat-raising moves
            # For simplicity, we'll apply to defender if it's an attacking move with negative stat changes
            # and to attacker if it's a stat-raising move

            # Apply stat changes to defender
            if target_id in [2, 8, 10, 11, 14]:  # Opponent-related targets
                # Apply to defender
                defender.stat_levels = defender.stat_levels or {}
                _, new_levels = self.stat_modifier_service.apply_stat_changes(
                    defender.context.pokemon.stats, stat_changes, defender.stat_levels)
                defender.stat_levels = new_levels

                # Log stat changes
                for change in stat_changes:
                    stat_id = change['stat_id']
                    stat_change = change['change']
                    if stat_change != 0:
                        stat_name = self._get_stat_name_by_id(stat_id)
                        if stat_change > 0:
                            logger_obj.log(f"{defender.context.pokemon.name}的{stat_name}提升了！\n\n")
                        else:
                            logger_obj.log(f"{defender.context.pokemon.name}的{stat_name}降低了！\n\n")

            # Apply stat changes to attacker
            elif target_id in [3, 4, 5, 7, 13, 15]:  # Self-related targets
                # Apply to attacker
                attacker.stat_levels = attacker.stat_levels or {}
                _, new_levels = self.stat_modifier_service.apply_stat_changes(
                    attacker.context.pokemon.stats, stat_changes, attacker.stat_levels)
                attacker.stat_levels = new_levels

                # Log stat changes
                for change in stat_changes:
                    stat_id = change['stat_id']
                    stat_change = change['change']
                    if stat_change != 0:
                        stat_name = self._get_stat_name_by_id(stat_id)
                        if stat_change > 0:
                            logger_obj.log(f"{attacker.context.pokemon.name}的{stat_name}提升了！\n\n")
                        else:
                            logger_obj.log(f"{attacker.context.pokemon.name}的{stat_name}降低了！\n\n")
            else:
                # Default behavior: if any stat changes are positive, apply to attacker (self)
                # if any are negative, apply to defender (opponent)
                positive_changes = any(change['change'] > 0 for change in stat_changes)
                negative_changes = any(change['change'] < 0 for change in stat_changes)

                if positive_changes:
                    attacker.stat_levels = attacker.stat_levels or {}
                    _, new_levels = self.stat_modifier_service.apply_stat_changes(
                        attacker.context.pokemon.stats, stat_changes, attacker.stat_levels)
                    attacker.stat_levels = new_levels

                    # Log positive stat changes
                    for change in stat_changes:
                        if change['change'] > 0:
                            stat_id = change['stat_id']
                            stat_name = self._get_stat_name_by_id(stat_id)
                            logger_obj.log(f"{attacker.context.pokemon.name}的{stat_name}提升了！\n\n")

                if negative_changes:
                    defender.stat_levels = defender.stat_levels or {}
                    _, new_levels = self.stat_modifier_service.apply_stat_changes(
                        defender.context.pokemon.stats, stat_changes, defender.stat_levels)
                    defender.stat_levels = new_levels

                    # Log negative stat changes
                    for change in stat_changes:
                        if change['change'] < 0:
                            stat_id = change['stat_id']
                            stat_name = self._get_stat_name_by_id(stat_id)
                            logger_obj.log(f"{defender.context.pokemon.name}的{stat_name}降低了！\n\n")

        # Recoil for struggle (should happen after stat changes)
        if is_struggle:
            recoil = max(1, attacker.context.pokemon.stats.hp // 4)
            attacker.current_hp -= recoil
            logger_obj.log(f"{attacker.context.pokemon.name} 因挣扎受到 {recoil} 点反作用伤害！\n\n")
            if attacker.current_hp <= 0:
                logger_obj.log(f"{attacker.context.pokemon.name} 倒下了！\n\n")
                return True # Attacker fainted (draw/loss depending on rules, but battle ends)

        if defender.current_hp <= 0:
            logger_obj.log(f"{defender.context.pokemon.name} 倒下了！\n\n")
            return True

        return False

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

    def _calculate_status_move_score(self, attacker_state: BattleState, defender_state: BattleState,
                                     move: BattleMoveInfo, logger_obj: Optional[BattleLogger] = None) -> float:
        """计算变化技能的评分"""
        score = 0.0


        # 1. 使用预加载的技能属性变化数据（避免在战斗循环中查询数据库）
        stat_changes = move.stat_changes
        target_id = move.target_id

        if not stat_changes:
            # 如果没有数据或者是纯状态异常技能（如电磁波），给一个基础分，防止完全不用
            # 可以在这里扩展异常状态的逻辑
            return 10.0

        # 2. 根据meta_category_id调整评分策略
        # 根据不同的技能类型调整评分逻辑
        if move.meta_category_id == 0:  # damage: 纯粹的攻击招式（无附加效果）
            # 对于纯攻击技能，保持基础评分
            score = 0.0

        elif move.meta_category_id == 1:  # ailment: 造成异常状态
            # 造成异常状态的技能，根据实际几率和状态类型调整评分
            base_score = 15.0
            # 根据异常状态触发几率调整评分
            chance_multiplier = (move.ailment_chance / 100.0)  # 转换为0-1的倍数
            # 如果几率为0，可能是默认100%（如纯状态技能），或者确实为0
            if chance_multiplier == 0:
                chance_multiplier = 1.0  # 假设为100%触发
            score += base_score * chance_multiplier

            # 根据异常状态类型调整评分
            ailment_id = move.meta_ailment_id
            # 不同异常状态的价值不同： paralysis(1), sleep(2), freeze(3), burn(4), poison(5)
            # 麻痹、灼伤、中毒对战斗持续性影响较大，睡眠、冰冻能直接限制行动但可能被替换
            if ailment_id in [1, 4, 5]:  # paralysis, burn, poison - 持续性影响
                score *= 1.4
            elif ailment_id in [2, 3]:  # sleep, freeze - 行动限制，但可能被替换
                score *= 1.2

            # 如果对手HP较高，异常状态技能更有价值
            hp_ratio = defender_state.current_hp / defender_state.context.pokemon.stats.hp
            if hp_ratio > 0.7:
                score *= 1.3  # 高HP时异常值更高

        elif move.meta_category_id == 2:  # net-good-stats: 提升能力
            # --- 优化点 A：降低强化/削弱技能的基础权重 ---
            # 提升自身能力的技能，大幅降低基础分
            score += 5.0  # 原来是10.0，现在降低到5.0

            # 如果对手是高攻手，提升防御更有价值
            opponent_attack = defender_state.context.pokemon.stats.attack
            if opponent_attack > attacker_state.context.pokemon.stats.defense:
                score *= 1.1  # 提升防御评分，但仍然不高

        elif move.meta_category_id == 3:  # heal: 回复
            # 回复技能，根据实际healing值和当前HP状态调整评分
            current_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
            heal_ratio = move.healing  # 获取实际的回复比例

            if heal_ratio > 0:  # 正数为回复
                # 根据回复量调整基础评分
                score += heal_ratio * 100.0  # 回复比例越高，基础评分越高

                # 如果HP较低，回复技能更有价值
                if current_hp_ratio < 0.5:  # HP低于50%时，回复技能更珍贵
                    score *= 2.0
                elif current_hp_ratio < 0.8:  # HP低于80%时，回复技能有价值
                    score *= 1.5
            elif heal_ratio < 0:  # 负数为消耗HP（如替身、诅咒等）
                # 消耗类技能的评分策略 - 主要基于战术价值
                score += abs(heal_ratio) * 50.0  # 消耗比例越高，基础评分越高

                # 只有在有战术意义时使用（例如：满血时用替身建立保护）
                if current_hp_ratio > 0.9:  # 在接近满血时使用消耗技能可能更有价值
                    score *= 1.3

        elif move.meta_category_id == 4:  # damage+ailment: 攻击并造成异常状态
            # 攻击并造成异常状态，评估为强力技能
            score += 25.0  # 高基础加分
            # 评估对当前对手的威胁
            hypothetical_damage, _ = self._calculate_damage_core(attacker_state, defender_state, move, simulate=True)
            if hypothetical_damage > defender_state.current_hp * 0.4:  # 如果能造成40%以上伤害
                score += 10.0

        elif move.meta_category_id == 5:  # swagger: 虚张声势类
            # 虚张声势类技能，使对手混乱但提升其攻击
            score += 12.0  # 基础加分
            # 如果对手攻击已经很高，让其混乱可能更危险，需要谨慎
            opponent_attack_level = defender_state.stat_levels.get(1, 0) if defender_state.stat_levels else 0
            if opponent_attack_level > 1:  # 如果对手攻击等级已经高于正常
                score *= 0.7  # 降低评分

        elif move.meta_category_id == 6:  # damage+lower: 攻击并降低能力
            # 攻击并降低能力，评估为强力技能
            # --- 优化点 A：降低强化/削弱技能的基础权重 ---
            score += 8.0  # 原来是20.0，现在降低到8.0
            # 评估对当前对手的威胁
            hypothetical_damage, _ = self._calculate_damage_core(attacker_state, defender_state, move, simulate=True)
            if hypothetical_damage > 0:  # 如果能造成伤害
                score += 10.0

        elif move.meta_category_id == 7:  # damage+raise: 攻击并提升能力
            # 攻击并提升能力，评估为强力技能
            # --- 优化点 A：降低强化/削弱技能的基础权重 ---
            score += 10.0  # 原来是22.0，现在降低到10.0
            # 评估对当前对手的威胁
            hypothetical_damage, _ = self._calculate_damage_core(attacker_state, defender_state, move, simulate=True)
            if hypothetical_damage > 0:  # 如果能造成伤害
                score += 8.0

        elif move.meta_category_id == 8:  # damage+heal: 攻击并回复
            # 攻击并回复，评估为强力技能
            score += 28.0  # 很高的基础加分（攻击+回复双重效果）
            # 评估对当前对手的威胁
            hypothetical_damage, _ = self._calculate_damage_core(attacker_state, defender_state, move, simulate=True)
            if hypothetical_damage > 0:  # 如果能造成伤害
                score += 12.0

        elif move.meta_category_id == 9:  # ohko: 一击必杀
            # 一击必杀技能，需要特殊评估
            score += 10.0  # 基础加分
            # 但由于命中率通常很低，在评估时需要考虑

        elif move.meta_category_id == 10:  # whole-field-effect: 全场效果
            # 全场效果如天气变化
            score += 15.0  # 基础加分
            # 可以根据当前宝可梦类型和天气相性调整

        elif move.meta_category_id == 11:  # field-effect: 场地效果
            # 场地效果如光墙、反射壁
            score += 18.0  # 基础加分
            # 根据当前战斗状况调整

        elif move.meta_category_id == 12:  # force-switch: 强制替换
            # 强制替换技能
            score += 8.0  # 基础加分
            # 在特定情况下可能非常有用

        elif move.meta_category_id == 13:  # unique: 特殊/独特
            # 独特效果，根据具体效果调整
            score += 12.0  # 基础加分
            # 可以根据具体情况进一步调整

        # 3. 遍历所有受影响的属性
        for change in stat_changes:
            stat_id = change['stat_id']
            delta = change['change']

            # 判断目标是自己还是对手
            # 简化逻辑：正向增益通常给自己，负向减益给对手
            # 也可以配合 target_id 判断 (2, 8, 10, 11, 14 为对手)
            is_opponent_target = target_id in [2, 8, 10, 11, 14] or delta < 0

            if is_opponent_target:

                # -- 试图降低对手能力 --
                current_stage = defender_state.stat_levels.get(stat_id, 0) if defender_state.stat_levels else 0
                if current_stage <= -2:
                    continue  # 已经降了两级了，没必要再降，甚至可以给负分
                # # 如果已经降无可降 (-6)，则该技能无效，0分
                # if current_stage <= -6:
                #     continue

                # 基础分大幅降低，依赖战况
                # 比如：如果对手物理攻击很高，降低攻击(Growl)价值高；如果对手是特攻手，Growl价值低
                score += 2.0 + (current_stage * 1)  # 原来是 5.0 + (current_stage * 3)，现在大幅降低

            else:
                # -- 试图提升自己能力 --
                current_stage = attacker_state.stat_levels.get(stat_id, 0) if attacker_state.stat_levels else 0

                # 如果已经升无可升 (+6)，则无效
                if current_stage >= 6:
                    continue

                # --- 优化点 A：只有在必要时才强化 ---
                # 提升幅度调整，考虑已有等级的影响
                # 基础分降低，只有在必要时（如能够确立斩杀线）才强化
                base_value = 10.0  # 原来是20.0，现在降低
                stage_factor = 5  # 原来是15，现在降低

                # 根据当前等级调整提升欲望
                if current_stage > 0:
                    # 已有强化的情况下，继续强化的欲望指数级下降
                    score += base_value + (delta * stage_factor * (0.7 ** current_stage))
                else:
                    # 没有强化时，正常计算
                    score += base_value + (delta * stage_factor)

        # 4. 战术修正：如果对手血量很低，不需要变化技能，直接打死更好
        # 假设斩杀线是 25%
        if defender_state.current_hp < defender_state.context.pokemon.stats.hp * 0.25:
            score *= 0.1


        # --- 优化点 B：伤害阈值判断 (最重要的修正) ---
        # 检查是否有攻击技能能造成不错伤害，若有则优先攻击
        max_expected_damage = 0
        for battle_move in attacker_state.context.moves:
            if battle_move.power > 0:
                # 使用 simulate=True 防止副作用
                hypothetical_damage, _ = self._calculate_damage_core(attacker_state, defender_state, battle_move, simulate=True)
                max_expected_damage = max(max_expected_damage, hypothetical_damage)

        defender_total_hp = defender_state.context.pokemon.stats.hp
        if defender_total_hp > 0:
            damage_percentage = max_expected_damage / defender_total_hp
            # 如果能打掉 25% 以上，状态技能评分 * 0.1
            if damage_percentage >= 0.25:
                score *= 0.1
            # 如果能打掉 33% 以上，状态技能评分 * 0.05
            if damage_percentage >= 0.33:
                score *= 0.05
            # 如果能打掉 50% 以上，基本不考虑状态技能
            if damage_percentage >= 0.5:
                score *= 0.01

        # --- 优化点 D：根据血量健康状况决策 ---
        # 如果 HP 低于 50%，AI 应该进入"拼命模式"，停止任何强化/削弱行为，直接输出
        attacker_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
        if attacker_hp_ratio < 0.5:
            score *= 0.05  # 极大降低变化技能评分
        elif attacker_hp_ratio < 0.4:
            score *= 0.01  # 更低的评分

        # --- 优化点 C：防止反复横跳 (Ping-Pong) ---
        # 检查自身属性等级，如果已经有强化等级（>0），继续强化的欲望应该指数级降低
        if hasattr(attacker_state, 'stat_levels') and attacker_state.stat_levels:
            # 优先检查攻击力、防御力和速度
            attacker_attack_level = attacker_state.stat_levels.get(StatID.ATTACK.value, 0)
            attacker_defense_level = attacker_state.stat_levels.get(StatID.DEFENSE.value, 0)
            attacker_speed_level = attacker_state.stat_levels.get(StatID.SPEED.value, 0)

            # 如果已有强化，进一步强化的评分大幅降低
            if attacker_attack_level > 0 or attacker_defense_level > 0 or attacker_speed_level > 0:
                for change in move.stat_changes if move.stat_changes else []:
                    if change.get('change', 0) > 0:  # 增益效果
                        # 对于已有等级的属性，进一步提升的收益降低
                        stat_id = change.get('stat_id', 0)
                        current_level = attacker_state.stat_levels.get(stat_id, 0)
                        if current_level > 0:
                            # 已经有强化的情况下，继续强化的收益指数级下降
                            reinforcement_penalty = 0.1 * (0.5 ** current_level)
                            score *= reinforcement_penalty

        # 检查对手属性等级，如果对手已经被削弱过（< 0），进一步削弱收益降低
        if hasattr(defender_state, 'stat_levels') and defender_state.stat_levels:
            defender_attack_level = defender_state.stat_levels.get(StatID.ATTACK.value, 0)
            defender_defense_level = defender_state.stat_levels.get(StatID.DEFENSE.value, 0)
            defender_speed_level = defender_state.stat_levels.get(StatID.SPEED.value, 0)

            # 如果对手已有削弱，进一步削弱的评分降低
            if defender_attack_level < 0 or defender_defense_level < 0 or defender_speed_level < 0:
                for change in move.stat_changes if move.stat_changes else []:
                    if change.get('change', 0) < 0:  # 削弱效果
                        # 对于已经被削弱的属性，进一步削弱的收益降低
                        debuff_penalty = 0.2  # 进一步削弱收益降低
                        score *= debuff_penalty

        # --- 通用逻辑：如果当前有招式能直接斩杀对手，则完全不使用状态技能 ---
        for m in attacker_state.context.moves:
            if m.power > 0:
                dmg, _ = self._calculate_damage_core(attacker_state, defender_state, m, simulate=True)
                if dmg >= defender_state.current_hp:
                    return -100.0  # 绝对不选

        return score