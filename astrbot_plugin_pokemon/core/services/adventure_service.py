import math
import random
from itertools import accumulate
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

from . import user_pokemon_service
from .exp_service import ExpService
from .pokemon_service import PokemonService
from ..models.common_models import BaseResult
from ...interface.response.answer_enum import AnswerEnum
from ..models.pokemon_models import WildPokemonInfo, PokemonStats, PokemonIVs, PokemonEVs, \
    UserPokemonInfo, WildPokemonEncounterLog, PokemonMoves
from ..models.user_models import UserTeam, UserItems
from ...infrastructure.repositories.abstract_repository import (
    AbstractAdventureRepository, AbstractPokemonRepository, AbstractUserRepository, AbstractTeamRepository,
    AbstractUserPokemonRepository, AbstractBattleRepository, AbstractUserItemRepository
)
from ..models.adventure_models import AdventureResult, LocationInfo, BattleResult, BattleMoveInfo
from astrbot.api import logger

class AdventureService:
    """冒险区域相关的业务逻辑服务"""

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
            move_repo = None,

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
        # ----------------------
        # 宝可梦属性克制表（第三世代及之后全属性，key: 攻击属性, value: {防御属性: 克制系数}）
        # ----------------------
        self.TYPE_CHART = {
            'normal': {'rock': 0.5, 'ghost': 0.0, 'steel': 0.5},
            'fire': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 2.0, 'bug': 2.0, 'rock': 0.5, 'dragon': 0.5, 'steel': 2.0},
            'water': {'fire': 2.0, 'water': 0.5, 'grass': 0.5, 'ground': 2.0, 'rock': 2.0, 'dragon': 0.5},
            'electric': {'water': 2.0, 'electric': 0.5, 'grass': 0.5, 'ground': 0.0, 'flying': 2.0, 'dragon': 0.5},
            'grass': {'fire': 0.5, 'water': 2.0, 'grass': 0.5, 'poison': 0.5, 'ground': 2.0, 'flying': 0.5, 'bug': 0.5, 'rock': 2.0, 'dragon': 0.5, 'steel': 0.5},
            'ice': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 0.5, 'ground': 2.0, 'flying': 2.0, 'dragon': 2.0, 'steel': 0.5},
            'fighting': {'normal': 2.0, 'ice': 2.0, 'poison': 0.5, 'flying': 0.5, 'psychic': 0.5, 'bug': 0.5, 'rock': 2.0, 'ghost': 0.0, 'dark': 2.0, 'steel': 2.0, 'fairy': 0.5},
            'poison': {'grass': 2.0, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'ghost': 0.5, 'steel': 0.0, 'fairy': 2.0},
            'ground': {'fire': 2.0, 'electric': 2.0, 'grass': 0.5, 'poison': 2.0, 'flying': 0.0, 'bug': 0.5, 'rock': 2.0, 'steel': 2.0},
            'flying': {'electric': 0.5, 'grass': 2.0, 'fighting': 2.0, 'bug': 2.0, 'rock': 0.5, 'steel': 0.5},
            'psychic': {'fighting': 2.0, 'poison': 2.0, 'psychic': 0.5, 'dark': 0.0, 'steel': 0.5},
            'bug': {'fire': 0.5, 'grass': 2.0, 'fighting': 0.5, 'poison': 0.5, 'flying': 0.5, 'psychic': 2.0, 'ghost': 0.5, 'dark': 2.0, 'steel': 0.5, 'fairy': 0.5},
            'rock': {'fire': 2.0, 'ice': 2.0, 'fighting': 0.5, 'ground': 0.5, 'flying': 2.0, 'bug': 2.0, 'steel': 0.5},
            'ghost': {'normal': 0.0, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5},
            'dragon': {'dragon': 2.0, 'steel': 0.5, 'fairy': 0.0},
            'dark': {'fighting': 0.5, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5, 'fairy': 0.5},
            'steel': {'fire': 0.5, 'water': 0.5, 'electric': 0.5, 'ice': 2.0, 'rock': 2.0, 'steel': 0.5, 'fairy': 2.0},
            'fairy': {'fighting': 2.0, 'poison': 0.5, 'bug': 0.5, 'dragon': 2.0, 'dark': 2.0, 'steel': 0.5}
        }

    def get_all_locations(self) -> BaseResult[List[LocationInfo]]:
        """
        获取所有可冒险的区域列表
        Returns:
            包含区域列表的字典
        """

        locations = self.adventure_repo.get_all_locations()

        if not locations:
            return BaseResult(
                success=True,
                message=AnswerEnum.ADVENTURE_NO_LOCATIONS.value,
            )

        formatted_locations: List[LocationInfo] = []
        for location in locations:
            location_info: LocationInfo = LocationInfo(
                id=location.id,
                name=location.name,
                description=location.description or "暂无描述",
                min_level=location.min_level,
                max_level=location.max_level
            )
            formatted_locations.append(location_info)


        return BaseResult(
            success=True,
            message=AnswerEnum.ADVENTURE_LOCATIONS_FOUND.value,
            data=formatted_locations
        )


    def adventure_in_location(self, user_id: str, location_id: int) -> BaseResult[AdventureResult]:
        """
        在指定区域进行冒险，随机刷新一只野生宝可梦
        Args:
            user_id: 用户ID
            location_id: 区域ID
        Returns:
            包含冒险结果的字典
        """
        # 1. 获取区域信息
        location = self.adventure_repo.get_location_by_id(location_id)
        if not location:
            return BaseResult(
                success=False,
                message=AnswerEnum.ADVENTURE_LOCATION_NOT_FOUND.value.format(location_id=location_id)
            )
        # 2 获取该区域的宝可梦列表
        location_pokemon_list = self.adventure_repo.get_location_pokemon_by_location_id(location_id)
        if not location_pokemon_list:
            return BaseResult(
                success=False,
                message=AnswerEnum.ADVENTURE_LOCATION_NO_POKEMON.value.format(location_name=location.name)
            )
        # 3. 权重随机选择宝可梦（使用itertools.accumulate简化累加逻辑）
        encounter_rates = [ap.encounter_rate for ap in location_pokemon_list]
        total_rate = sum(encounter_rates)
        random_value = random.uniform(0, total_rate)

        # 累加概率，找到第一个超过随机值的宝可梦
        for idx, cumulative_rate in enumerate(accumulate(encounter_rates)):
            if random_value <= cumulative_rate:
                selected_location_pokemon = location_pokemon_list[idx]
                break
        else:
            # 兜底：如果循环未触发break（理论上不会发生），取最后一个
            selected_location_pokemon = location_pokemon_list[-1]

        # 4. 生成宝可梦等级（使用变量名简化赋值）
        min_level = selected_location_pokemon.min_level
        max_level = selected_location_pokemon.max_level
        wild_pokemon_level = random.randint(min_level, max_level)
        # 5. 创建野生宝可梦（直接使用返回结果，无需额外处理）
        wild_pokemon_result = self.pokemon_service.create_single_pokemon(
            species_id=selected_location_pokemon.pokemon_species_id,
            max_level=wild_pokemon_level,
            min_level=wild_pokemon_level
        )
        if not wild_pokemon_result.success:
            return BaseResult(
                success=False,
                message=wild_pokemon_result.message
            )
        wild_pokemon = wild_pokemon_result.data
        wild_pokemon_info = WildPokemonInfo(
                id=0,
                species_id=wild_pokemon.base_pokemon.id,
                name=wild_pokemon.base_pokemon.name_zh,
                gender=wild_pokemon.gender,
                level=wild_pokemon_level,
                exp=wild_pokemon.exp,
                stats=PokemonStats(
                    hp=wild_pokemon.stats.hp,
                    attack=wild_pokemon.stats.attack,
                    defense=wild_pokemon.stats.defense,
                    sp_attack=wild_pokemon.stats.sp_attack,
                    sp_defense=wild_pokemon.stats.sp_defense,
                    speed=wild_pokemon.stats.speed,
                ),
                ivs=PokemonIVs(
                    hp_iv=wild_pokemon.ivs.hp_iv,
                    attack_iv=wild_pokemon.ivs.attack_iv,
                    defense_iv=wild_pokemon.ivs.defense_iv,
                    sp_attack_iv=wild_pokemon.ivs.sp_attack_iv,
                    sp_defense_iv=wild_pokemon.ivs.sp_defense_iv,
                    speed_iv=wild_pokemon.ivs.speed_iv,
                ),
                evs=PokemonEVs(
                    hp_ev=wild_pokemon.evs.hp_ev,
                    attack_ev=wild_pokemon.evs.attack_ev,
                    defense_ev=wild_pokemon.evs.defense_ev,
                    sp_attack_ev=wild_pokemon.evs.sp_attack_ev,
                    sp_defense_ev=wild_pokemon.evs.sp_defense_ev,
                    speed_ev=wild_pokemon.evs.speed_ev,
                ),
                moves=PokemonMoves(
                    move1_id=wild_pokemon.moves.move1_id,
                    move2_id=wild_pokemon.moves.move2_id,
                    move3_id=wild_pokemon.moves.move3_id,
                    move4_id=wild_pokemon.moves.move4_id,
                )
        )
        wild_pokemon_id = self.pokemon_repo.add_wild_pokemon(wild_pokemon_info)

        self.user_pokemon_repo.add_user_encountered_wild_pokemon(
            user_id=user_id,
            wild_pokemon_id = wild_pokemon_id,
            location_id=location.id,
            encounter_rate=selected_location_pokemon.encounter_rate,
        )
        return BaseResult(
            success=True,
            message=AnswerEnum.ADVENTURE_SUCCESS.value,
            data=AdventureResult(
                wild_pokemon=wild_pokemon_info,
                location=LocationInfo(
                    id=location.id,
                    name=location.name,
                ),
            )
        )

    def adventure_in_battle(self, user_id: str, wild_pokemon_info: WildPokemonInfo) -> BaseResult:
        """
        处理用户与野生宝可梦战斗的结果。

        :param user_id: 用户ID
        :param wild_pokemon_info: 野生宝可梦信息
        :return: 战斗结果
        """
        # 检查用户是否有设置队伍
        user_team_data: UserTeam = self.team_repo.get_user_team(user_id)
        user = self.user_repo.get_user_by_id(user_id)
        if not user_team_data:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_TEAM_NOT_SET.value,
            )

        user_team_list: List[int] = user_team_data.team_pokemon_ids

        # 开始战斗，传入玩家的队伍
        result = self.start_battle(user_id, wild_pokemon_info, user_team_list)
        return result

    def start_battle(self, user_id: str, wild_pokemon_info: WildPokemonInfo, user_team_list: List[int] = None) -> BaseResult[BattleResult]:
        """
        开始一场与野生宝可梦的战斗
        Args:
            user_id: 用户ID
            wild_pokemon_info: 野生宝可梦数据
            user_team_list: 用户队伍中的宝可梦ID列表
        Returns:
            包含战斗结果的字典
        """

        # 如果没有提供队伍列表，从用户数据获取
        if user_team_list is None:
            user_team_data: UserTeam = self.team_repo.get_user_team(user_id)
            if not user_team_data or not user_team_data.team_pokemon_ids:
                return BaseResult(
                    success=False,
                    message=AnswerEnum.USER_TEAM_NOT_SET.value
                )
            user_team_list = user_team_data.team_pokemon_ids

        # 按顺序使用队伍中的宝可梦进行战斗
        current_pokemon_index = 0
        battle_result = None
        battle_result_str = "fail"  # 默认设为失败
        final_user_pokemon_info = None
        all_user_win_rates = []  # 存储所有尝试过的宝可梦的胜率
        all_wild_win_rates = []  # 存储所有尝试过的宝可梦对应的野生宝可梦胜率
        battle_log = []  # 战斗日志，记录每个宝可梦的战斗情况

        # 循环使用队伍中的宝可梦，直到有宝可梦获胜或队伍全部用完
        while current_pokemon_index < len(user_team_list):
            user_pokemon_id = user_team_list[current_pokemon_index]
            user_pokemon_info = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, user_pokemon_id)

            if not user_pokemon_info:
                current_pokemon_index += 1
                continue  # 如果该宝可梦不存在，跳到下一个

            final_user_pokemon_info = user_pokemon_info  # 记录当前战斗的宝可梦信息

            # 1. 计算胜率 (蒙特卡洛方法) - 用于显示
            user_win_rate, wild_win_rate = self.calculate_battle_win_rate(user_pokemon_info, wild_pokemon_info)
            all_user_win_rates.append(user_win_rate)
            all_wild_win_rates.append(wild_win_rate)

            # 2. 执行实际战斗 (一次运行，带日志)
            # 野生宝可梦应该保持其HP。
            
            battle_outcome, battle_log_data, remaining_wild_hp = self.execute_real_battle(
                user_pokemon_info, wild_pokemon_info
            )

            # 3. 保存日志

            battle_log.append({
                "pokemon_id": user_pokemon_info.id,
                "pokemon_name": user_pokemon_info.name,
                "species_name": user_pokemon_info.species_id,
                "level": user_pokemon_info.level,
                "win_rate": user_win_rate,
                "result": battle_outcome,
                "details": battle_log_data # 详细回合制
            })

            current_battle_result_str = "success" if battle_outcome == "win" else "fail"

            # 如果当前宝可梦获胜，跳出循环
            if current_battle_result_str == "success":
                battle_result = (user_win_rate, wild_win_rate)
                battle_result_str = "success"
                break
            else:
                # 当前宝可梦失败
                current_pokemon_index += 1
                # 更新野生宝可梦的HP
                wild_pokemon_info.stats.hp = max(0, remaining_wild_hp)

        # 将完整的战斗日志保存到数据库
        log_id = 0
        if self.battle_repo:
            full_log = [entry["details"] for entry in battle_log]
            log_id = self.battle_repo.save_battle_log(
                user_id=user_id,
                target_name=wild_pokemon_info.name,
                log_data=battle_log,
                result=battle_result_str
            )

        # 如果所有宝可梦都失败了，则战斗失败
        if battle_result is None:
            # 如果所有宝可梦都失败，使用所有尝试过的宝可梦的平均胜率
            if all_user_win_rates:
                user_win_rate = round(sum(all_user_win_rates) / len(all_user_win_rates), 2)
                wild_win_rate = round(sum(all_wild_win_rates) / len(all_wild_win_rates), 2)
            else:
                # 如果没有找到有效的宝可梦，返回失败结果
                user_win_rate, wild_win_rate = 0.0, 100.0
                battle_result_str = "fail"
        else:
            user_win_rate, wild_win_rate = battle_result

        # 处理经验值（仅在胜利时）
        exp_details = {}
        if self.exp_service and battle_result_str == "success":
            # 计算宝可梦获得的经验值
            pokemon_exp_gained = self.exp_service.calculate_pokemon_exp_gain(wild_pokemon_id=wild_pokemon_info.id, wild_pokemon_level=wild_pokemon_info.level, battle_result=battle_result_str)
            # 获取用户队伍中的所有宝可梦
            user_team_data:UserTeam = self.team_repo.get_user_team(user_id)
            team_pokemon_results = []
            team_pokemon_ids=user_team_data.team_pokemon_ids
            # 更新队伍中所有宝可梦的经验值
            if team_pokemon_ids:
                team_pokemon_results = self.exp_service.update_team_pokemon_after_battle(
                    user_id, team_pokemon_ids, pokemon_exp_gained)

            exp_details = {
                "pokemon_exp": team_pokemon_results[0] if team_pokemon_results else {"success": False, "message": AnswerEnum.TEAM_GET_NO_TEAM.value},
                "team_pokemon_results": team_pokemon_results
            }

        elif self.exp_service and battle_result_str != "success":
            # 战斗失败时不获得经验
            exp_details = {
                "pokemon_exp": {"success": True, "exp_gained": 0, "message": AnswerEnum.BATTLE_FAILURE_NO_EXP.value},
                "user_exp": {"success": True, "exp_gained": 0, "message": AnswerEnum.BATTLE_FAILURE_NO_EXP.value},
                "team_pokemon_results": []
            }

        # 更新野生宝可梦遇到日志 - 标记为已战斗
        # 获取最近的野生宝可梦遇到记录
        recent_encounters: List[WildPokemonEncounterLog] = self.user_pokemon_repo.get_user_encounters(user_id, limit=5)
        encounter_log_id = None
        for encounter in recent_encounters:
            if (encounter.wild_pokemon_id == wild_pokemon_info.id and
                encounter.is_battled == 0):  # 未战斗的记录
                encounter_log_id = encounter.id
                break
        if encounter_log_id:
            battle_outcome = "win" if battle_result_str == "success" else "lose"
            self.user_pokemon_repo.update_encounter_log(
                log_id=encounter_log_id,
                is_battled=1,
                battle_result=battle_outcome
            )

        return BaseResult(
            success=True,
            message=AnswerEnum.BATTLE_SUCCESS.value,
            data=BattleResult(
                user_pokemon={
                    "name": final_user_pokemon_info.name if final_user_pokemon_info else "Unknown",
                    "species": final_user_pokemon_info.species_id if final_user_pokemon_info else 0,
                    "level": final_user_pokemon_info.level if final_user_pokemon_info else 0,
                    "hp": final_user_pokemon_info.stats.hp if final_user_pokemon_info else 0,
                    "attack": final_user_pokemon_info.stats.attack if final_user_pokemon_info else 0,
                    "defense": final_user_pokemon_info.stats.defense if final_user_pokemon_info else 0,
                    "speed": final_user_pokemon_info.stats.speed if final_user_pokemon_info else 0
                },
                wild_pokemon={
                    "name": wild_pokemon_info.name,
                    "level": wild_pokemon_info.level,
                    "hp": wild_pokemon_info.stats.hp,
                    "attack": wild_pokemon_info.stats.attack,
                    "defense": wild_pokemon_info.stats.defense,
                    "speed": wild_pokemon_info.stats.speed
                },
                win_rates={
                    "user_win_rate": user_win_rate,
                    "wild_win_rate": wild_win_rate
                },
                result=battle_result_str,
                exp_details=exp_details,
                battle_log=battle_log,
                log_id=log_id # 返回日志ID
            )
        )


    def calculate_type_effectiveness(self, attacker_types: List[str], defender_types: List[str]) -> float:
        """
        计算属性克制系数
        攻击方对防御方的总克制系数（取双属性的乘积，如火焰+飞行对岩石：2.0×2.0=4.0）
        """
        effectiveness = 1.0
        for attacker_type in attacker_types:
            type_name = attacker_type.lower()
            if type_name in self.TYPE_CHART:
                for defender_type in defender_types:
                    def_type_name = defender_type.lower()
                    effectiveness *= self.TYPE_CHART[type_name].get(def_type_name, 1.0)
        return effectiveness

    def get_move_details(self, move_id: int) -> Optional[BattleMoveInfo]:
        """
        获取招式详情
        """
        move_data = self.move_repo.get_move_by_id(move_id)
        if not move_data:
            return None
        return BattleMoveInfo(
            power=move_data.get('power', 0) or 0,
            accuracy=move_data.get('accuracy', 100) or 100,
            type_name=move_data.get('type_name', 'normal'),
            damage_class_id=move_data.get('damage_class_id', 2),
            priority=move_data.get('priority', 0),
            type_effectiveness=1.0,
            stab_bonus=1.0,
            move_id=move_id,
            move_name=move_data.get('name_zh', 'Unknown Move')
        )

    def get_moves_list(self, attacker: Any) -> List[BattleMoveInfo]:
        """
        获取攻击方的所有招式详情
        """
        attacker_moves = [attacker.moves.move1_id, attacker.moves.move2_id,
                          attacker.moves.move3_id, attacker.moves.move4_id]
        valid_moves = [m for m in attacker_moves if m and m > 0]
        moves_list = []
        for move_id in valid_moves:
            move_details = self.get_move_details(move_id)
            if move_details:
                moves_list.append(move_details)
        return moves_list

    def get_randon_move(self, attacker: Any) -> Optional[BattleMoveInfo]:
        """
        随机选择一个招式
        """
        attacker_moves = [attacker.moves.move1_id, attacker.moves.move2_id,
                          attacker.moves.move3_id, attacker.moves.move4_id]
        valid_moves = [m for m in attacker_moves if m and m > 0]
        if not valid_moves:
            return None
        random_move_id = random.choice(valid_moves)
        move_data = self.move_repo.get_move_by_id(random_move_id)
        if not move_data:
            return None
        return BattleMoveInfo(
            power=move_data.get('power', 0) or 0,
            accuracy=move_data.get('accuracy', 100) or 100,
            type_name=move_data.get('type_name', 'normal'),
            damage_class_id=move_data.get('damage_class_id', 2),
            priority=move_data.get('priority', 0),
            type_effectiveness=1.0,
            stab_bonus=1.0,
            move_id=random_move_id,
            move_name=move_data.get('name_zh', 'Unknown Move')
        )

    def get_best_move(self, attacker: Any, defender: Any) -> BattleMoveInfo:
        """
        根据预期伤害为攻击方选择最佳招式。
        """
        attacker_moves = [attacker.moves.move1_id, attacker.moves.move2_id,
                          attacker.moves.move3_id, attacker.moves.move4_id]
        valid_moves = [m for m in attacker_moves if m and m > 0]

        attacker_types = self.pokemon_repo.get_pokemon_types(attacker.species_id) or ['normal']
        defender_types = self.pokemon_repo.get_pokemon_types(defender.species_id) or ['normal']

        best_move = None
        max_expected_damage = -1.0

        # 默认招式 (类似挣扎)
        default_move = BattleMoveInfo(
            power=50, accuracy=100.0, type_name='normal',
            damage_class_id=2, priority=0, type_effectiveness=1.0, stab_bonus=1.0, move_id=0, move_name="默认招式"
        )

        if not self.move_repo or not valid_moves:
            return default_move

        for move_id in valid_moves:
            move_data = self.move_repo.get_move_by_id(move_id)
            if not move_data:
                continue

            power = move_data.get('power', 0) or 0
            if power == 0:  # 状态招式，暂时忽略
                continue

            move_name = move_data.get('name_zh', 'Unknown Move')
            accuracy = move_data.get('accuracy', 100) or 100
            type_name = move_data.get('type_name', 'normal')
            damage_class = move_data.get('damage_class_id', 2)  # 2 物理, 3 特攻
            priority = move_data.get('priority', 0)

            # 属性效果
            eff = self.calculate_type_effectiveness([type_name], defender_types)

            # 同属性加成
            stab = 1.5 if type_name in attacker_types else 1.0

            # 属性值
            atk_stat = attacker.stats.attack if damage_class == 2 else attacker.stats.sp_attack
            def_stat = defender.stats.defense if damage_class == 2 else defender.stats.sp_defense

            # 简化伤害评分选择
            damage_score = power * (accuracy / 100.0) * eff * stab * (atk_stat / max(1, def_stat))

            if damage_score > max_expected_damage:
                max_expected_damage = damage_score
                best_move = BattleMoveInfo(
                    move_name=move_name,
                    power=power,
                    accuracy=float(accuracy),
                    type_name=type_name,
                    damage_class_id=damage_class,
                    priority=priority,
                    type_effectiveness=eff,
                    stab_bonus=stab,
                    move_id=move_id
                )

        return best_move if best_move else default_move

    def resolve_damage(self, attacker: Any, defender: Any, move: BattleMoveInfo) -> int:
        # 命中检查
        if random.random() * 100 > move.accuracy:
            return 0

        # 属性
        atk_stat = attacker.stats.attack if move.damage_class_id == 2 else attacker.stats.sp_attack
        def_stat = defender.stats.defense if move.damage_class_id == 2 else defender.stats.sp_defense

        # 等级
        level = attacker.level

        # 基础伤害
        base_damage = ((2 * level / 5 + 2) * move.power * atk_stat / max(1, def_stat)) / 50 + 2

        # 修正系数
        # 暴击检查 (1/16 = 6.25%)
        is_crit = random.random() < 0.0625
        crit_multiplier = 1.5 if is_crit else 1.0

        # 随机因素 (0.85 - 1.0)
        random_multiplier = random.uniform(0.85, 1.0)

        final_damage = base_damage * move.type_effectiveness * move.stab_bonus * crit_multiplier * random_multiplier

        return int(final_damage)

    def execute_real_battle(self, user_pokemon: UserPokemonInfo, wild_pokemon: WildPokemonInfo) -> Tuple[str, List[str], int]:
        """
        执行单次实际战斗模拟并返回日志和结果。
        返回: (result_str, log_lines, remaining_wild_hp)
        """
        cur_user_hp = user_pokemon.stats.hp
        cur_wild_hp = wild_pokemon.stats.hp

        log_lines = []
        log_lines.append(f"战斗开始！{user_pokemon.name} (Lv.{user_pokemon.level}) VS {wild_pokemon.name} (Lv.{wild_pokemon.level})\n\n")
        log_lines.append(f"{user_pokemon.name} HP: {cur_user_hp}, {wild_pokemon.name} HP: {cur_wild_hp}\n\n")

        turn = 0
        max_turns = 50
        result = "fail"

        user_moves_list = self.get_moves_list(user_pokemon)
        wild_moves_list = self.get_moves_list(wild_pokemon)

        while cur_user_hp > 0 and cur_wild_hp > 0 and turn < max_turns:
            turn += 1
            log_lines.append(f"--- 第 {turn} 回合 ---\n\n")
            user_random_move = random.choice(user_moves_list)
            wild_random_move = random.choice(wild_moves_list)
            user_first = self.user_goes_first(
                user_pokemon.stats.speed,
                wild_pokemon.stats.speed,
                user_random_move,
                wild_random_move
            )

            first_attacker = user_pokemon if user_first else wild_pokemon
            second_attacker = wild_pokemon if user_first else user_pokemon
            first_move = user_random_move if user_first else wild_random_move
            second_move = wild_random_move if user_first else user_random_move

            # 首次攻击
            dmg = self.resolve_damage(first_attacker, second_attacker, first_move)
            if user_first:
                cur_wild_hp -= dmg
                log_lines.append(f"{user_pokemon.name} 使用了 {first_move.type_name} 属性招式 {first_move.move_name} ！造成了 {dmg} 点伤害。\n\n")
                if cur_wild_hp <= 0:
                    log_lines.append(f"{wild_pokemon.name} 倒下了！\n\n")
                    result = "win"
                    break
            else:
                cur_user_hp -= dmg
                log_lines.append(f"{wild_pokemon.name} 使用了 {first_move.type_name} 属性招式 {first_move.move_name} ！造成了 {dmg} 点伤害。\n\n")
                if cur_user_hp <= 0:
                    log_lines.append(f"{user_pokemon.name} 倒下了！\n\n")
                    result = "fail"
                    break

            # 第二次攻击
            dmg = self.resolve_damage(second_attacker, first_attacker, second_move)
            if user_first:
                cur_user_hp -= dmg
                log_lines.append(f"{wild_pokemon.name} 使用了 {second_move.type_name} 属性招式 {second_move.move_name} ！造成了 {dmg} 点伤害。\n\n")
                if cur_user_hp <= 0:
                    log_lines.append(f"{user_pokemon.name} 倒下了！\n\n")
                    result = "fail"
                    break
            else:
                cur_wild_hp -= dmg
                log_lines.append(f"{user_pokemon.name} 使用了 {second_move.type_name} 属性招式 {second_move.move_name} ！造成了 {dmg} 点伤害。\n\n")
                if cur_wild_hp <= 0:
                    log_lines.append(f"{wild_pokemon.name} 倒下了！\n\n")
                    result = "win"
                    break

            log_lines.append(f"剩余HP - {user_pokemon.name}: {max(0, cur_user_hp)}, {wild_pokemon.name}: {max(0, cur_wild_hp)}\n\n")

        if turn >= max_turns:
            log_lines.append("战斗回合数达到上限，强制结束。\n\n")
            result = "fail"

        return result, log_lines, cur_wild_hp

    def user_goes_first(self, user_speed: int, wild_speed: int, user_move: BattleMoveInfo, wild_move: BattleMoveInfo) -> bool:
        if user_move.priority > wild_move.priority:
            return True
        elif wild_move.priority > user_move.priority:
            return False

        if user_speed > wild_speed:
            return True
        elif wild_speed > user_speed:
            return False
        else:
            return random.random() < 0.5

    def calculate_battle_win_rate(self, user_pokemon: UserPokemonInfo, wild_pokemon: WildPokemonInfo) -> Tuple[float, float]:
        """
        计算宝可梦战斗胜率 (使用蒙特卡洛模拟)
        """
        user_wins = 0
        simulations = 1000  # 运行1000次模拟
        user_moves_list = self.get_moves_list(user_pokemon)
        wild_moves_list = self.get_moves_list(wild_pokemon)

        for _ in range(simulations):
            # 重置模拟的HP
            cur_user_hp = user_pokemon.stats.hp
            cur_wild_hp = wild_pokemon.stats.hp

            turn = 0
            max_turns = 50  # 防止无限循环

            while cur_user_hp > 0 and cur_wild_hp > 0 and turn < max_turns:
                turn += 1
                user_random_move = random.choice(user_moves_list)
                wild_random_move = random.choice(wild_moves_list)
                user_first = self.user_goes_first(
                    user_pokemon.stats.speed,
                    wild_pokemon.stats.speed,
                    user_random_move,
                    wild_random_move
                )

                if user_first:
                    # 用户攻击
                    dmg = self.resolve_damage(user_pokemon, wild_pokemon, user_random_move)
                    cur_wild_hp -= dmg
                    if cur_wild_hp <= 0:
                        user_wins += 1
                        break

                    # 野生宝可梦攻击
                    dmg = self.resolve_damage(wild_pokemon, user_pokemon, wild_random_move)
                    cur_user_hp -= dmg
                else:
                    # 野生宝可梦攻击
                    dmg = self.resolve_damage(wild_pokemon, user_pokemon, wild_random_move)
                    cur_user_hp -= dmg
                    if cur_user_hp <= 0:
                        break  # 用户输了

                    # 用户攻击
                    dmg = self.resolve_damage(user_pokemon, wild_pokemon, user_random_move)
                    cur_wild_hp -= dmg
                    if cur_wild_hp <= 0:
                        user_wins += 1
                        break

        win_rate = (user_wins / simulations) * 100
        return round(win_rate, 1), round(100 - win_rate, 1)

    def calculate_catch_success_rate(self, user_id: str, wild_pokemon: WildPokemonInfo, item_id: str) -> Dict[str, Any]:
        """
        计算捕捉成功率
        Args:
            user_id: 用户ID
            wild_pokemon: 野生宝可梦数据
        Returns:
            float: 捕捉成功率（0-1之间）
        """
        # 检查用户背包中的道具
        user_items: UserItems = self.user_item_repo.get_user_items(user_id)
        pokeball_item = None
        user_item_list = user_items.items
        if item_id is not None:
            # 用户指定了特定的道具ID
            for item in user_item_list:
                if item.item_id == item_id and int(item.category_id) == 34 and item.quantity > 0:
                    pokeball_item = item
                    break
        else:
            # 用户未指定道具ID，自动寻找第一个可用的精灵球
            for item in user_item_list:
                if int(item.category_id) == 34 and item.quantity > 0:
                    pokeball_item = item
                    break

        if not pokeball_item:
            if item_id is not None:
                message = f"❌ 找不到ID为 {item_id} 的精灵球或该道具不存在，无法进行捕捉！请检查道具ID或先通过签到或其他方式获得精灵球。"
            else:
                message = AnswerEnum.USER_POKEBALLS_EMPTY.value
            return {"success": False, "message": message}

        # 根据精灵球类型调整基础捕捉率
        ball_multiplier = 1.0  # 普通精灵球
        if pokeball_item.name_zh == '超级球':
            ball_multiplier = 1.5
        elif pokeball_item.name_zh == '高级球':
            ball_multiplier = 2.0
        elif pokeball_item.name_zh == '大师球':
            ball_multiplier = 255

        # 边界条件：当前HP不能小于0或大于最大HP，基础捕获率范围0~255
        max_hp = wild_pokemon.stats.hp
        # 假设current_hp为随机值，正态分布，均值为最大HP的3/4，标准差为最大HP的1/4
        temp_current_hp = int(random.gauss(max_hp * 3 / 4, max_hp / 4))
        current_hp = max(0, min(max_hp, temp_current_hp))  # 确保在有效范围内
        base_capture_rate = int(self.pokemon_repo.get_pokemon_capture_rate(wild_pokemon.species_id))

        status = "none"
        # 异常状态倍率映射
        status_multipliers = {
            "none": 1.0,
            "paralysis": 1.2,
            "burn": 1.2,
            "poison": 1.2,
            "sleep": 1.5,
            "freeze": 1.5
        }
        status_multi = status_multipliers.get(status.lower(), 1.0)

        # 计算核心公式
        if current_hp == 0:
            catch_value = 0  # 濒死宝可梦无法捕捉
        else:
            hp_term = 3 * max_hp - 2 * current_hp
            numerator = hp_term * base_capture_rate * ball_multiplier * status_multi
            denominator = 3 * max_hp
            catch_value = int(numerator // denominator)  # 向下取整

        # 判定值上限为255（超过则100%成功）
        catch_value = min(catch_value, 255)
        # 计算成功率（随机数0~255，共256种可能）
        success_rate = (catch_value / 256) if catch_value > 0 else 0.0

        return {
            "success": True,
            "message": f"判定值为{catch_value}，捕捉成功率为{round(success_rate, 2)}%",
            "data": {
                "catch_value": catch_value,
                "success_rate": round(success_rate, 2),
                "pokeball_item": pokeball_item,
            }
        }

    def get_battle_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """根据战斗日志ID获取战斗日志"""
        return self.battle_repo.get_battle_log_by_id(log_id)
