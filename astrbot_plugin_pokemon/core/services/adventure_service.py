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
    AbstractUserPokemonRepository, AbstractBattleRepository, AbstractUserItemRepository, AbstractMoveRepository
)
from ..models.adventure_models import AdventureResult, LocationInfo, BattleResult, BattleMoveInfo, BattleContext
from .battle_engine import BattleLogic, BattleState, ListBattleLogger, NoOpBattleLogger
from astrbot.api import logger


class AdventureService:
    """冒险区域相关的业务逻辑服务"""

    # --- 常量定义 ---
    TRAINER_ENCOUNTER_RATE = 0.3  # 训练家遭遇几率


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
            move_repo: AbstractMoveRepository,
            exp_service: ExpService,
            config: Dict[str, Any],
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
        self.battle_logic = BattleLogic(move_repo=self.move_repo)

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

        # 检查该宝可梦物种是否已被用户捕捉
        pokedex_result = self.user_pokemon_repo.get_user_pokedex_ids(user_id)
        is_pokemon_caught = False
        if pokedex_result and wild_pokemon_info.species_id in pokedex_result.get("caught", set()):
            is_pokemon_caught = True

        return BaseResult(
            success=True,
            message=AnswerEnum.ADVENTURE_SUCCESS.value,
            data=AdventureResult(
                wild_pokemon=wild_pokemon_info,
                location=LocationInfo(id=location.id, name=location.name),
                trainer=None,
                is_pokemon_caught=is_pokemon_caught
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
                # 检查宝可梦的当前HP，如果为0则跳过
                if u_info.current_hp > 0:
                    user_pokemon_contexts.append(self._create_battle_context(u_info, is_user=True))

        # 检查是否有可用的宝可梦参与战斗
        if not user_pokemon_contexts:
            return BaseResult(success=False, message="您的所有宝可梦都处于濒死状态，无法进行战斗！")

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
            battle_outcome, log_data, rem_wild_hp, rem_user_hp = self.execute_real_battle(user_ctx, wild_ctx)

            # 更新野生怪状态
            wild_pokemon_info.stats.hp = max(0, rem_wild_hp)
            wild_ctx.current_hp = wild_pokemon_info.stats.hp

            user_ctx.pokemon.stats.hp = max(0, rem_user_hp)
            user_ctx.current_hp = user_ctx.pokemon.stats.hp  # 也要更新上下文中的current_hp以确保一致性
            battle_log.append({
                "pokemon_id": user_ctx.pokemon.id,
                "pokemon_name": user_ctx.pokemon.name,
                "species_name": user_ctx.pokemon.species_id,
                "level": user_ctx.pokemon.level,
                "win_rate": u_win_rate,
                "result": battle_outcome,
                "details": log_data
            })

            # 检查野生宝可梦是否被击败
            if wild_pokemon_info.stats.hp <= 0:
                # 野生宝可梦被击败，战斗成功
                battle_result_str = "success"
                break
            elif battle_outcome == "win":
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

        # 保存战斗后用户的宝可梦状态（HP和PP）
        # 只保存参与战斗的宝可梦（即在战斗循环中被访问过的）
        for i in range(current_idx + 1):  # 保存从索引0到当前索引的所有宝可梦
            if i >= len(user_pokemon_contexts):  # 防御性检查
                break
            ctx = user_pokemon_contexts[i]
            # 更新用户宝可梦的当前HP和当前PP
            self.user_pokemon_repo._update_user_pokemon_fields(
                user_id=user_id,
                pokemon_id=ctx.pokemon.id,
                current_hp=ctx.pokemon.stats.hp,
                current_pp1=ctx.moves[0].current_pp if len(ctx.moves) > 0 else 0,
                current_pp2=ctx.moves[1].current_pp if len(ctx.moves) > 1 else 0,
                current_pp3=ctx.moves[2].current_pp if len(ctx.moves) > 2 else 0,
                current_pp4=ctx.moves[3].current_pp if len(ctx.moves) > 3 else 0
            )

        if self.battle_repo:
            log_id = self.battle_repo.save_battle_log(
                user_id=user_id,
                target_name=wild_pokemon_info.name,
                log_data=battle_log,
                result=battle_result_str
            )
        logger.info(f"战斗日志ID: {log_id}")
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
        # 如果是用户的宝可梦，使用current_hp；如果是野生宝可梦，使用stats.hp
        if isinstance(pokemon_info, UserPokemonInfo):
            current_hp = pokemon_info.current_hp
        else:
            current_hp = pokemon_info.stats.hp
        return BattleContext(
            pokemon=pokemon_info,
            moves=moves_list,
            types=types,
            current_hp=current_hp,
            is_user=is_user
        )

    def _preload_moves(self, pokemon: Any) -> List[BattleMoveInfo]:
        """批量加载宝可梦的所有招式详情，包括预加载的属性变化数据"""
        move_ids = [pokemon.moves.move1_id, pokemon.moves.move2_id, pokemon.moves.move3_id, pokemon.moves.move4_id]
        valid_ids = [m for m in move_ids if m and m > 0]
        loaded_moves = []
        if self.move_repo:
            for mid in valid_ids:
                m_data = self.move_repo.get_move_by_id(mid)
                if m_data:
                    # 基础数值强转，防止数据库返回字符串导致逻辑判断失败
                    max_pp = int(m_data.get('pp', 5) or 5)
                    power = int(m_data.get('power', 0) or 0)
                    accuracy = int(m_data.get('accuracy', 100) or 100)
                    priority = int(m_data.get('priority', 0) or 0)
                    target_id = int(m_data.get('target_id', 0) or 0)
                    damage_class_id = int(m_data.get('damage_class_id', 2) or 2)
                    meta_category_id = int(m_data.get('meta_category_id', 0) or 0)
                    # 其他相关字段也建议强转
                    stat_chance = float(m_data.get('stat_chance', 0.0) or 0.0)
                    drain = float(m_data.get('drain', 0.0) or 0.0)
                    ailment_chance = int(m_data.get('ailment_chance', 0) or 0)
                    meta_ailment_id = int(m_data.get('meta_ailment_id', 0) or 0)
                    healing = float(m_data.get('healing', 0.0) or 0.0)
                    # 预加载技能的属性变化数据
                    stat_changes = self.move_repo.get_move_stat_changes_by_move_id(mid) or []

                    loaded_moves.append(BattleMoveInfo(
                        power=power,
                        accuracy=accuracy,
                        type_name=m_data.get('type_name', 'normal'),
                        damage_class_id=damage_class_id,
                        priority=priority,
                        type_effectiveness=1.0,
                        stab_bonus=1.0,
                        move_id=mid,
                        move_name=m_data.get('name_zh', 'Unknown Move'),
                        max_pp=max_pp,
                        current_pp=max_pp,
                        # 预加载的属性变化数据
                        stat_changes=stat_changes,
                        target_id=target_id,
                        meta_category_id=meta_category_id,
                        ailment_chance=ailment_chance,
                        meta_ailment_id=meta_ailment_id,
                        healing=healing,
                        stat_chance=stat_chance,
                        drain=drain
                    ))

                    # max_pp = m_data.get('pp', 5) or 5
                    # 预加载技能的属性变化数据和目标信息
                    # stat_changes = self.move_repo.get_move_stat_changes_by_move_id(mid) or []
                    # target_id = m_data.get('target_id', 0)
                    # # 预加载技能的meta类别ID
                    # meta_category_id = m_data.get('meta_category_id', 0)
                    # # 预加载技能的stat_chance
                    # stat_chance = m_data.get('stat_chance', 0.0)
                    # # 预加载技能的drain
                    # drain = m_data.get('drain', 0.0)
                    # loaded_moves.append(BattleMoveInfo(
                    #     power=m_data.get('power', 0) or 0,
                    #     accuracy=m_data.get('accuracy', 100) or 100,
                    #     type_name=m_data.get('type_name', 'normal'),
                    #     damage_class_id=m_data.get('damage_class_id', 2),
                    #     priority=m_data.get('priority', 0),
                    #     type_effectiveness=1.0,
                    #     stab_bonus=1.0,
                    #     move_id=mid,
                    #     move_name=m_data.get('name_zh', 'Unknown Move'),
                    #     max_pp=max_pp,
                    #     current_pp=max_pp,
                    #     # 预加载的属性变化数据，避免在战斗循环中查询数据库
                    #     stat_changes=stat_changes,
                    #     target_id=target_id,
                    #     meta_category_id=meta_category_id,
                    #     ailment_chance=m_data.get('ailment_chance', 0.0),
                    #     meta_ailment_id=m_data.get('meta_ailment_id', 0),
                    #     healing=m_data.get('healing', 0.0),
                    #     stat_chance=stat_chance,
                    #     drain=drain
                    # ))
        return loaded_moves

    def execute_real_battle(self, user_ctx: BattleContext, wild_ctx: BattleContext) -> tuple[str, Any, int, int]:
        """执行实战，生成详细日志"""
        logger_obj = ListBattleLogger(log_details=True)  # 真实战斗时启用详细日志
        logger_obj.log(f"战斗开始！{user_ctx.pokemon.name} (Lv.{user_ctx.pokemon.level}) VS {wild_ctx.pokemon.name} (Lv.{wild_ctx.pokemon.level})\n\n")
        logger_obj.log(f"{user_ctx.pokemon.name} HP: {user_ctx.current_hp}, {wild_ctx.pokemon.name} HP: {wild_ctx.current_hp}\n\n")

        # Create BattleState linked to the contexts
        # Note: In real battle, we want to update the context's HP and PP as well?
        # The original code modified user_ctx.current_hp and wild_ctx.current_hp directly.
        # BattleState takes initial values from context.
        # We need to sync back or just use the state to track progress and then update context at the end?
        # Actually, the original code updated user_ctx.current_hp in place.
        # Let's use BattleState to track the battle, and then update the context.

        user_state = BattleState.from_context(user_ctx)
        wild_state = BattleState.from_context(wild_ctx)

        turn = 0
        max_turns = 50
        winner = None
        logger.info(f"[DEBUG] =====================执行实战，生成详细日志=====================")
        
        while user_state.current_hp > 0 and wild_state.current_hp > 0 and turn < max_turns:
            turn += 1
            logger_obj.log(f"--- 第 {turn} 回合 ---\n\n")

            battle_ended = self.battle_logic.process_turn(user_state, wild_state, logger_obj)
            
            logger_obj.log(f"\n\n剩余HP - {user_ctx.pokemon.name}: {max(0, user_state.current_hp)}, {wild_ctx.pokemon.name}: {max(0, wild_state.current_hp)}\n\n")

            if battle_ended:
                if user_state.current_hp > 0:
                    winner = "user"
                else:
                    winner = "wild"
                break

        if not winner:
            result = "fail"
            logger_obj.log("战斗超时，强制结束。\n\n")
        else:
            result = "win" if winner == "user" else "fail"
        
        logger.info("=====================实战结束=====================")

        # Sync PP back to moves in context (HP is handled by the caller)
        for i, move in enumerate(user_ctx.moves):
            move.current_pp = user_state.current_pps[i]
        for i, move in enumerate(wild_ctx.moves):
            move.current_pp = wild_state.current_pps[i]

        return result, logger_obj.logs, wild_state.current_hp, user_state.current_hp
        # return result, logger_obj.logs, wild_state.current_hp


    def calculate_battle_win_rate(self, user_ctx: BattleContext, wild_ctx: BattleContext, simulations: int = 100) -> \
    Tuple[float, float]:
        """优化版蒙特卡洛模拟：减少对象创建，仅追踪整数PP"""
        user_wins = 0
        logger_obj = NoOpBattleLogger()

        for _ in range(simulations):
            # Create fresh state for each simulation
            user_state = BattleState.from_context(user_ctx)
            wild_state = BattleState.from_context(wild_ctx)

            turn = 0
            while user_state.current_hp > 0 and wild_state.current_hp > 0 and turn < 50:
                turn += 1
                battle_ended = self.battle_logic.process_turn(user_state, wild_state, logger_obj)
                if battle_ended:
                    break
            
            if user_state.current_hp > 0:
                user_wins += 1

        win_rate = (user_wins / simulations) * 100
        return round(win_rate, 1), round(100 - win_rate, 1)

    def calculate_type_effectiveness(self, attacker_types: List[str], defender_types: List[str]) -> float:
        """计算属性克制系数"""
        return self.battle_logic.calculate_type_effectiveness(attacker_types, defender_types)

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

        # 处理特殊精灵球逻辑
        ball_id = int(pokeball_item.item_id)
        ball_multiplier = 1.0  # 默认倍数

        # 根据精灵球ID应用特殊逻辑
        # 1: 大师球 - 100% 捕捉成功率
        if ball_id == 1:
            ball_multiplier = 255.0  # 大师球确保捕捉成功
        # 2: 高级球 - 2x 捕捉成功率
        elif ball_id == 2:
            ball_multiplier = 2.0
        # 3: 超级球 - 1.5x 捕捉成功率
        elif ball_id == 3:
            ball_multiplier = 1.5
        # 4: 普通精灵球 - 1x 捕捉成功率
        elif ball_id == 4:
            ball_multiplier = 1.0
        # 5: 狩猎球 - 按描述这球只能在特定区域使用，这里先按1.5x处理
        elif ball_id == 5:
            ball_multiplier = 1.5
        # 6: 捕网球球 - 3x针对水/虫系宝可梦，1x其他
        elif ball_id == 6:
            # 检查野生宝可梦是否为水系或虫系
            pokemon_types = [t.lower() for t in self.pokemon_repo.get_pokemon_types(wild_pokemon.species_id) or ['normal']]
            if 'water' in pokemon_types or 'bug' in pokemon_types:
                ball_multiplier = 3.0
            else:
                ball_multiplier = 1.0
        # 7: 潜水球球 - 3.5x针对水上/钓鱼时遇到的宝可梦，1x其他
        elif ball_id == 7:
            # 这里先按3.5x处理，实际应用时可能需要判断是否在水上/钓鱼情境中
            ball_multiplier = 3.5
        # 8: 巢穴球 - 捕捉率根据宝可梦等级变化 (40-level)/10，最高3.9x (level 1)，最低1x (level 30+)
        elif ball_id == 8:
            level = wild_pokemon.level
            # 根据公式 (40 - level) / 10 计算倍数，最低为1.0
            calculated_multiplier = max(1.0, (40 - level) / 10)
            ball_multiplier = min(3.9, calculated_multiplier)  # 最高3.9倍
        # 9: 重复球 - 3x针对已捕捉过的宝可梦种类，1x其他
        elif ball_id == 9:
            # 检查用户是否已捕获过该种类的宝可梦
            pokedex_result = self.user_pokemon_repo.get_user_pokedex_ids(user_id)
            if pokedex_result and wild_pokemon.species_id in pokedex_result.get("caught", set()):
                ball_multiplier = 3.0
            else:
                ball_multiplier = 1.0
        # 10: 计时球 - 捕捉率随回合增加，最高4x
        elif ball_id == 10:
            # 这里先按1x处理，实际应用中可能需要根据战斗回合数调整
            ball_multiplier = 1.0
        # 11: 豪华球 - 捕捉成功后初始友好度+200
        elif ball_id == 11:
            ball_multiplier = 1.0  # 基础捕捉率不变
        # 12: 纪念球 - 1x 捕捉成功率
        elif ball_id == 12:
            ball_multiplier = 1.0
        # 13: 黑暗球 - 夜晚(18:00-6:00)时3.5x，其他时间1x
        elif ball_id == 13:
            # 获取当前北京时间
            from datetime import datetime
            import pytz
            beijing_tz = pytz.timezone('Asia/Shanghai')  # 北京时间
            current_time = datetime.now(beijing_tz)
            current_hour = current_time.hour

            # 如果当前时间在18:00-6:00之间（晚上6点到早上6点），使用3.5倍数
            if 18 <= current_hour <= 23 or 0 <= current_hour < 6:
                ball_multiplier = 3.5
            else:
                ball_multiplier = 1.0
        # 14: 治愈球 - 捕捉成功后立即治愈
        elif ball_id == 14:
            ball_multiplier = 1.0  # 基础捕捉率不变
        # 15: 先机球 - 首回合4x，其他回合1x
        elif ball_id == 15:
            # 这里先按4x处理，实际应用中可能需要判断是否为战斗首回合
            ball_multiplier = 4.0
        # 16: 贵重球 - 1x 捕捉成功率
        elif ball_id == 16:
            ball_multiplier = 1.0

        max_hp = wild_pokemon.stats.hp
        # 简单模拟当前血量 (若有战斗上下文应传入实际血量)
        temp_current_hp = int(random.gauss(max_hp * 0.75, max_hp * 0.25))
        current_hp = max(1, min(max_hp, temp_current_hp))

        base_capture_rate = int(self.pokemon_repo.get_pokemon_capture_rate(wild_pokemon.species_id))
        catch_value = int(((3 * max_hp - 2 * current_hp) * base_capture_rate * ball_multiplier) // (3 * max_hp))
        catch_value = min(catch_value, 255)
        success_rate = catch_value / 256.0

        # 特殊处理大师球：直接返回100%成功率
        if ball_id == 1:  # 大师球
            success_rate = 1.0
            catch_value = 255

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

                # 检查宝可梦当前的HP状态，濒死（HP=0）的宝可梦不应该获得经验
                current_pokemon = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pid)
                if not current_pokemon or current_pokemon.current_hp <= 0:
                    # 濒死的宝可梦不获得经验
                    continue

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
                # 检查宝可梦的当前HP，如果为0则跳过
                if u_info.current_hp > 0:
                    user_contexts.append(self._create_battle_context(u_info, True))

        # 检查是否有可用的宝可梦参与战斗
        if not user_contexts:
            return BaseResult(success=False, message="您的所有宝可梦都处于濒死状态，无法进行战斗！")

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
            outcome, details, rem_t_hp, rem_u_hp = self.execute_real_battle(u_ctx, t_ctx)

            # 更新用户和训练家的 HP
            u_ctx.pokemon.stats.hp = max(0, rem_u_hp)
            u_ctx.current_hp = u_ctx.pokemon.stats.hp  # 也要更新上下文中的current_hp以确保一致性

            t_ctx.pokemon.stats.hp = max(0, rem_t_hp)
            t_ctx.current_hp = t_ctx.pokemon.stats.hp  # 也要更新上下文中的current_hp以确保一致性

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

            # 检查训练家宝可梦是否被击败
            if t_ctx.pokemon.stats.hp <= 0:
                # 训练家宝可梦被击败，对方下一只上场
                t_idx += 1  # 击败对方一只，对方下一只上场
            elif outcome == "win":
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

        # 保存战斗后用户的宝可梦状态（HP和PP）
        # 只保存参与战斗的宝可梦（即在战斗循环中被访问过的）
        for i in range(u_idx + 1):  # 保存从索引0到当前索引的所有宝可梦
            ctx = user_contexts[i]
            # 更新用户宝可梦的当前HP和当前PP
            self.user_pokemon_repo._update_user_pokemon_fields(
                user_id=user_id,
                pokemon_id=ctx.pokemon.id,
                current_hp=ctx.pokemon.stats.hp,
                current_pp1=ctx.moves[0].current_pp if len(ctx.moves) > 0 else 0,
                current_pp2=ctx.moves[1].current_pp if len(ctx.moves) > 1 else 0,
                current_pp3=ctx.moves[2].current_pp if len(ctx.moves) > 2 else 0,
                current_pp4=ctx.moves[3].current_pp if len(ctx.moves) > 3 else 0
            )

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

                # 检查宝可梦当前的HP状态，濒死（HP=0）的宝可梦不应该获得经验
                if current_pokemon.current_hp <= 0:
                    # 濒死的宝可梦不获得经验
                    pokemon_exp = 0
                    exp_message = "宝可梦处于濒死状态，未获得经验"
                elif pokemon_id in battle_deaths:
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