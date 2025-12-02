import math
import random
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass, field

from . import user_pokemon_service
from .exp_service import ExpService
from .pokemon_service import PokemonService
from ..models.common_models import BaseResult
from ...interface.response.answer_enum import AnswerEnum
from ..models.pokemon_models import (
    WildPokemonInfo, PokemonStats, PokemonIVs, PokemonEVs,
    UserPokemonInfo, WildPokemonEncounterLog, PokemonMoves
)
from ..models.user_models import UserTeam, UserItems
from ...infrastructure.repositories.abstract_repository import (
    AbstractAdventureRepository, AbstractPokemonRepository, AbstractUserRepository, AbstractTeamRepository,
    AbstractUserPokemonRepository, AbstractBattleRepository, AbstractUserItemRepository
)
from ..models.adventure_models import AdventureResult, LocationInfo, BattleResult, BattleMoveInfo
from astrbot.api import logger


# 定义一个简易的战斗上下文，用于在模拟和实战中传递预加载的数据
@dataclass
class BattleContext:
    pokemon: Union[UserPokemonInfo, WildPokemonInfo]
    moves: List[BattleMoveInfo]
    types: List[str]
    current_hp: int
    is_user: bool


class AdventureService:
    """冒险区域相关的业务逻辑服务"""

    # ----------------------
    # 宝可梦属性克制表（类常量）
    # ----------------------
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

    def adventure_in_location(self, user_id: str, location_id: int) -> BaseResult[AdventureResult]:
        """在指定区域进行冒险，随机刷新一只野生宝可梦"""
        # 1. 获取区域信息
        location = self.adventure_repo.get_location_by_id(location_id)
        if not location:
            return BaseResult(success=False,
                              message=AnswerEnum.ADVENTURE_LOCATION_NOT_FOUND.value.format(location_id=location_id))

        # 2. 获取该区域的宝可梦列表
        location_pokemon_list = self.adventure_repo.get_location_pokemon_by_location_id(location_id)
        if not location_pokemon_list:
            return BaseResult(success=False, message=AnswerEnum.ADVENTURE_LOCATION_NO_POKEMON.value.format(
                location_name=location.name))

        # 3. 权重随机选择宝可梦 (优化：使用 random.choices)
        selected_location_pokemon = random.choices(
            location_pokemon_list,
            weights=[ap.encounter_rate for ap in location_pokemon_list],
            k=1
        )[0]

        # 4. 生成随机等级
        wild_pokemon_level = random.randint(selected_location_pokemon.min_level, selected_location_pokemon.max_level)

        # 5. 创建野生宝可梦
        wild_pokemon_result = self.pokemon_service.create_single_pokemon(
            species_id=selected_location_pokemon.pokemon_species_id,
            max_level=wild_pokemon_level,
            min_level=wild_pokemon_level
        )
        if not wild_pokemon_result.success:
            return BaseResult(success=False, message=wild_pokemon_result.message)

        wild_pokemon = wild_pokemon_result.data
        # 构建 info 对象 (属性拷贝)
        wild_pokemon_info = WildPokemonInfo(
            id=0,
            species_id=wild_pokemon.base_pokemon.id,
            name=wild_pokemon.base_pokemon.name_zh,
            gender=wild_pokemon.gender,
            level=wild_pokemon_level,
            exp=wild_pokemon.exp,
            stats=PokemonStats(**wild_pokemon.stats.__dict__),  # 假设是dataclass或dict兼容
            ivs=PokemonIVs(**wild_pokemon.ivs.__dict__),
            evs=PokemonEVs(**wild_pokemon.evs.__dict__),
            moves=PokemonMoves(
                move1_id=wild_pokemon.moves.move1_id,
                move2_id=wild_pokemon.moves.move2_id,
                move3_id=wild_pokemon.moves.move3_id,
                move4_id=wild_pokemon.moves.move4_id,
            ),
            nature_id=wild_pokemon.nature_id,
        )

        wild_pokemon_id = self.pokemon_repo.add_wild_pokemon(wild_pokemon_info)

        self.user_pokemon_repo.add_user_encountered_wild_pokemon(
            user_id=user_id,
            wild_pokemon_id=wild_pokemon_id,
            location_id=location.id,
            encounter_rate=selected_location_pokemon.encounter_rate,
        )
        return BaseResult(
            success=True,
            message=AnswerEnum.ADVENTURE_SUCCESS.value,
            data=AdventureResult(
                wild_pokemon=wild_pokemon_info,
                location=LocationInfo(id=location.id, name=location.name),
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

        # 预加载野生宝可梦的 Context (包含招式数据，避免循环内查询数据库)
        wild_ctx = self._create_battle_context(wild_pokemon_info, is_user=False)

        current_pokemon_index = 0
        battle_result_str = "fail"
        final_user_pokemon_info = None
        all_user_win_rates = []
        all_wild_win_rates = []
        battle_log = []
        log_id = 0

        while current_pokemon_index < len(user_team_list):
            user_pokemon_id = user_team_list[current_pokemon_index]
            user_pokemon_info = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, user_pokemon_id)

            if not user_pokemon_info:
                current_pokemon_index += 1
                continue

            # 预加载玩家宝可梦的 Context
            user_ctx = self._create_battle_context(user_pokemon_info, is_user=True)
            final_user_pokemon_info = user_pokemon_info

            # 1. 计算胜率 (使用预加载数据的Context，大幅提升性能)
            # 重置HP用于模拟
            user_ctx.current_hp = user_pokemon_info.stats.hp
            wild_ctx.current_hp = wild_pokemon_info.stats.hp
            user_win_rate, wild_win_rate = self.calculate_battle_win_rate(user_ctx, wild_ctx)

            all_user_win_rates.append(user_win_rate)
            all_wild_win_rates.append(wild_win_rate)

            # 2. 执行实际战斗
            # 确保实战使用当前的HP状态 (如果野生怪之前受过伤)
            user_ctx.current_hp = user_pokemon_info.stats.hp
            wild_ctx.current_hp = wild_pokemon_info.stats.hp  # 实战开始，重置为当前实际值

            battle_outcome, battle_log_data, remaining_wild_hp = self.execute_real_battle(user_ctx, wild_ctx)

            # 更新野生宝可梦数据对象，以便下一轮（如果输了）继承血量
            wild_pokemon_info.stats.hp = max(0, remaining_wild_hp)
            wild_ctx.current_hp = wild_pokemon_info.stats.hp  # 更新 Context

            battle_log.append({
                "pokemon_id": user_pokemon_info.id,
                "pokemon_name": user_pokemon_info.name,
                "species_name": user_pokemon_info.species_id,
                "level": user_pokemon_info.level,
                "win_rate": user_win_rate,
                "result": battle_outcome,
                "details": battle_log_data
            })

            if battle_outcome == "win":
                battle_result_str = "success"
                break
            else:
                current_pokemon_index += 1

        # 计算最终显示的胜率（如果赢了显示当前只，输了显示平均）
        final_u_rate, final_w_rate = 0.0, 100.0
        if battle_result_str == "success":
            final_u_rate, final_w_rate = all_user_win_rates[-1], all_wild_win_rates[-1]
        elif all_user_win_rates:
            final_u_rate = round(sum(all_user_win_rates) / len(all_user_win_rates), 2)
            final_w_rate = round(sum(all_wild_win_rates) / len(all_wild_win_rates), 2)

        # 保存日志
        if self.battle_repo:
            log_id = self.battle_repo.save_battle_log(
                user_id=user_id,
                target_name=wild_pokemon_info.name,
                log_data=battle_log,
                result=battle_result_str
            )

        # 处理经验值
        exp_details = self._handle_battle_experience(user_id, battle_result_str, wild_pokemon_info)

        # 更新图鉴/遭遇日志
        self._update_encounter_log(user_id, wild_pokemon_info.id, battle_result_str)

        return BaseResult(
            success=True,
            message=AnswerEnum.BATTLE_SUCCESS.value,
            data=BattleResult(
                user_pokemon=self._format_pokemon_summary(final_user_pokemon_info),
                wild_pokemon=self._format_pokemon_summary(wild_pokemon_info, is_wild=True),
                win_rates={"user_win_rate": final_u_rate, "wild_win_rate": final_w_rate},
                result=battle_result_str,
                exp_details=exp_details,
                battle_log=battle_log,
                log_id=log_id
            )
        )

    def _create_battle_context(self, pokemon_info: Union[UserPokemonInfo, WildPokemonInfo],
                               is_user: bool) -> BattleContext:
        """辅助方法：创建战斗上下文，预加载招式和属性"""
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
        """批量加载宝可梦的所有招式详情，避免循环查库"""
        move_ids = [pokemon.moves.move1_id, pokemon.moves.move2_id, pokemon.moves.move3_id, pokemon.moves.move4_id]
        valid_ids = [m for m in move_ids if m and m > 0]

        loaded_moves = []
        if self.move_repo:
            for mid in valid_ids:
                m_data = self.move_repo.get_move_by_id(mid)
                if m_data:
                    loaded_moves.append(BattleMoveInfo(
                        power=m_data.get('power', 0) or 0,
                        accuracy=m_data.get('accuracy', 100) or 100,
                        type_name=m_data.get('type_name', 'normal'),
                        damage_class_id=m_data.get('damage_class_id', 2),
                        priority=m_data.get('priority', 0),
                        type_effectiveness=1.0,
                        stab_bonus=1.0,
                        move_id=mid,
                        move_name=m_data.get('name_zh', 'Unknown Move')
                    ))
        return loaded_moves

    def get_best_move_from_context(self, attacker_ctx: BattleContext, defender_ctx: BattleContext) -> BattleMoveInfo:
        """
        基于预加载的 Context 选择最佳招式 (纯内存计算)
        """
        default_move = BattleMoveInfo(
            power=50, accuracy=100.0, type_name='normal',
            damage_class_id=2, priority=0, type_effectiveness=1.0, stab_bonus=1.0, move_id=0, move_name="默认招式"
        )

        if not attacker_ctx.moves:
            return default_move

        best_move = None
        max_score = -1.0

        for move in attacker_ctx.moves:
            if move.power == 0: continue  # 暂时忽略变化类招式

            score = self._get_move_damage_score(attacker_ctx, defender_ctx, move)
            if score > max_score:
                max_score = score
                best_move = move

        return best_move if best_move else default_move

    def _get_move_damage_score(self, attacker_ctx: BattleContext, defender_ctx: BattleContext,
                               move: BattleMoveInfo) -> float:
        """计算招式评分 (用于AI决策)"""
        # 1. 属性克制
        eff = self.calculate_type_effectiveness([move.type_name], defender_ctx.types)
        # 2. 本系加成 (STAB)
        stab = 1.5 if move.type_name in attacker_ctx.types else 1.0

        # 3. 攻防数值
        atk_stat = attacker_ctx.pokemon.stats.attack if move.damage_class_id == 2 else attacker_ctx.pokemon.stats.sp_attack
        def_stat = defender_ctx.pokemon.stats.defense if move.damage_class_id == 2 else defender_ctx.pokemon.stats.sp_defense

        # 临时保存计算好的系数到 move 对象中，供 resolve_damage 使用 (避免重复计算)
        move.type_effectiveness = eff
        move.stab_bonus = stab

        # 评分公式
        return move.power * (move.accuracy / 100.0) * eff * stab * (atk_stat / max(1, def_stat))

    def resolve_damage(self, attacker_ctx: BattleContext, defender_ctx: BattleContext, move: BattleMoveInfo) -> int:
        """计算实际伤害"""
        if random.random() * 100 > move.accuracy:
            return 0

        # 重新计算攻防，因为Context可能变了? 不，Context里的Pokemon Stats是不变的，Stat变化应在Context里维护
        # 这里简化处理，直接取 stats
        atk_stat = attacker_ctx.pokemon.stats.attack if move.damage_class_id == 2 else attacker_ctx.pokemon.stats.sp_attack
        def_stat = defender_ctx.pokemon.stats.defense if move.damage_class_id == 2 else defender_ctx.pokemon.stats.sp_defense

        level = attacker_ctx.pokemon.level

        # 基础伤害公式
        base_damage = ((2 * level / 5 + 2) * move.power * atk_stat / max(1, def_stat)) / 50 + 2

        # 随机波动
        is_crit = random.random() < 0.0625
        crit_multiplier = 1.5 if is_crit else 1.0
        random_multiplier = random.uniform(0.85, 1.0)

        # move.type_effectiveness 和 stab_bonus 已经在 get_best_move_from_context -> _get_move_damage_score 中计算并赋值了
        # 如果是随机招式，可能没赋值，这里做一个兜底
        if move.type_effectiveness == 1.0 and move.move_id != 0:
            move.type_effectiveness = self.calculate_type_effectiveness([move.type_name], defender_ctx.types)
            move.stab_bonus = 1.5 if move.type_name in attacker_ctx.types else 1.0

        final_damage = base_damage * move.type_effectiveness * move.stab_bonus * crit_multiplier * random_multiplier
        return int(final_damage)

    def execute_real_battle(self, user_ctx: BattleContext, wild_ctx: BattleContext) -> Tuple[str, List[str], int]:
        """执行带日志的战斗"""
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

            # 决定顺序
            user_first = self._is_user_first(user_ctx, wild_ctx, u_move, w_move)

            first_ctx, first_move = (user_ctx, u_move) if user_first else (wild_ctx, w_move)
            second_ctx, second_move = (wild_ctx, w_move) if user_first else (user_ctx, u_move)

            # 行动序列
            # 1. 先手攻击
            dmg1 = self.resolve_damage(first_ctx, second_ctx, first_move)
            second_ctx.current_hp -= dmg1
            log_lines.append(f"{first_ctx.pokemon.name} 使用了 {first_move.move_name}！造成 {dmg1} 点伤害。\n\n")

            if second_ctx.current_hp <= 0:
                log_lines.append(f"{second_ctx.pokemon.name} 倒下了！\n\n")
                winner = "user" if user_first else "wild"
                break

            # 2. 后手攻击
            dmg2 = self.resolve_damage(second_ctx, first_ctx, second_move)
            first_ctx.current_hp -= dmg2
            log_lines.append(f"{second_ctx.pokemon.name} 使用了 {second_move.move_name}！造成 {dmg2} 点伤害。\n\n")

            if first_ctx.current_hp <= 0:
                log_lines.append(f"{first_ctx.pokemon.name} 倒下了！\n\n")
                winner = "wild" if user_first else "user"
                break

            log_lines.append(
                f"剩余HP - {user_ctx.pokemon.name}: {max(0, user_ctx.current_hp)}, {wild_ctx.pokemon.name}: {max(0, wild_ctx.current_hp)}\n\n")

        result = "win" if winner == "user" else "fail"
        if not winner:
            log_lines.append("战斗超时，强制结束。\n\n")

        return result, log_lines, wild_ctx.current_hp

    def calculate_battle_win_rate(self, user_ctx: BattleContext, wild_ctx: BattleContext, simulations: int = 100) -> \
    Tuple[float, float]:
        """
        计算胜率 (蒙特卡洛模拟) - 极致优化版
        注意：传入的 ctx.current_hp 会在模拟中被修改，所以每次模拟前要重置，或者使用临时变量。
        这里我们在循环内使用局部变量跟踪HP。
        """
        user_wins = 0

        # 缓存频繁访问的属性
        u_speed = user_ctx.pokemon.stats.speed
        w_speed = wild_ctx.pokemon.stats.speed
        u_start_hp = user_ctx.current_hp
        w_start_hp = wild_ctx.current_hp

        # 预计算最佳招式 (简单AI假设每回合都用这招，进一步加速模拟)
        # 如果需要更精确的模拟（例如考虑随机性导致最佳招式变化），需把这步放回循环内
        # 这里为了性能，我们假设AI总是选择期望伤害最高的招式
        u_best_move_static = self.get_best_move_from_context(user_ctx, wild_ctx)
        w_best_move_static = self.get_best_move_from_context(wild_ctx, user_ctx)

        for _ in range(simulations):
            cur_u_hp = u_start_hp
            cur_w_hp = w_start_hp
            turn = 0

            while cur_u_hp > 0 and cur_w_hp > 0 and turn < 20:  # 减少模拟回合上限
                turn += 1

                # 若需要每回合重新决策招式，取消注释下面两行，注释掉循环外的 static 定义
                # u_move = self.get_best_move_from_context(user_ctx, wild_ctx)
                # w_move = self.get_best_move_from_context(wild_ctx, user_ctx)
                u_move = u_best_move_static
                w_move = w_best_move_static

                user_first = self._is_user_first_simple(u_speed, w_speed, u_move.priority, w_move.priority)

                if user_first:
                    # User attacks Wild
                    dmg = self.resolve_damage(user_ctx, wild_ctx, u_move)
                    cur_w_hp -= dmg
                    if cur_w_hp <= 0: break
                    # Wild attacks User
                    dmg = self.resolve_damage(wild_ctx, user_ctx, w_move)
                    cur_u_hp -= dmg
                else:
                    # Wild attacks User
                    dmg = self.resolve_damage(wild_ctx, user_ctx, w_move)
                    cur_u_hp -= dmg
                    if cur_u_hp <= 0: break
                    # User attacks Wild
                    dmg = self.resolve_damage(user_ctx, wild_ctx, u_move)
                    cur_w_hp -= dmg

            if cur_u_hp > 0:
                user_wins += 1

        win_rate = (user_wins / simulations) * 100
        return round(win_rate, 1), round(100 - win_rate, 1)

    def calculate_type_effectiveness(self, attacker_types: List[str], defender_types: List[str]) -> float:
        """计算属性克制系数"""
        effectiveness = 1.0
        for atk_type in attacker_types:
            atk = atk_type.lower()
            if atk in self.TYPE_CHART:
                for def_type in defender_types:
                    effectiveness *= self.TYPE_CHART[atk].get(def_type.lower(), 1.0)
        return effectiveness

    def _is_user_first(self, user_ctx: BattleContext, wild_ctx: BattleContext, u_move: BattleMoveInfo,
                       w_move: BattleMoveInfo) -> bool:
        return self._is_user_first_simple(
            user_ctx.pokemon.stats.speed,
            wild_ctx.pokemon.stats.speed,
            u_move.priority,
            w_move.priority
        )

    def _is_user_first_simple(self, u_speed, w_speed, u_prio, w_prio) -> bool:
        """简化版先手判定，仅依赖数值"""
        if u_prio > w_prio: return True
        if w_prio > u_prio: return False
        if u_speed > w_speed: return True
        if w_speed > u_speed: return False
        return random.random() < 0.5

    def calculate_catch_success_rate(self, user_id: str, wild_pokemon: WildPokemonInfo, item_id: str) -> Dict[str, Any]:
        """计算捕捉成功率"""
        user_items: UserItems = self.user_item_repo.get_user_items(user_id)
        pokeball_item = None

        # 查找精灵球
        target_item_id = item_id if item_id else None
        for item in user_items.items:
            is_ball = int(item.category_id) == 34
            if is_ball and item.quantity > 0:
                if target_item_id is None or item.item_id == target_item_id:
                    pokeball_item = item
                    break

        if not pokeball_item:
            msg = f"❌ 找不到ID为 {item_id} 的精灵球" if item_id else AnswerEnum.USER_POKEBALLS_EMPTY.value
            return {"success": False, "message": msg}

        # 倍率设置
        ball_map = {'超级球': 1.5, '高级球': 2.0, '大师球': 255.0}
        ball_multiplier = ball_map.get(pokeball_item.name_zh, 1.0)

        max_hp = wild_pokemon.stats.hp
        # 注意：这里逻辑保留原样（随机HP），如果是战斗后捕捉，应传入 remaining_hp
        temp_current_hp = int(random.gauss(max_hp * 0.75, max_hp * 0.25))
        current_hp = max(1, min(max_hp, temp_current_hp))  # 最小1血

        base_capture_rate = int(self.pokemon_repo.get_pokemon_capture_rate(wild_pokemon.species_id))

        # 计算公式
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

    # --- Helpers for formatting and logs ---

    def _handle_battle_experience(self, user_id: str, result_str: str, wild_pokemon: WildPokemonInfo):
        if not self.exp_service or result_str != "success":
            return {
                "pokemon_exp": {"success": True, "exp_gained": 0, "message": AnswerEnum.BATTLE_FAILURE_NO_EXP.value},
                "ev_gained": {"hp_ev": 0, "attack_ev": 0, "defense_ev": 0, "sp_attack_ev": 0, "sp_defense_ev": 0, "speed_ev": 0},
                "team_pokemon_results": []
            }

        exp_gained = self.exp_service.calculate_pokemon_exp_gain(
            wild_pokemon_id=wild_pokemon.species_id,  # 使用species_id而不是id
            wild_pokemon_level=wild_pokemon.level,
            battle_result=result_str
        )

        # 计算EV奖励
        ev_gained = self.exp_service.calculate_pokemon_ev_gain(
            wild_pokemon_species_id=wild_pokemon.species_id,
            battle_result=result_str
        )

        user_team = self.team_repo.get_user_team(user_id)
        team_results = []
        if user_team and user_team.team_pokemon_ids:
            team_results = self.exp_service.update_team_pokemon_after_battle(
                user_id,
                user_team.team_pokemon_ids,
                exp_gained,
                ev_gained
            )

        return {
            "pokemon_exp": team_results[0] if team_results else {},
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