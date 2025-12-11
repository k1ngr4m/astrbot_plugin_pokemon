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
    # --- Constants ---
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

    def _calculate_damage_core(self, attacker_state: BattleState, defender_state: BattleState, move: BattleMoveInfo) -> Tuple[int, Dict[str, Any]]:
        if random.random() * 100 > move.accuracy:
            return 0, {"missed": True, "type_effectiveness": 1.0, "is_crit": False}

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

        return int(final_damage), {
            "missed": False,
            "type_effectiveness": eff,
            "is_crit": is_crit,
            "stab_bonus": stab
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
            logger_obj.log(f"{attacker.context.pokemon.name} 使用了 {move.move_name}{pp_info}！")
        else:
            dmg, effects = self._calculate_damage_core(attacker, defender, move)
            defender.current_hp -= dmg

            desc = f"{attacker.context.pokemon.name} 使用了 {move.move_name}{pp_info}！"
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

        # Process stat changes from pre-loaded move data (avoiding database queries in combat loop)
        # This should happen after the move usage is logged
        if move.move_id > 0 and move.stat_changes:
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
        best_dmg_move_score = 0
        for m in attacker_state.context.moves:
            if m.power > 0:
                dmg, _ = self._calculate_damage_core(attacker_state, defender_state, m)
                if dmg >= defender_state.current_hp:
                    return -100.0  # 绝对不选

        score = 0.0

        # 1. 使用预加载的技能属性变化数据（避免在战斗循环中查询数据库）
        stat_changes = move.stat_changes
        target_id = move.target_id

        if not stat_changes:
            # 如果没有数据或者是纯状态异常技能（如电磁波），给一个基础分，防止完全不用
            # 可以在这里扩展异常状态的逻辑
            return 10.0

        # 2. 检查是否应该使用状态技能 - 如果攻击技能能造成高伤害，则降低状态技能评分
        # 寻找当前宝可梦的所有攻击技能中预期伤害最高的
        max_expected_damage = 0
        for battle_move in attacker_state.context.moves:
            if battle_move.power > 0:  # 攻击技能
                # 估算这个技能对当前对手的预期伤害
                hypothetical_damage, _ = self._calculate_damage_core(attacker_state, defender_state, battle_move)
                max_expected_damage = max(max_expected_damage, hypothetical_damage)

        # 计算预期伤害占对手总HP的百分比
        defender_total_hp = defender_state.context.pokemon.stats.hp
        if defender_total_hp > 0:
            damage_percentage = max_expected_damage / defender_total_hp
            # 如果预期伤害能打掉对手30%或以上的HP，则状态技能评分大幅降低
            if damage_percentage >= 0.3:
                score *= 0.2  # 降低到原来的20%
                # 如果伤害能打掉50%或以上，几乎不考虑状态技能
                if damage_percentage >= 0.5:
                    score *= 0.1  # 降低到原来的10%

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
                score += 5.0 + (current_stage * 3)

            else:
                # -- 试图提升自己能力 --
                current_stage = attacker_state.stat_levels.get(stat_id, 0) if attacker_state.stat_levels else 0

                # 如果已经升无可升 (+6)，则无效
                if current_stage >= 6:
                    continue

                # 提升幅度越大越好 (例如剑舞+2 比 变硬+1 分高)
                # 基础分 30，每级价值 15 分
                score += 20.0 + (delta * 15)

        # 4. 血量危机判定：如果自己快死了 (HP < 30%)，变化技能评分减半，被迫对攻
        if attacker_state.current_hp / attacker_state.context.pokemon.stats.hp < 0.3:
            score *= 0.5

        # 4. 战术修正：如果对手血量很低，不需要变化技能，直接打死更好
        # 假设斩杀线是 25%
        if defender_state.current_hp < defender_state.context.pokemon.stats.hp * 0.25:
            score *= 0.1

        return score