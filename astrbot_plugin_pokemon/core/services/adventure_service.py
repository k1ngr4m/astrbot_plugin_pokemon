import math
import random
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass, replace

from . import user_pokemon_service
from .exp_service import ExpService
from .pokemon_service import PokemonService
from ..models.common_models import BaseResult
from ...interface.response.answer_enum import AnswerEnum
from ..models.pokemon_models import (
    WildPokemonInfo, PokemonStats, PokemonIVs, PokemonEVs,
    UserPokemonInfo, WildPokemonEncounterLog, PokemonMoves
)
from ..models.trainer_models import BattleTrainer
from ..models.user_models import UserTeam, UserItems
from ...infrastructure.repositories.abstract_repository import (
    AbstractAdventureRepository, AbstractPokemonRepository, AbstractUserRepository, AbstractTeamRepository,
    AbstractUserPokemonRepository, AbstractBattleRepository, AbstractUserItemRepository
)
from ..models.adventure_models import AdventureResult, LocationInfo, BattleResult, BattleMoveInfo
from astrbot.api import logger


# 定义一个简易的战斗上下文
@dataclass
class BattleContext:
    pokemon: Union[UserPokemonInfo, WildPokemonInfo]
    moves: List[BattleMoveInfo]
    types: List[str]
    current_hp: int
    is_user: bool


