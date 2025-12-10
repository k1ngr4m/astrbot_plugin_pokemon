import random
from typing import List, Tuple, Dict, Any, Optional, Protocol
from dataclasses import dataclass

from astrbot.api import logger
from ..models.adventure_models import BattleContext, BattleMoveInfo


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

    @classmethod
    def from_context(cls, context: BattleContext) -> 'BattleState':
        return cls(
            context=context,
            current_hp=context.current_hp,
            current_pps=[m.current_pp for m in context.moves]
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

    def __init__(self):
        self._struggle_move = self._create_struggle_move()

    def _create_struggle_move(self) -> BattleMoveInfo:
        return BattleMoveInfo(
            power=40, accuracy=100.0, type_name='normal', damage_class_id=2,
            priority=0, type_effectiveness=1.0, stab_bonus=1.0,
            max_pp=10, current_pp=10, move_id=self.STRUGGLE_MOVE_ID, move_name="挣扎"
        )

    def get_struggle_move(self) -> BattleMoveInfo:
        return self._struggle_move

    def calculate_type_effectiveness(self, attacker_types: List[str], defender_types: List[str]) -> float:
        effectiveness = 1.0
        for atk_type in attacker_types:
            atk_dict = self.TYPE_CHART.get(atk_type.lower())
            if not atk_dict: continue
            for def_type in defender_types:
                effectiveness *= atk_dict.get(def_type.lower(), 1.0)
        return effectiveness

    def _get_atk_def_ratio(self, attacker_ctx: BattleContext, defender_ctx: BattleContext, move: BattleMoveInfo) -> float:
        atk_stat = attacker_ctx.pokemon.stats.attack if move.damage_class_id == 2 else attacker_ctx.pokemon.stats.sp_attack
        def_stat = defender_ctx.pokemon.stats.defense if move.damage_class_id == 2 else defender_ctx.pokemon.stats.sp_defense
        return atk_stat / max(1, def_stat)

    def _calculate_move_score(self, attacker_ctx: BattleContext, defender_ctx: BattleContext,
                              move: BattleMoveInfo, logger_obj: Optional[BattleLogger] = None) -> float:
        eff = self.calculate_type_effectiveness([move.type_name], defender_ctx.types)
        stab = 1.5 if move.type_name in attacker_ctx.types else 1.0

        # Note: We don't cache eff/stab on the move object here to avoid side effects during simulation if possible,
        # but the original code did. For now, let's calculate it fresh.

        atk_def_ratio = self._get_atk_def_ratio(attacker_ctx, defender_ctx, move)
        score = move.power * (move.accuracy / 100.0) * eff * stab * atk_def_ratio

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
        Select the best move based on the current state (PP availability).
        """
        attacker_ctx = attacker_state.context
        defender_ctx = defender_state.context
        current_pps = attacker_state.current_pps

        available_moves = []
        for i, move in enumerate(attacker_ctx.moves):
            if current_pps[i] > 0:
                available_moves.append(move)

        if not available_moves:
            if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                logger.info("没有可用招式，使用挣扎")
            return self.get_struggle_move()

        attack_moves = [m for m in available_moves if m.power > 0]
        status_moves = [m for m in available_moves if m.power == 0]

        if not attack_moves:
            if status_moves:
                selected = random.choice(status_moves)
                if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                    logger.info(f"没有攻击招式，随机选择变化招式: {selected.move_name}")
                return selected
            else:
                if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                    logger.info("既没有攻击招式也没有变化招式，使用挣扎")
                return self.get_struggle_move()

        # Select best attack move
        best_move = None
        best_score = -1.0

        for move in attack_moves:
            score = self._calculate_move_score(attacker_ctx, defender_ctx, move, logger_obj)
            if score > best_score:
                best_score = score
                best_move = move
        
        if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
            logger.info(f"最终选择: {best_move.move_name} (评分: {best_score:.2f})")
        return best_move

    def _calculate_damage_core(self, attacker_ctx: BattleContext, defender_ctx: BattleContext, move: BattleMoveInfo) -> Tuple[int, Dict[str, Any]]:
        if random.random() * 100 > move.accuracy:
            return 0, {"missed": True, "type_effectiveness": 1.0, "is_crit": False}

        atk_stat = attacker_ctx.pokemon.stats.attack if move.damage_class_id == 2 else attacker_ctx.pokemon.stats.sp_attack
        def_stat = defender_ctx.pokemon.stats.defense if move.damage_class_id == 2 else defender_ctx.pokemon.stats.sp_defense
        level = attacker_ctx.pokemon.level

        base_damage = ((2 * level / 5 + 2) * move.power * atk_stat / max(1, def_stat)) / 50 + 2

        is_crit = random.random() < self.CRIT_RATE
        crit_multiplier = 1.5 if is_crit else 1.0
        random_multiplier = random.uniform(0.85, 1.0)

        eff = self.calculate_type_effectiveness([move.type_name], defender_ctx.types)
        stab = 1.5 if move.type_name in attacker_ctx.types else 1.0

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
        
        u_spd = user_state.context.pokemon.stats.speed
        w_spd = wild_state.context.pokemon.stats.speed
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

        # Status move
        if move.damage_class_id == 1:
            logger_obj.log(f"{attacker.context.pokemon.name} 使用了 {move.move_name}！")
            return False

        # Attack move
        dmg, effects = self._calculate_damage_core(attacker.context, defender.context, move)
        defender.current_hp -= dmg
        
        desc = f"{attacker.context.pokemon.name} 使用了 {move.move_name}！"
        if is_struggle:
            desc = f"{attacker.context.pokemon.name} 使用了挣扎！（PP耗尽）\n\n"
        
        # PP display for logging (optional, maybe just show current/max)
        # For simulation we don't care about logging PP details usually
        logger_obj.log(f"{desc} 造成 {dmg} 点伤害。\n\n")

        if effects["missed"]:
            logger_obj.log("没有击中目标！\n\n")
        else:
            if effects["is_crit"]: logger_obj.log("击中要害！\n\n")
            eff = effects["type_effectiveness"]
            if eff > 1.0: logger_obj.log("效果绝佳！\n\n")
            elif eff == 0.0: logger_obj.log("似乎没有效果！\n\n")
            elif eff < 1.0: logger_obj.log("效果不佳！\n\n")

        # Recoil for struggle
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