class AdventureService:
    """冒险区域相关的业务逻辑服务"""

    # --- 常量定义 ---
    TRAINER_ENCOUNTER_RATE = 0.3  # 训练家遭遇几率
    CRIT_RATE = 0.0625  # 暴击几率
    STRUGGLE_MOVE_ID = -1  # 挣扎技能ID

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

    def __init__(
            self,
            adventure_repo: AbstractAdventureRepository,
            pokemon_repo: AbstractPokemonRepository,
            team_repo: AbstractTeamRepository,
            pokemon_service: PokemonService,
            user_repo: AbstractUserRepository,
            user_pokemon_repo: AbstractUserPokemonRepository,
            battle_repo: AbstractBattleRepository,
            user_item_repo: AbstractUserItemRepository,
            exp_service: ExpService,
            config: Dict[str, Any],
            move_repo=None,
    ):
        self.adventure_repo = adventure_repo
        self.pokemon_repo = pokemon_repo
        self.team_repo = team_repo
        self.pokemon_service = pokemon_service
        self.user_repo = user_repo
        self.exp_service = exp_service
        self.user_pokemon_repo = user_pokemon_repo
        self.user_item_repo = user_item_repo
        self.config = config
        self.move_repo = move_repo
        self.battle_repo = battle_repo
        self.trainer_service = None

    def set_trainer_service(self, trainer_service):
        """设置训练家服务"""
        self.trainer_service = trainer_service

    def get_all_locations(self) -> BaseResult[List[LocationInfo]]:
        """获取所有可冒险的区域列表"""
        locations = self.adventure_repo.get_all_locations()
        if not locations:
            return BaseResult(success=True, message=AnswerEnum.ADVENTURE_NO_LOCATIONS.value)

        formatted_locations = [
            LocationInfo(
                id=loc.id,
                name=loc.name,
                description=loc.description or "暂无描述",
                min_level=loc.min_level,
                max_level=loc.max_level
            ) for loc in locations
        ]

        return BaseResult(
            success=True,
            message=AnswerEnum.ADVENTURE_LOCATIONS_FOUND.value,
            data=formatted_locations
        )

    def _create_placeholder_pokemon(self, name: str) -> WildPokemonInfo:
        """创建用于训练家占位的 WildPokemonInfo 对象"""
        return WildPokemonInfo(
            id=0, species_id=0, name=name, gender="M", level=0, exp=0,
            stats=PokemonStats(hp=0, attack=0, defense=0, sp_attack=0, sp_defense=0, speed=0),
            ivs=PokemonIVs(hp_iv=0, attack_iv=0, defense_iv=0, sp_attack_iv=0, sp_defense_iv=0, speed_iv=0),
            evs=PokemonEVs(hp_ev=0, attack_ev=0, defense_ev=0, sp_attack_ev=0, sp_defense_ev=0, speed_ev=0),
            moves=PokemonMoves(move1_id=0, move2_id=0, move3_id=0, move4_id=0),
            nature_id=0,
        )

    def adventure_in_location(self, user_id: str, location_id: int, encounter_npc_only: bool = False) -> BaseResult[
        AdventureResult]:
        """在指定区域进行冒险，随机刷新一只野生宝可梦或训练家"""
        location = self.adventure_repo.get_location_by_id(location_id)
        if not location:
            return BaseResult(success=False,
                              message=AnswerEnum.ADVENTURE_LOCATION_NOT_FOUND.value.format(location_id=location_id))

        user_team_data = self.team_repo.get_user_team(user_id)
        has_team = user_team_data and user_team_data.team_pokemon_ids

        # 判断是否触发训练家遭遇 (强制NPC 或 概率触发)
        should_encounter_trainer = encounter_npc_only or (has_team and random.random() < self.TRAINER_ENCOUNTER_RATE)

        if should_encounter_trainer:
            trainer_result = self.adventure_with_trainer(user_id, location_id)
            if trainer_result.success and trainer_result.data:
                battle_trainer = trainer_result.data
                trainer_name = battle_trainer.trainer.name if battle_trainer.trainer else "训练家"
                return BaseResult(
                    success=True,
                    message=AnswerEnum.ADVENTURE_SUCCESS.value,
                    data=AdventureResult(
                        wild_pokemon=self._create_placeholder_pokemon(trainer_name),
                        location=LocationInfo(id=location.id, name=location.name),
                        trainer=battle_trainer
                    )
                )
            elif encounter_npc_only:
                return BaseResult(success=False, message="没有遇到可挑战的训练家")

        # --- 正常遇到野生宝可梦 ---
        location_pokemon_list = self.adventure_repo.get_location_pokemon_by_location_id(location_id)
        if not location_pokemon_list:
            return BaseResult(success=False, message=AnswerEnum.ADVENTURE_LOCATION_NO_POKEMON.value.format(
                location_name=location.name))

        # 权重随机选择
        selected_ap = random.choices(
            location_pokemon_list,
            weights=[ap.encounter_rate for ap in location_pokemon_list],
            k=1
        )[0]

        wild_level = random.randint(selected_ap.min_level, selected_ap.max_level)
        wild_res = self.pokemon_service.create_single_pokemon(
            species_id=selected_ap.pokemon_species_id,
            max_level=wild_level,
            min_level=wild_level
        )
        if not wild_res.success:
            return BaseResult(success=False, message=wild_res.message)

        wild_pokemon = wild_res.data
        # 构建 info 对象
        wild_pokemon_info = WildPokemonInfo(
            id=0,
            species_id=wild_pokemon.base_pokemon.id,
            name=wild_pokemon.base_pokemon.name_zh,
            gender=wild_pokemon.gender,
            level=wild_level,
            exp=wild_pokemon.exp,
            stats=PokemonStats(**wild_pokemon.stats.__dict__),
            ivs=PokemonIVs(**wild_pokemon.ivs.__dict__),
            evs=PokemonEVs(**wild_pokemon.evs.__dict__),
            moves=PokemonMoves(
                move1_id=wild_pokemon.moves.move1_id, move2_id=wild_pokemon.moves.move2_id,
                move3_id=wild_pokemon.moves.move3_id, move4_id=wild_pokemon.moves.move4_id,
            ),
            nature_id=wild_pokemon.nature_id,
        )

        wild_pokemon_id = self.pokemon_repo.add_wild_pokemon(wild_pokemon_info)
        self.user_pokemon_repo.add_user_encountered_wild_pokemon(
            user_id=user_id,
            wild_pokemon_id=wild_pokemon_id,
            location_id=location.id,
            encounter_rate=selected_ap.encounter_rate,
        )
        return BaseResult(
            success=True,
            message=AnswerEnum.ADVENTURE_SUCCESS.value,
            data=AdventureResult(
                wild_pokemon=wild_pokemon_info,
                location=LocationInfo(id=location.id, name=location.name),
                trainer=None
            )
        )

    def adventure_in_battle(self, user_id: str, wild_pokemon_info: WildPokemonInfo) -> BaseResult:
        """处理用户与野生宝可梦战斗的结果"""
        user_team_data = self.team_repo.get_user_team(user_id)
        if not user_team_data or not user_team_data.team_pokemon_ids:
            return BaseResult(success=False, message=AnswerEnum.USER_TEAM_NOT_SET.value)

        return self.start_battle(user_id, wild_pokemon_info, user_team_data.team_pokemon_ids)

    def start_battle(self, user_id: str, wild_pokemon_info: WildPokemonInfo, user_team_list: List[int] = None) -> \
    BaseResult[BattleResult]:
        """开始一场与野生宝可梦的战斗"""
        if user_team_list is None:
            user_team_data = self.team_repo.get_user_team(user_id)
            if not user_team_data or not user_team_data.team_pokemon_ids:
                return BaseResult(success=False, message=AnswerEnum.USER_TEAM_NOT_SET.value)
            user_team_list = user_team_data.team_pokemon_ids

        wild_ctx = self._create_battle_context(wild_pokemon_info, is_user=False)
        user_pokemon_contexts = []
        for pid in user_team_list:
            u_info = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pid)
            if u_info:
                user_pokemon_contexts.append(self._create_battle_context(u_info, is_user=True))

        current_idx = 0
        battle_result_str = "fail"
        final_user_info = None
        all_win_rates = []
        battle_log = []
        log_id = 0

        while current_idx < len(user_team_list):
            if current_idx >= len(user_pokemon_contexts):  # 防御性编程
                break

            user_ctx = user_pokemon_contexts[current_idx]
            final_user_info = user_ctx.pokemon  # 使用 Context 里的引用

            # 模拟前重置 HP
            sim_u_hp = user_ctx.current_hp
            sim_w_hp = wild_ctx.current_hp

            # 计算胜率 (仅用于展示)
            user_ctx.current_hp = user_ctx.pokemon.stats.hp
            wild_ctx.current_hp = wild_pokemon_info.stats.hp
            u_win_rate, w_win_rate = self.calculate_battle_win_rate(user_ctx, wild_ctx)

            # 恢复实际 HP
            user_ctx.current_hp = sim_u_hp
            wild_ctx.current_hp = sim_w_hp

            all_win_rates.append((u_win_rate, w_win_rate))

            # 实战
            battle_outcome, log_data, rem_wild_hp = self.execute_real_battle(user_ctx, wild_ctx)

            # 更新野生怪状态
            wild_pokemon_info.stats.hp = max(0, rem_wild_hp)
            wild_ctx.current_hp = wild_pokemon_info.stats.hp

            # 上下文已经在 execute_real_battle 中被修改了 (HP, PP)，这里不需要显式回写
            # 只需要将数据记录到日志
            battle_log.append({
                "pokemon_id": user_ctx.pokemon.id,
                "pokemon_name": user_ctx.pokemon.name,
                "species_name": user_ctx.pokemon.species_id,
                "level": user_ctx.pokemon.level,
                "win_rate": u_win_rate,
                "result": battle_outcome,
                "details": log_data
            })

            if battle_outcome == "win":
                battle_result_str = "success"
                break
            else:
                current_idx += 1

        # 计算最终胜率
        final_u_rate, final_w_rate = 0.0, 100.0
        if battle_result_str == "success" and all_win_rates:
            final_u_rate, final_w_rate = all_win_rates[-1]
        elif all_win_rates:
            u_rates = [r[0] for r in all_win_rates]
            w_rates = [r[1] for r in all_win_rates]
            final_u_rate = round(sum(u_rates) / len(u_rates), 2)
            final_w_rate = round(sum(w_rates) / len(w_rates), 2)

        if self.battle_repo:
            log_id = self.battle_repo.save_battle_log(
                user_id=user_id,
                target_name=wild_pokemon_info.name,
                log_data=battle_log,
                result=battle_result_str
            )
        exp_details = self._handle_battle_experience(user_id, battle_result_str, wild_pokemon_info, battle_log)
        self._update_encounter_log(user_id, wild_pokemon_info.id, battle_result_str)

        user_exp_result = None
        if battle_result_str == "success":
            user_exp_result = self.exp_service.add_exp_for_defeating_wild_pokemon(user_id, wild_pokemon_info.level)

        return BaseResult(
            success=True,
            message=AnswerEnum.BATTLE_SUCCESS.value,
            data=BattleResult(
                user_pokemon=self._format_pokemon_summary(final_user_info),
                wild_pokemon=self._format_pokemon_summary(wild_pokemon_info, is_wild=True),
                win_rates={"user_win_rate": final_u_rate, "wild_win_rate": final_w_rate},
                result=battle_result_str,
                exp_details=exp_details,
                battle_log=battle_log,
                log_id=log_id,
                is_trainer_battle=False,
                user_battle_exp_result=user_exp_result
            )
        )

    def _create_battle_context(self, pokemon_info: Union[UserPokemonInfo, WildPokemonInfo],
                               is_user: bool) -> BattleContext:
        types = self.pokemon_repo.get_pokemon_types(pokemon_info.species_id) or ['normal']
        moves_list = self._preload_moves(pokemon_info)
        return BattleContext(
            pokemon=pokemon_info,
            moves=moves_list,
            types=types,
            current_hp=pokemon_info.stats.hp,
            is_user=is_user
        )

    def _preload_moves(self, pokemon: Any) -> List[BattleMoveInfo]:
        """批量加载宝可梦的所有招式详情"""
        move_ids = [pokemon.moves.move1_id, pokemon.moves.move2_id, pokemon.moves.move3_id, pokemon.moves.move4_id]
        valid_ids = [m for m in move_ids if m and m > 0]
        loaded_moves = []
        if self.move_repo:
            for mid in valid_ids:
                m_data = self.move_repo.get_move_by_id(mid)
                if m_data:
                    max_pp = m_data.get('pp', 5) or 5
                    loaded_moves.append(BattleMoveInfo(
                        power=m_data.get('power', 0) or 0,
                        accuracy=m_data.get('accuracy', 100) or 100,
                        type_name=m_data.get('type_name', 'normal'),
                        damage_class_id=m_data.get('damage_class_id', 2),
                        priority=m_data.get('priority', 0),
                        type_effectiveness=1.0,
                        stab_bonus=1.0,
                        move_id=mid,
                        move_name=m_data.get('name_zh', 'Unknown Move'),
                        max_pp=max_pp,
                        current_pp=max_pp
                    ))
        return loaded_moves

    def _get_struggle_move(self) -> BattleMoveInfo:
        """获取挣扎招式的单例/常量"""
        return BattleMoveInfo(
            power=40, accuracy=100.0, type_name='normal', damage_class_id=2,
            priority=0, type_effectiveness=1.0, stab_bonus=1.0,
            max_pp=10, current_pp=10, move_id=self.STRUGGLE_MOVE_ID, move_name="挣扎"
        )

    def get_best_move_from_context(self, attacker_ctx: BattleContext, defender_ctx: BattleContext,
                                   current_pps: List[int] = None) -> BattleMoveInfo:
        """
        选择最佳招式。
        current_pps: 可选，仅用于模拟时传入临时的PP列表，避免修改对象。如果不传则使用 attacker_ctx.moves 里的值。
        """
        moves = attacker_ctx.moves

        # 仅在非模拟模式（实战）下记录日志
        is_simulation = current_pps is not None
        if not is_simulation:
            logger.info(f"技能选择开始: 攻击方 {attacker_ctx.pokemon.name}(Lv.{attacker_ctx.pokemon.level}) 选择最佳招式")

        # 确定可用招式
        available_moves = []
        if current_pps:
            # 模拟模式
            for i, move in enumerate(moves):
                if current_pps[i] > 0:
                    available_moves.append(move)
        else:
            # 实战模式
            available_moves = [m for m in moves if m.current_pp > 0]
            if not is_simulation:
                logger.info(f"实战模式: 招式PP状态 {[m.current_pp for m in moves]}")

        if not available_moves:
            if not is_simulation:
                logger.info("没有可用招式，使用挣扎")
            return self._get_struggle_move()

        if not is_simulation:
            logger.info(f"可用招式: {[m.move_name for m in available_moves]}")

        # 分离攻击和变化招式
        attack_moves = [m for m in available_moves if m.power > 0]
        status_moves = [m for m in available_moves if m.power == 0]

        if not is_simulation:
            logger.info(f"攻击招式: {[m.move_name for m in attack_moves]}")
            logger.info(f"变化招式: {[m.move_name for m in status_moves]}")

        if not attack_moves:
            if status_moves:
                selected_move = random.choice(status_moves)
                if not is_simulation:
                    logger.info(f"没有攻击招式，随机选择变化招式: {selected_move.move_name}")
                return selected_move
            else:
                if not is_simulation:
                    logger.info("既没有攻击招式也没有变化招式，使用挣扎")
                return self._get_struggle_move()

        # 计算每个攻击招式的评分并记录详情（仅在实战模式下记录）
        move_scores = []
        for move in attack_moves:
            score = self._calculate_move_score(attacker_ctx, defender_ctx, move, is_simulation)
            move_scores.append((move, score))
            if not is_simulation:
                logger.info(
                    f"招式 {move.move_name}: 伤害{move.power} 精确度{move.accuracy}% "
                    f"克制系数{move.type_effectiveness} STAB{move.stab_bonus} "
                    f"攻击/防御比率{self._get_atk_def_ratio(attacker_ctx, defender_ctx, move)} "
                    f"→ 评分: {score:.2f}"
                )

        # 选择评分最高的攻击招式
        best_move = max(attack_moves, key=lambda m: self._calculate_move_score(attacker_ctx, defender_ctx, m, is_simulation))
        if not is_simulation:
            logger.info(f"最终选择: {best_move.move_name} (评分: {max([score for _, score in move_scores]):.2f})")
        return best_move

    def _get_atk_def_ratio(self, attacker_ctx: BattleContext, defender_ctx: BattleContext, move: BattleMoveInfo) -> float:
        """获取攻击/防御比率，用于日志记录"""
        atk_stat = attacker_ctx.pokemon.stats.attack if move.damage_class_id == 2 else attacker_ctx.pokemon.stats.sp_attack
        def_stat = defender_ctx.pokemon.stats.defense if move.damage_class_id == 2 else defender_ctx.pokemon.stats.sp_defense
        return atk_stat / max(1, def_stat)

    def _calculate_move_score(self, attacker_ctx: BattleContext, defender_ctx: BattleContext,
                              move: BattleMoveInfo, is_simulation: bool = False) -> float:
        eff = self.calculate_type_effectiveness([move.type_name], defender_ctx.types)
        stab = 1.5 if move.type_name in attacker_ctx.types else 1.0

        # 缓存计算结果到 move 对象 (副作用，但在实战中是有益的)
        move.type_effectiveness = eff
        move.stab_bonus = stab

        atk_stat = attacker_ctx.pokemon.stats.attack if move.damage_class_id == 2 else attacker_ctx.pokemon.stats.sp_attack
        def_stat = defender_ctx.pokemon.stats.defense if move.damage_class_id == 2 else defender_ctx.pokemon.stats.sp_defense

        atk_def_ratio = atk_stat / max(1, def_stat)
        score = move.power * (move.accuracy / 100.0) * eff * stab * atk_def_ratio

        if not is_simulation:
            logger.info(
                f"评分计算详情 - {move.move_name}: "
                f"基础伤害({move.power}) * 命中率({move.accuracy/100.0:.2f}) * "
                f"克制({eff}) * STAB({stab}) * 攻防比({atk_def_ratio:.2f}) = {score:.2f}"
            )

        return score

    def _calculate_damage_core(self, attacker_ctx: BattleContext, defender_ctx: BattleContext, move: BattleMoveInfo) -> \
    Tuple[int, Dict[str, Any]]:
        """统一的核心伤害计算逻辑"""
        # 命中判定
        if random.random() * 100 > move.accuracy:
            return 0, {"missed": True, "type_effectiveness": 1.0, "is_crit": False}

        atk_stat = attacker_ctx.pokemon.stats.attack if move.damage_class_id == 2 else attacker_ctx.pokemon.stats.sp_attack
        def_stat = defender_ctx.pokemon.stats.defense if move.damage_class_id == 2 else defender_ctx.pokemon.stats.sp_defense
        level = attacker_ctx.pokemon.level

        base_damage = ((2 * level / 5 + 2) * move.power * atk_stat / max(1, def_stat)) / 50 + 2

        is_crit = random.random() < self.CRIT_RATE
        crit_multiplier = 1.5 if is_crit else 1.0
        random_multiplier = random.uniform(0.85, 1.0)

        # 确保系数存在
        if move.type_effectiveness == 1.0 and move.move_id != 0 and move.type_name:
            move.type_effectiveness = self.calculate_type_effectiveness([move.type_name], defender_ctx.types)
        if move.stab_bonus == 1.0 and move.type_name in attacker_ctx.types:
            move.stab_bonus = 1.5

        final_damage = base_damage * move.type_effectiveness * move.stab_bonus * crit_multiplier * random_multiplier

        return int(final_damage), {
            "missed": False,
            "type_effectiveness": move.type_effectiveness,
            "is_crit": is_crit,
            "stab_bonus": move.stab_bonus
        }

    def resolve_damage(self, attacker_ctx: BattleContext, defender_ctx: BattleContext, move: BattleMoveInfo) -> int:
        dmg, _ = self._calculate_damage_core(attacker_ctx, defender_ctx, move)
        return dmg

    def calculate_damage_with_effects(self, attacker_ctx: BattleContext, defender_ctx: BattleContext,
                                      move: BattleMoveInfo) -> Tuple[int, Dict[str, any]]:
        return self._calculate_damage_core(attacker_ctx, defender_ctx, move)

    def execute_real_battle(self, user_ctx: BattleContext, wild_ctx: BattleContext) -> Tuple[str, List[str], int]:
        """执行实战，生成详细日志"""
        log_lines = [
            f"战斗开始！{user_ctx.pokemon.name} (Lv.{user_ctx.pokemon.level}) VS {wild_ctx.pokemon.name} (Lv.{wild_ctx.pokemon.level})\n\n",
            f"{user_ctx.pokemon.name} HP: {user_ctx.current_hp}, {wild_ctx.pokemon.name} HP: {wild_ctx.current_hp}\n\n"
        ]

        turn = 0
        max_turns = 50
        winner = None
        while user_ctx.current_hp > 0 and wild_ctx.current_hp > 0 and turn < max_turns:
            turn += 1
            log_lines.append(f"--- 第 {turn} 回合 ---\n\n")

            u_move = self.get_best_move_from_context(user_ctx, wild_ctx)
            w_move = self.get_best_move_from_context(wild_ctx, user_ctx)

            user_first = self._is_user_first(user_ctx, wild_ctx, u_move, w_move)

            first_unit, second_unit = (user_ctx, u_move), (wild_ctx, w_move)
            if not user_first:
                first_unit, second_unit = second_unit, first_unit

            # 执行先手
            if self._process_turn_action(first_unit[0], second_unit[0], first_unit[1], log_lines):
                winner = "user" if user_first else "wild"  # 对手倒下
                break  # 战斗结束
            if first_unit[0].current_hp <= 0:  # 检查反伤自杀
                winner = "wild" if user_first else "user"
                break

            # 执行后手
            if self._process_turn_action(second_unit[0], first_unit[0], second_unit[1], log_lines):
                winner = "wild" if user_first else "user"
                break
            if second_unit[0].current_hp <= 0:  # 检查反伤自杀
                winner = "user" if user_first else "wild"
                break

            log_lines.append(
                f"剩余HP - {user_ctx.pokemon.name}: {max(0, user_ctx.current_hp)}, {wild_ctx.pokemon.name}: {max(0, wild_ctx.current_hp)}\n\n")

        if not winner:
            result = "fail"
            log_lines.append("战斗超时，强制结束。\n\n")
        else:
            result = "win" if winner == "user" else "fail"
        return result, log_lines, wild_ctx.current_hp

    def _process_turn_action(self, attacker: BattleContext, defender: BattleContext, move: BattleMoveInfo,
                             logs: List[str]) -> bool:
        """
        处理单次回合行动。
        返回 True 表示由于此次攻击对手倒下（战斗结束）。
        """
        is_struggle = (move.move_id == self.STRUGGLE_MOVE_ID)

        # 扣除 PP
        if not is_struggle and move.current_pp > 0:
            move.current_pp -= 1

        # 变化技能处理
        if move.damage_class_id == 1:
            logs.append(f"{attacker.pokemon.name} 使用了 {move.move_name}！PP: {move.current_pp}/{move.max_pp}\n\n")
            return False  # 变化技暂无伤害，不会导致对手倒下

        # 攻击技能处理
        dmg, effects = self._calculate_damage_core(attacker, defender, move)
        defender.current_hp -= dmg

        desc = f"{attacker.pokemon.name} 使用了 {move.move_name}！"
        if is_struggle:
            desc = f"{attacker.pokemon.name} 使用了挣扎！（PP耗尽）"
        logs.append(f"{desc} 造成 {dmg} 点伤害。PP: {move.current_pp}/{move.max_pp}\n\n")

        if effects["missed"]:
            logs.append("没有击中目标！\n\n")
        else:
            if effects["is_crit"]: logs.append("击中要害！\n\n")
            eff = effects["type_effectiveness"]
            if eff > 1.0:
                logs.append("效果绝佳！\n\n")
            elif eff == 0.0:
                logs.append("似乎没有效果！\n\n")
            elif eff < 1.0:
                logs.append("效果不佳！\n\n")

        # 挣扎反伤
        if is_struggle:
            recoil = max(1, attacker.pokemon.stats.hp // 4)
            attacker.current_hp -= recoil
            logs.append(f"{attacker.pokemon.name} 因挣扎受到 {recoil} 点反作用伤害！\n\n")

        if defender.current_hp <= 0:
            logs.append(f"{defender.pokemon.name} 倒下了！\n\n")
            return True

        return False

    def calculate_battle_win_rate(self, user_ctx: BattleContext, wild_ctx: BattleContext, simulations: int = 100) -> \
    Tuple[float, float]:
        """优化版蒙特卡洛模拟：减少对象创建，仅追踪整数PP"""
        user_wins = 0

        # 提取速度和初始HP，避免属性查找开销
        u_speed = user_ctx.pokemon.stats.speed
        w_speed = wild_ctx.pokemon.stats.speed
        u_hp_start = user_ctx.current_hp
        w_hp_start = wild_ctx.current_hp

        # 提取 moves 的初始 PP 列表
        u_pp_start = [m.current_pp for m in user_ctx.moves]
        w_pp_start = [m.current_pp for m in wild_ctx.moves]

        # 缓存挣扎对象
        struggle = self._get_struggle_move()

        for _ in range(simulations):
            cur_u_hp = u_hp_start
            cur_w_hp = w_hp_start

            # 使用列表切片快速复制 PP 状态
            cur_u_pps = u_pp_start[:]
            cur_w_pps = w_pp_start[:]

            turn = 0
            while cur_u_hp > 0 and cur_w_hp > 0 and turn < 15:  # 降低模拟回合上限以提升性能
                turn += 1

                # 获取招式 (传递 PP 列表)
                u_move = self.get_best_move_from_context(user_ctx, wild_ctx, cur_u_pps)
                w_move = self.get_best_move_from_context(wild_ctx, user_ctx, cur_w_pps)

                # 简单判定先手
                user_first = True
                if u_move.priority < w_move.priority:
                    user_first = False
                elif u_move.priority == w_move.priority:
                    if u_speed < w_speed:
                        user_first = False
                    elif u_speed == w_speed and random.random() < 0.5:
                        user_first = False

                # 模拟回合逻辑
                first_move, first_attacker, first_defender, first_pps = (u_move, user_ctx, wild_ctx,
                                                                         cur_u_pps) if user_first else (w_move,
                                                                                                        wild_ctx,
                                                                                                        user_ctx,
                                                                                                        cur_w_pps)
                second_move, second_attacker, second_defender, second_pps = (w_move, wild_ctx, user_ctx,
                                                                             cur_w_pps) if user_first else (u_move,
                                                                                                            user_ctx,
                                                                                                            wild_ctx,
                                                                                                            cur_u_pps)

                # Action 1
                idx = -1
                if first_move.move_id != self.STRUGGLE_MOVE_ID:
                    # 找到对应的 index 扣 PP (这里假设 moves 顺序不变)
                    try:
                        idx = first_attacker.moves.index(first_move)
                        if first_pps[idx] > 0: first_pps[idx] -= 1
                    except ValueError:
                        pass

                dmg, _ = self._calculate_damage_core(first_attacker, first_defender, first_move)
                if user_first:
                    cur_w_hp -= dmg
                else:
                    cur_u_hp -= dmg

                if cur_u_hp <= 0 or cur_w_hp <= 0: break

                # Action 2
                if second_move.move_id != self.STRUGGLE_MOVE_ID:
                    try:
                        idx = second_attacker.moves.index(second_move)
                        if second_pps[idx] > 0: second_pps[idx] -= 1
                    except ValueError:
                        pass

                dmg, _ = self._calculate_damage_core(second_attacker, second_defender, second_move)
                if user_first:
                    cur_u_hp -= dmg
                else:
                    cur_w_hp -= dmg

            if cur_u_hp > 0:
                user_wins += 1

        win_rate = (user_wins / simulations) * 100
        return round(win_rate, 1), round(100 - win_rate, 1)

    def calculate_type_effectiveness(self, attacker_types: List[str], defender_types: List[str]) -> float:
        """计算属性克制系数"""
        effectiveness = 1.0
        for atk_type in attacker_types:
            atk_dict = self.TYPE_CHART.get(atk_type.lower())
            if not atk_dict: continue

            for def_type in defender_types:
                effectiveness *= atk_dict.get(def_type.lower(), 1.0)
        return effectiveness

    def _is_user_first(self, user_ctx: BattleContext, wild_ctx: BattleContext, u_move: BattleMoveInfo,
                       w_move: BattleMoveInfo) -> bool:
        u_prio, w_prio = u_move.priority, w_move.priority
        if u_prio != w_prio:
            return u_prio > w_prio

        u_spd, w_spd = user_ctx.pokemon.stats.speed, wild_ctx.pokemon.stats.speed
        if u_spd != w_spd:
            return u_spd > w_spd

        return random.random() < 0.5

    def calculate_catch_success_rate(self, user_id: str, wild_pokemon: WildPokemonInfo, item_id: str) -> Dict[str, Any]:
        """计算捕捉成功率"""
        user_items: UserItems = self.user_item_repo.get_user_items(user_id)
        pokeball_item = None

        target_item_id = item_id if item_id else None
        for item in user_items.items:
            is_ball = int(item.category_id) == 34 or int(item.category_id) == 33
            if is_ball and item.quantity > 0:
                if target_item_id is None or item.item_id == target_item_id:
                    pokeball_item = item
                    break

        if not pokeball_item:
            msg = f"❌ 找不到ID为 {item_id} 的精灵球" if item_id else AnswerEnum.USER_POKEBALLS_EMPTY.value
            return {"success": False, "message": msg}

        ball_map = {'超级球': 1.5, '高级球': 2.0, '大师球': 255.0}
        ball_multiplier = ball_map.get(pokeball_item.name_zh, 1.0)

        max_hp = wild_pokemon.stats.hp
        # 简单模拟当前血量 (若有战斗上下文应传入实际血量)
        temp_current_hp = int(random.gauss(max_hp * 0.75, max_hp * 0.25))
        current_hp = max(1, min(max_hp, temp_current_hp))

        base_capture_rate = int(self.pokemon_repo.get_pokemon_capture_rate(wild_pokemon.species_id))
        catch_value = int(((3 * max_hp - 2 * current_hp) * base_capture_rate * ball_multiplier) // (3 * max_hp))
        catch_value = min(catch_value, 255)
        success_rate = catch_value / 256.0

        return {
            "success": True,
            "message": f"判定值为{catch_value}，捕捉成功率为{round(success_rate * 100, 2)}%",
            "data": {
                "catch_value": catch_value,
                "success_rate": round(success_rate, 2),
                "pokeball_item": pokeball_item,
            }
        }

    def _handle_battle_experience(self, user_id: str, result_str: str, wild_pokemon: WildPokemonInfo,
                                  battle_log: List[Dict] = None):
        """处理战斗后的经验分配"""
        if not self.exp_service or result_str != "success":
            return {
                "pokemon_exp": {"success": True, "exp_gained": 0, "message": AnswerEnum.BATTLE_FAILURE_NO_EXP.value},
                "ev_gained": {"hp_ev": 0, "attack_ev": 0, "defense_ev": 0, "sp_attack_ev": 0, "sp_defense_ev": 0,
                              "speed_ev": 0},
                "team_pokemon_results": []
            }

        base_exp_gained = self.exp_service.calculate_pokemon_exp_gain(
            wild_pokemon_id=wild_pokemon.species_id,
            wild_pokemon_level=wild_pokemon.level,
            battle_result=result_str
        )
        ev_gained = self.exp_service.calculate_pokemon_ev_gain(
            wild_pokemon_species_id=wild_pokemon.species_id,
            battle_result=result_str
        )

        user_team = self.team_repo.get_user_team(user_id)
        team_results = []
        primary_result = {}

        if user_team and user_team.team_pokemon_ids:
            battle_participants = set()
            battle_deaths = set()

            if battle_log:
                for b_info in battle_log:
                    pid = b_info.get("pokemon_id")
                    battle_participants.add(pid)
                    if b_info.get("result") == "fail":
                        battle_deaths.add(pid)

            for pokemon_id in user_team.team_pokemon_ids:
                pid = int(pokemon_id)
                if pid in battle_deaths:
                    continue  # 死亡无经验

                is_participant = pid in battle_participants
                p_exp = base_exp_gained if is_participant else (base_exp_gained // 2)
                msg = "获得全部经验" if is_participant else "获得一半经验"

                res = self.exp_service.update_pokemon_after_battle(user_id, pid, p_exp, ev_gained)
                res.update({"message": msg, "original_base_exp": base_exp_gained, "applied_exp": p_exp})
                team_results.append(res)

                # 记录首发宠物的经验结果
                if not primary_result and is_participant:
                    primary_result = res

        if not primary_result and team_results:
            primary_result = team_results[0]

        return {
            "pokemon_exp": primary_result,
            "ev_gained": ev_gained,
            "team_pokemon_results": team_results
        }

    def _update_encounter_log(self, user_id: str, wild_pokemon_id: int, result_str: str):
        recent_encounters = self.user_pokemon_repo.get_user_encounters(user_id, limit=5)
        for encounter in recent_encounters:
            if encounter.wild_pokemon_id == wild_pokemon_id and encounter.is_battled == 0:
                outcome = "win" if result_str == "success" else "lose"
                self.user_pokemon_repo.update_encounter_log(encounter.id, is_battled=1, battle_result=outcome)
                break

    def _format_pokemon_summary(self, poke_info: Union[UserPokemonInfo, WildPokemonInfo], is_wild: bool = False):
        if not poke_info:
            return {"name": "Unknown", "hp": 0}
        return {
            "name": poke_info.name,
            "species": getattr(poke_info, 'species_id', 0),
            "level": poke_info.level,
            "hp": poke_info.stats.hp,
            "attack": poke_info.stats.attack,
            "defense": poke_info.stats.defense,
            "speed": poke_info.stats.speed
        }

    def get_battle_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        return self.battle_repo.get_battle_log_by_id(log_id)

    def adventure_with_trainer(self, user_id: str, location_id: int) -> BaseResult:
        if not self.trainer_service:
            return BaseResult(success=False, message="训练家服务未初始化")

        user_team_data = self.team_repo.get_user_team(user_id)
        if not user_team_data or not user_team_data.team_pokemon_ids:
            return BaseResult(success=False, message=AnswerEnum.USER_TEAM_NOT_SET.value)

        trainer = self.trainer_service.get_random_trainer_at_location(location_id, user_id)
        if not trainer:
            return BaseResult(success=True, message="没有遇到训练家", data=None)

        battle_trainer = self.trainer_service.get_trainer_with_pokemon(trainer.id)
        if not battle_trainer:
            return BaseResult(success=False, message="获取训练家宝可梦失败")

        self.user_pokemon_repo.set_user_current_trainer_encounter(user_id, trainer.id)
        return BaseResult(success=True, message="遇到了训练家！", data=battle_trainer)

    def start_trainer_battle(self, user_id: str, battle_trainer: BattleTrainer, user_team_list: List[int]) -> \
    BaseResult[BattleResult]:
        """开始与训练家的战斗"""
        if not user_team_list:
            return BaseResult(success=False, message=AnswerEnum.USER_TEAM_NOT_SET.value)
        if not battle_trainer.pokemon_list:
            return BaseResult(success=False, message="训练家没有宝可梦")

        # 预加载数据
        trainer_pokes = battle_trainer.pokemon_list
        trainer_contexts = [self._create_battle_context(p, False) for p in trainer_pokes]

        user_contexts = []
        for pid in user_team_list:
            u_info = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pid)
            if u_info:
                user_contexts.append(self._create_battle_context(u_info, True))

        u_idx = 0
        t_idx = 0
        battle_log = []
        all_u_wins, all_t_wins = [], []
        battle_result_str = "fail"

        # 记录遭遇
        self.trainer_service.record_trainer_encounter(user_id, battle_trainer.trainer.id)

        while u_idx < len(user_contexts) and t_idx < len(trainer_contexts):
            u_ctx = user_contexts[u_idx]
            t_ctx = trainer_contexts[t_idx]

            # 模拟胜率 (不改变当前 HP)
            sim_u_hp, sim_t_hp = u_ctx.current_hp, t_ctx.current_hp
            u_win, t_win = self.calculate_battle_win_rate(u_ctx, t_ctx)
            u_ctx.current_hp, t_ctx.current_hp = sim_u_hp, sim_t_hp

            all_u_wins.append(u_win)
            all_t_wins.append(t_win)

            # 实战
            outcome, details, rem_t_hp = self.execute_real_battle(u_ctx, t_ctx)

            # 记录训练家剩余血量
            t_ctx.current_hp = max(0, rem_t_hp)

            battle_log.append({
                "pokemon_id": u_ctx.pokemon.id,
                "pokemon_name": u_ctx.pokemon.name,
                "species_name": u_ctx.pokemon.species_id,
                "level": u_ctx.pokemon.level,
                "trainer_pokemon_name": t_ctx.pokemon.name,
                "trainer_pokemon_level": t_ctx.pokemon.level,
                "win_rate": u_win,
                "result": outcome,
                "details": details
            })

            if outcome == "win":
                t_idx += 1  # 击败对方一只，对方下一只上场
            else:
                u_idx += 1  # 我方战败，下一只上场

        if t_idx >= len(trainer_contexts):
            battle_result_str = "success"

        # 统计平均胜率
        f_u_rate = round(sum(all_u_wins) / len(all_u_wins), 2) if all_u_wins else 0
        f_t_rate = round(sum(all_t_wins) / len(all_t_wins), 2) if all_t_wins else 0

        # 保存日志
        log_id = 0
        if self.battle_repo:
            t_name = battle_trainer.trainer.name or '未知训练家'
            log_id = self.battle_repo.save_battle_log(user_id, f"训练家 {t_name}", battle_log, battle_result_str)

        # 奖励计算
        last_poke_level = trainer_pokes[-1].level
        exp_details = self._handle_trainer_battle_experience(user_id, battle_result_str, battle_trainer, battle_log,
                                                             last_poke_level)

        money_reward = 0
        user_exp_result = None

        if battle_result_str == "success":
            rewards = self.trainer_service.calculate_trainer_battle_rewards(battle_trainer.trainer, last_poke_level)
            money_reward = rewards["money_reward"]
            self.trainer_service.handle_trainer_battle_win(user_id, battle_trainer.trainer.id, money_reward)
            user_exp_result = self.exp_service.add_exp_for_defeating_npc_trainer(user_id,
                                                                                 battle_trainer.trainer.base_payout)

        final_u_info = user_contexts[min(u_idx, len(user_contexts) - 1)].pokemon if user_contexts else None

        return BaseResult(
            success=True,
            message=AnswerEnum.BATTLE_SUCCESS.value if battle_result_str == "success" else "训练家对战失败",
            data=BattleResult(
                user_pokemon=self._format_pokemon_summary(final_u_info),
                wild_pokemon=self._format_pokemon_summary(trainer_pokes[-1], is_wild=True),
                win_rates={"user_win_rate": f_u_rate, "wild_win_rate": f_t_rate},
                result=battle_result_str,
                exp_details=exp_details,
                battle_log=battle_log,
                log_id=log_id,
                is_trainer_battle=True,
                money_reward=money_reward,
                user_battle_exp_result=user_exp_result
            )
        )


    def _handle_trainer_battle_experience(self, user_id: str, result_str: str, battle_trainer: BattleTrainer, battle_log: List[Dict], last_pokemon_level: int):
        """处理训练家战斗后的经验分配（训练家对战经验是野生宝可梦的1.5倍）"""
        if not self.exp_service or result_str != "success":
            return {
                "pokemon_exp": {"success": False, "exp_gained": 0, "message": AnswerEnum.BATTLE_FAILURE_NO_EXP.value},
                "ev_gained": {"hp_ev": 0, "attack_ev": 0, "defense_ev": 0, "sp_attack_ev": 0, "sp_defense_ev": 0, "speed_ev": 0},
                "team_pokemon_results": [],
                "trainer_battle": True
            }

        # 计算基础经验值并应用1.5倍加成
        base_exp_gained = self.exp_service.calculate_pokemon_exp_gain(
            wild_pokemon_id=battle_trainer.pokemon_list[0].species_id,  # 使用第一只宝可梦的种类
            wild_pokemon_level=last_pokemon_level,  # 使用王牌宝可梦等级
            battle_result=result_str
        )

        # 训练家对战经验加成
        trainer_exp_multiplier = 1.5
        base_exp_gained = int(base_exp_gained * trainer_exp_multiplier)

        # 计算EV奖励
        ev_gained = self.exp_service.calculate_pokemon_ev_gain(
            wild_pokemon_species_id=battle_trainer.pokemon_list[0].species_id,
            battle_result=result_str
        )

        user_team = self.team_repo.get_user_team(user_id)
        team_results = []
        if user_team and user_team.team_pokemon_ids:
            # 根据战斗日志确定每只宝可梦的状态：出场、未出场或死亡
            team_pokemon_ids = user_team.team_pokemon_ids
            battle_participants = set()  # 出场的宝可梦ID
            battle_deaths = set()  # 死亡的宝可梦ID

            if battle_log:
                for battle_info in battle_log:
                    pokemon_id = battle_info.get("pokemon_id")
                    battle_participants.add(pokemon_id)

                    # 检查这只宝可梦是否在战斗中死亡
                    if battle_info.get("result") == "fail":
                        battle_deaths.add(pokemon_id)

            # 计算每只宝可梦的经验值
            for pokemon_id in team_pokemon_ids:
                pokemon_id = int(pokemon_id)  # 确保是整数
                current_pokemon = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)

                if not current_pokemon:
                    continue

                # 确定该宝可梦的状态和对应的经验值
                if pokemon_id in battle_deaths:
                    # 死亡的宝可梦不获得经验
                    pokemon_exp = 0
                    exp_message = "宝可梦在战斗中死亡，未获得经验"
                elif pokemon_id in battle_participants:
                    # 出场的宝可梦获得100%经验
                    pokemon_exp = base_exp_gained
                    exp_message = f"宝可梦参与训练家对战，获得{base_exp_gained}经验"
                else:
                    # 未出场的宝可梦获得50%经验
                    pokemon_exp = base_exp_gained // 2
                    exp_message = f"宝可梦未参与训练家对战，获得{base_exp_gained // 2}经验"

                # 更新单个宝可梦的经验
                pokemon_result = self.exp_service.update_pokemon_after_battle(
                    user_id, pokemon_id, pokemon_exp, ev_gained
                )
                pokemon_result["message"] = exp_message
                pokemon_result["original_base_exp"] = base_exp_gained
                pokemon_result["applied_exp"] = pokemon_exp  # 添加实际应用的经验值
                pokemon_result["trainer_battle_exp"] = True  # 标识这是训练家对战经验

                team_results.append(pokemon_result)

        # 返回第一个参与战斗的宝可梦的结果作为主结果
        primary_result = {}
        if battle_log and team_results:
            first_battle_pokemon_id = battle_log[0].get("pokemon_id") if battle_log else None
            for result in team_results:
                if result.get("pokemon_id") == first_battle_pokemon_id:
                    primary_result = result
                    break

        if not primary_result and team_results:
            primary_result = team_results[0]

        return {
            "pokemon_exp": primary_result,
            "ev_gained": ev_gained,
            "team_pokemon_results": team_results,
            "trainer_battle": True
        }