import math
import random
from itertools import accumulate
from typing import Dict, Any, List, Tuple

from .exp_service import ExpService
from .pokemon_service import PokemonService
from ..models.common_models import BaseResult
from ...interface.response.answer_enum import AnswerEnum
from ..models.pokemon_models import WildPokemonInfo, PokemonStats, PokemonIVs, PokemonEVs, \
    UserPokemonInfo, WildPokemonEncounterLog, PokemonMoves
from ..models.user_models import UserTeam, UserItems
from ...infrastructure.repositories.abstract_repository import (
    AbstractAdventureRepository, AbstractPokemonRepository, AbstractUserRepository, AbstractTeamRepository
)
from ..models.adventure_models import AdventureResult, LocationInfo, BattleResult
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
            exp_service: ExpService,
            config: Dict[str, Any],
            move_repo = None  # 为兼容性添加，可选参数
    ):
        self.adventure_repo = adventure_repo
        self.pokemon_repo = pokemon_repo
        self.team_repo = team_repo
        self.pokemon_service = pokemon_service
        self.user_repo = user_repo
        self.exp_service = exp_service
        self.config = config
        self.move_repo = move_repo
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

        self.pokemon_repo.add_user_encountered_wild_pokemon(
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
            user_pokemon_info = self.user_repo.get_user_pokemon_by_id(user_id, user_pokemon_id)

            if not user_pokemon_info:
                current_pokemon_index += 1
                continue  # 如果该宝可梦不存在，跳到下一个

            final_user_pokemon_info = user_pokemon_info  # 记录当前战斗的宝可梦信息

            # 计算战斗胜率
            user_win_rate, wild_win_rate = self.calculate_battle_win_rate(user_pokemon_info, wild_pokemon_info)
            all_user_win_rates.append(user_win_rate)
            all_wild_win_rates.append(wild_win_rate)

            # 随机决定战斗结果
            import random
            current_battle_result_str = "success" if random.random() * 100 < user_win_rate else "fail"

            # 记录当前宝可梦的战斗情况
            battle_log.append({
                "pokemon_id": user_pokemon_info.id,
                "pokemon_name": user_pokemon_info.name,
                "species_name": user_pokemon_info.species_id,  # 实际上应该是宝可梦的物种名称，这里暂时使用id
                "level": user_pokemon_info.level,
                "win_rate": user_win_rate,
                "result": current_battle_result_str
            })

            # 如果当前宝可梦获胜，跳出循环
            if current_battle_result_str == "success":
                battle_result = (user_win_rate, wild_win_rate)
                battle_result_str = "success"
                break
            else:
                # 当前宝可梦失败，尝试下一个宝可梦
                current_pokemon_index += 1

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
        recent_encounters: List[WildPokemonEncounterLog] = self.pokemon_repo.get_user_encounters(user_id, limit=5)
        encounter_log_id = None
        for encounter in recent_encounters:
            if (encounter.wild_pokemon_id == wild_pokemon_info.id and
                encounter.is_battled == 0):  # 未战斗的记录
                encounter_log_id = encounter.id
                break
        if encounter_log_id:
            battle_outcome = "win" if battle_result_str == "success" else "lose"
            self.pokemon_repo.update_encounter_log(
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
                battle_log=battle_log
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

    def calculate_battle_win_rate(self, user_pokemon: UserPokemonInfo, wild_pokemon: WildPokemonInfo) -> Tuple[float, float]:
        """
        计算宝可梦战斗胜率 (基于真实伤害公式与击杀回合数模拟)

        Args:
            user_pokemon: 攻击方宝可梦数据
            wild_pokemon: 防御方宝可梦数据
            skill_type: 用户选用的技能类型 ('physical' 或 'special')

        Returns:
            Tuple[float, float]: (攻击方胜率%, 防御方胜率%)
        """

        # ----------------------
        # 辅助函数：标准宝可梦伤害公式
        # ----------------------
        def calculate_damage(attacker_level, atk_stat, def_stat, power, type_effectiveness, stab_bonus=1.0, rand_multiplier=1.0):
            # 宝可梦伤害公式:
            # Damage = ((((2 * Level / 5 + 2) * Attack * Power / Defense) / 50) + 2) * Modifier
            # STAB (Same Type Attack Bonus) 修正：同属性招式伤害增加50%
            # 随机数修正：在0.85到1.0之间浮动

            base_damage = ((2 * attacker_level / 5 + 2) * power * atk_stat / max(1, def_stat)) / 50 + 2
            final_damage = base_damage * type_effectiveness * stab_bonus * rand_multiplier
            return final_damage

        # ----------------------
        # 1. 准备数据
        # ----------------------

        # 获取属性类型
        user_types = self.pokemon_repo.get_pokemon_types(user_pokemon.species_id) or ['normal']
        wild_types = self.pokemon_repo.get_pokemon_types(wild_pokemon.species_id) or ['normal']

        # 为了保持兼容性，计算宝可梦自身的属性克制，但实际伤害计算使用招式的属性克制
        # 玩家对野怪的克制（基于宝可梦属性，但实际用处是招式属性）
        # 野怪对玩家的克制
        # 我们已经在前面的招式选择逻辑中计算了具体招式的克制系数，直接使用即可

        # 在这里不再预先确定攻防属性，而是根据每个招式来确定
        # 玩家：智能选择它较高的攻击属性 (模拟用户使用指定类型中高伤的招式)
        if user_pokemon.stats.attack > user_pokemon.stats.sp_attack:
            preferred_user_atk_stat = 'attack'
        else:
            preferred_user_atk_stat = 'sp_attack'

        # 野怪：智能选择它较高的攻击属性 (模拟野生宝可梦使用本系高攻技能)
        if wild_pokemon.stats.attack > wild_pokemon.stats.sp_attack:
            preferred_wild_atk_stat = 'attack'
        else:
            preferred_wild_atk_stat = 'sp_attack'

        # 初始化用户和野怪的攻防值 - 默认使用基于skill_type的值
        user_atk_val = user_pokemon.stats.attack if preferred_user_atk_stat == 'attack' else user_pokemon.stats.sp_attack
        wild_def_val_for_user = wild_pokemon.stats.defense if preferred_user_atk_stat == 'attack' else wild_pokemon.stats.sp_defense
        wild_atk_val = wild_pokemon.stats.attack if preferred_wild_atk_stat == 'attack' else wild_pokemon.stats.sp_attack
        user_def_val_for_wild = user_pokemon.stats.defense if preferred_wild_atk_stat == 'attack' else user_pokemon.stats.sp_defense

        # 获取宝可梦的招式
        user_moves = [user_pokemon.moves.move1_id, user_pokemon.moves.move2_id,
                      user_pokemon.moves.move3_id, user_pokemon.moves.move4_id]

        # 过滤出有效的招式ID
        valid_user_moves = [move_id for move_id in user_moves if move_id and move_id > 0]

        # 获取玩家招式信息，选择预期伤害最高的招式
        user_move_power = 80  # 默认值
        user_move_type = ''   # 默认值
        user_stab_bonus = 1.0  # STAB加成
        user_type_mod = 1.0  # 招式属性克制系数
        user_move_accuracy = 100.0  # 招式命中率（0-100，转换为0-1之间的值）

        if self.move_repo and valid_user_moves:
            best_damage = 0
            for move_id in valid_user_moves:
                move_info = self.move_repo.get_move_by_id(move_id)
                if move_info:
                    move_damage_class = move_info.get('damage_class_id', 3)  # 3通常代表特殊攻击，2代表物理攻击
                    is_physical = move_damage_class == 2
                    is_special = move_damage_class == 3

                    # 只考虑与攻击类型匹配的招式
                    if (preferred_user_atk_stat == 'attack' and is_physical) or \
                       (preferred_user_atk_stat == 'sp_attack' and is_special):
                        move_power = move_info.get('power', 80)
                        move_type = move_info.get('type_name', '')
                        move_accuracy = move_info.get('accuracy', 100)  # 命中率，如果为None则默认100%

                        # 计算该招式的预期伤害
                        move_atk_val = user_pokemon.stats.attack if is_physical else user_pokemon.stats.sp_attack
                        move_def_val = wild_pokemon.stats.defense if is_physical else wild_pokemon.stats.sp_defense

                        # 计算属性克制系数
                        move_type_effectiveness = self.calculate_type_effectiveness([move_type], wild_types)

                        # 计算STAB加成
                        stab_bonus = 1.5 if move_type in user_types else 1.0

                        # 计算预期伤害（考虑命中率）
                        expected_damage = ((2 * user_pokemon.level / 5 + 2) * move_atk_val * move_power / max(1, move_def_val)) / 50 + 2
                        expected_damage *= move_type_effectiveness * stab_bonus * 0.925  # 0.925是平均随机浮动值
                        # 对于非必中招式，还要乘以命中率
                        if move_accuracy < 100:  # 不是必中招式
                            expected_damage *= move_accuracy / 100.0

                        # 如果这个招式的伤害更高，选择它
                        if expected_damage > best_damage:
                            best_damage = expected_damage
                            user_move_power = move_power
                            user_move_type = move_type
                            user_stab_bonus = stab_bonus
                            user_type_mod = move_type_effectiveness  # 保存招式的属性克制系数
                            user_move_accuracy = move_accuracy  # 保存招式命中率
                            # 保存该招式的攻防类型用于后续的伤害计算
                            user_atk_val = user_pokemon.stats.attack if is_physical else user_pokemon.stats.sp_attack
                            wild_def_val_for_user = wild_pokemon.stats.defense if is_physical else wild_pokemon.stats.sp_defense
                            # Also store the move's damage class for later use
                            user_best_move_is_physical = is_physical

        # 获取野生宝可梦的招式
        wild_moves = [wild_pokemon.moves.move1_id, wild_pokemon.moves.move2_id,
                      wild_pokemon.moves.move3_id, wild_pokemon.moves.move4_id]

        # 过滤出有效的招式ID
        valid_wild_moves = [move_id for move_id in wild_moves if move_id and move_id > 0]

        # 重新初始化野怪的攻击和防御值
        wild_atk_val = wild_pokemon.stats.attack if preferred_wild_atk_stat == 'attack' else wild_pokemon.stats.sp_attack
        user_def_val_for_wild = user_pokemon.stats.defense if preferred_wild_atk_stat == 'attack' else user_pokemon.stats.sp_defense

        # 获取野怪招式信息，计算综合伤害
        wild_move_power = 80  # 默认值
        wild_move_type = ''   # 默认值
        wild_stab_bonus = 1.0  # STAB加成
        wild_type_mod = 1.0  # 招式属性克制系数
        wild_move_accuracy = 100.0  # 招式命中率（0-100，转换为0-1之间的值）

        # 初始化野怪的伤害计算所需的变量
        min_damage_to_user = 0  # 最小伤害
        avg_damage_to_user = 0  # 平均伤害
        max_damage_to_user = 0  # 最大伤害
        wild_damage_calculated = False  # 标记是否已经计算了野怪的伤害

        if self.move_repo and valid_wild_moves:
            total_min_damage = 0
            total_avg_damage = 0
            total_max_damage = 0
            valid_move_count = 0

            # 为了模拟野怪的攻击偏重，我们根据野怪的攻击属性来决定使用哪种类型的招式
            prefers_physical = wild_pokemon.stats.attack >= wild_pokemon.stats.sp_attack
            preferred_skill_type = 'physical' if prefers_physical else 'special'

            for move_id in valid_wild_moves:
                move_info = self.move_repo.get_move_by_id(move_id)
                if move_info:
                    move_damage_class = move_info.get('damage_class_id', 3)  # 3通常代表特殊攻击，2代表物理攻击
                    is_physical = move_damage_class == 2
                    is_special = move_damage_class == 3

                    # 只考虑与攻击类型匹配的招式（根据野怪偏向的攻击类型）
                    if (preferred_skill_type == 'physical' and is_physical) or (preferred_skill_type == 'special' and is_special):
                        move_power = move_info.get('power', 80)
                        move_type = move_info.get('type_name', '')
                        move_accuracy = move_info.get('accuracy', 100)  # 命中率，如果为None则默认100%

                        # 根据招式的实际类型计算攻防值
                        move_atk_val = wild_pokemon.stats.attack if is_physical else wild_pokemon.stats.sp_attack
                        move_def_val = user_pokemon.stats.defense if is_physical else user_pokemon.stats.sp_defense

                        # 计算属性克制系数
                        move_type_effectiveness = self.calculate_type_effectiveness([move_type], user_types)

                        # 计算STAB加成
                        stab_bonus = 1.5 if move_type in wild_types else 1.0

                        # 计算不同随机系数下的伤害
                        min_damage = ((2 * wild_pokemon.level / 5 + 2) * move_atk_val * move_power / max(1, move_def_val)) / 50 + 2
                        min_damage *= move_type_effectiveness * stab_bonus * 0.85  # 最小随机系数
                        # 对于非必中招式，还要乘以命中率
                        if move_accuracy < 100:  # 不是必中招式
                            min_damage *= move_accuracy / 100.0

                        avg_damage = ((2 * wild_pokemon.level / 5 + 2) * move_atk_val * move_power / max(1, move_def_val)) / 50 + 2
                        avg_damage *= move_type_effectiveness * stab_bonus * 0.925  # 平均随机系数
                        if move_accuracy < 100:
                            avg_damage *= move_accuracy / 100.0

                        max_damage = ((2 * wild_pokemon.level / 5 + 2) * move_atk_val * move_power / max(1, move_def_val)) / 50 + 2
                        max_damage *= move_type_effectiveness * stab_bonus * 1.0  # 最大随机系数
                        if move_accuracy < 100:
                            max_damage *= move_accuracy / 100.0

                        # 累加到总和中，用于后续平均
                        total_min_damage += min_damage
                        total_avg_damage += avg_damage
                        total_max_damage += max_damage
                        valid_move_count += 1

            # 如果有有效的招式，使用平均伤害来反映野怪的真实攻击能力
            if valid_move_count > 0:
                # 计算平均伤害，模拟野怪随机使用技能的特性
                min_damage_to_user = total_min_damage / valid_move_count
                avg_damage_to_user = total_avg_damage / valid_move_count
                max_damage_to_user = total_max_damage / valid_move_count
                wild_damage_calculated = True

                # 还是设置一个代表性的招式用于后面的属性克制等信息（为了保持兼容性）
                # 选择第一个有效招式作为代表
                first_move_id = [mid for mid in valid_wild_moves
                                if self.move_repo.get_move_by_id(mid) and
                                ((preferred_skill_type == 'physical' and self.move_repo.get_move_by_id(mid).get('damage_class_id', 3) == 2) or
                                 (preferred_skill_type == 'special' and self.move_repo.get_move_by_id(mid).get('damage_class_id', 3) == 3))][0] if any(self.move_repo.get_move_by_id(mid) and
                                ((preferred_skill_type == 'physical' and self.move_repo.get_move_by_id(mid).get('damage_class_id', 3) == 2) or
                                 (preferred_skill_type == 'special' and self.move_repo.get_move_by_id(mid).get('damage_class_id', 3) == 3)) for mid in valid_wild_moves) else valid_wild_moves[0] if valid_wild_moves else None

                if first_move_id and self.move_repo.get_move_by_id(first_move_id):
                    first_move_info = self.move_repo.get_move_by_id(first_move_id)
                    wild_move_power = first_move_info.get('power', 80)
                    wild_move_type = first_move_info.get('type_name', '')
                    wild_move_accuracy = first_move_info.get('accuracy', 100)
                    # 重新计算该招式的属性加成
                    wild_type_mod = self.calculate_type_effectiveness([wild_move_type], user_types)
                    wild_stab_bonus = 1.5 if wild_move_type in wild_types else 1.0
                    # 重新计算攻防值
                    move_damage_class = first_move_info.get('damage_class_id', 3)  # 3通常代表特殊攻击，2代表物理攻击
                    is_wild_move_physical = move_damage_class == 2
                    wild_atk_val = wild_pokemon.stats.attack if is_wild_move_physical else wild_pokemon.stats.sp_attack
                    user_def_val_for_wild = user_pokemon.stats.defense if is_wild_move_physical else user_pokemon.stats.sp_defense
        else:
            # 如果没有move_repo或野怪没有招式，使用原始逻辑
            # 模拟野怪使用其类型的招式
            if wild_types:
                # 选择野怪类型中的一个作为招式类型（使用第一个）
                wild_move_type = wild_types[0]
                # 如果野怪招式类型与野怪属性相同，则有STAB加成
                if wild_move_type in wild_types:
                    wild_stab_bonus = 1.5
                    # 计算属性克制
                    wild_type_mod = self.calculate_type_effectiveness(wild_types, user_types)
                else:
                    wild_type_mod = self.calculate_type_effectiveness(wild_types, user_types)
                # 设置默认命中率
                wild_move_accuracy = 100.0  # 默认为100%
            # Default attack and defense values
            wild_atk_val = wild_pokemon.stats.attack if preferred_wild_atk_stat == 'attack' else wild_pokemon.stats.sp_attack
            user_def_val_for_wild = user_pokemon.stats.defense if preferred_wild_atk_stat == 'attack' else user_pokemon.stats.sp_defense

        # ----------------------
        # 2. 计算每回合伤害 (DPT) - 考虑随机波动
        # ----------------------

        # 计算玩家对野怪的伤害：最小、平均、最大
        min_damage_to_wild = calculate_damage(
            user_pokemon.level, user_atk_val, wild_def_val_for_user, user_move_power, user_type_mod, user_stab_bonus, 0.85
        )
        avg_damage_to_wild = calculate_damage(
            user_pokemon.level, user_atk_val, wild_def_val_for_user, user_move_power, user_type_mod, user_stab_bonus, 0.925
        )
        max_damage_to_wild = calculate_damage(
            user_pokemon.level, user_atk_val, wild_def_val_for_user, user_move_power, user_type_mod, user_stab_bonus, 1.0
        )

        # 计算野怪对玩家的伤害：最小、平均、最大
        # 如果已计算过野怪伤害，则使用计算好的值，否则使用单次计算
        if not wild_damage_calculated:
            min_damage_to_user = calculate_damage(
                wild_pokemon.level, wild_atk_val, user_def_val_for_wild, wild_move_power, wild_type_mod, wild_stab_bonus, 0.85
            )
            avg_damage_to_user = calculate_damage(
                wild_pokemon.level, wild_atk_val, user_def_val_for_wild, wild_move_power, wild_type_mod, wild_stab_bonus, 0.925
            )
            max_damage_to_user = calculate_damage(
                wild_pokemon.level, wild_atk_val, user_def_val_for_wild, wild_move_power, wild_type_mod, wild_stab_bonus, 1.0
            )
        # 否则，使用已经计算好的伤害值（在野怪招式循环中计算的）
        # 此时 min_damage_to_user, avg_damage_to_user, max_damage_to_user 已经被设置

        # ----------------------
        # 3. 计算击杀所需回合数 (Turns to Kill) - 考虑斩杀线波动
        # ----------------------

        # HP 修正：确保 HP 至少为 1
        user_hp = max(1, user_pokemon.stats.hp)
        wild_hp = max(1, wild_pokemon.stats.hp)

        # 检查是否可以一击必杀（最大伤害 >= 对方HP），同时考虑命中率
        user_can_ohko = max_damage_to_wild >= wild_hp
        wild_can_ohko = max_damage_to_user >= user_hp

        # 初始化win_score
        win_score = 0.0

        # 如果有一方可一击必杀，计算其成功概率，同时考虑命中率
        if user_can_ohko and not wild_can_ohko:
            # 用户可以一击必杀，但野怪不能
            # 考虑用户先手优势和命中率
            effective_user_ohko_chance = 1.0
            if user_move_accuracy < 100:  # 如果不是必中招式
                effective_user_ohko_chance = user_move_accuracy / 100.0

            if user_pokemon.stats.speed >= wild_pokemon.stats.speed:
                # 用户先手，计算一击必杀的概率
                if max_damage_to_wild >= wild_hp and min_damage_to_wild < wild_hp:
                    # 介于HP和最大伤害之间，计算精确击杀概率
                    ohko_chance = (max_damage_to_wild - wild_hp) / (max_damage_to_wild - min_damage_to_wild)
                    win_score = ohko_chance * effective_user_ohko_chance * 3.0  # 结合命中率
                else:
                    # 肯定能击杀或肯定不能击杀
                    base_chance = 1.0 if max_damage_to_wild >= wild_hp else 0.0
                    win_score = base_chance * effective_user_ohko_chance * 3.0  # 结合命中率
            else:
                # 野怪先手，用户需要活过第一轮，然后反击击杀
                if max_damage_to_user >= user_hp:
                    # 野怪可以一击必杀
                    wild_ohko_chance = 1.0 if min_damage_to_user >= user_hp else (
                        (max_damage_to_user - user_hp) / (max_damage_to_user - min_damage_to_user)
                        if max_damage_to_user > min_damage_to_user else 0.0
                    )
                    user_survive_chance = 1.0 - wild_ohko_chance
                else:
                    user_survive_chance = 1.0

                # 如果用户活过第一轮，再计算反击击杀概率，结合命中率
                if user_survive_chance > 0:
                    user_ohko_chance = 0.0
                    if max_damage_to_wild >= wild_hp:
                        user_ohko_chance = 1.0 if min_damage_to_wild >= wild_hp else (
                            (max_damage_to_wild - wild_hp) / (max_damage_to_wild - min_damage_to_wild)
                            if max_damage_to_wild > min_damage_to_wild else 0.0
                        )
                    # 考虑反击招式的命中率
                    effective_user_ohko_chance = user_ohko_chance * (user_move_accuracy / 100.0)
                    win_score = user_survive_chance * effective_user_ohko_chance * 2.0
                else:
                    win_score = -3.0 * (wild_move_accuracy / 100.0)  # 野怪必定先手击杀（考虑命中率）

        elif wild_can_ohko and not user_can_ohko:
            # 野怪可以一击必杀，但用户不能
            effective_wild_ohko_chance = 1.0
            if wild_move_accuracy < 100:  # 如果不是必中招式
                effective_wild_ohko_chance = wild_move_accuracy / 100.0

            if wild_pokemon.stats.speed >= user_pokemon.stats.speed:
                # 野怪先手，计算击杀概率
                wild_ohko_chance = 0.0
                if max_damage_to_user >= user_hp:
                    wild_ohko_chance = 1.0 if min_damage_to_user >= user_hp else (
                        (max_damage_to_user - user_hp) / (max_damage_to_user - min_damage_to_user)
                        if max_damage_to_user > min_damage_to_user else 0.0
                    )
                win_score = -wild_ohko_chance * effective_wild_ohko_chance * 3.0  # 结合命中率
            else:
                # 用户先手，需要击杀或活过野怪第一轮
                user_kill_chance = 0.0
                if max_damage_to_wild >= wild_hp:
                    user_kill_chance = 1.0 if min_damage_to_wild >= wild_hp else (
                        (max_damage_to_wild - wild_hp) / (max_damage_to_wild - min_damage_to_wild)
                        if max_damage_to_wild > min_damage_to_wild else 0.0
                    )
                # 考虑用户招式的命中率
                effective_user_kill_chance = user_kill_chance * (user_move_accuracy / 100.0)

                # 野怪一击必杀概率
                wild_ohko_chance = 0.0
                if max_damage_to_user >= user_hp:
                    wild_ohko_chance = 1.0 if min_damage_to_user >= user_hp else (
                        (max_damage_to_user - user_hp) / (max_damage_to_user - min_damage_to_user)
                        if max_damage_to_user > min_damage_to_user else 0.0
                    )
                # 考虑野怪招式的命中率
                effective_wild_ohko_chance_for_prob = wild_ohko_chance * (wild_move_accuracy / 100.0)

                # 用户胜率 = 先手击杀率 + (活过第一轮率 * 后续击杀率)
                user_win_rate = effective_user_kill_chance + (1 - effective_wild_ohko_chance_for_prob) * effective_user_kill_chance
                wild_win_rate = effective_wild_ohko_chance_for_prob
                win_score = (user_win_rate - wild_win_rate) * 2.0

        elif user_can_ohko and wild_can_ohko:
            # 双方都可能一击必杀，比较速度
            if user_pokemon.stats.speed > wild_pokemon.stats.speed:
                # 用户先手，必定先攻击
                user_ohko_chance = 1.0 if min_damage_to_wild >= wild_hp else (
                    (max_damage_to_wild - wild_hp) / (max_damage_to_wild - min_damage_to_wild)
                    if max_damage_to_wild > min_damage_to_wild else 0.0
                ) if max_damage_to_wild >= wild_hp else 0.0
                # 考虑用户招式的命中率
                effective_user_ohko_chance = user_ohko_chance * (user_move_accuracy / 100.0)
                win_score = effective_user_ohko_chance * 2.0
            elif wild_pokemon.stats.speed > user_pokemon.stats.speed:
                # 野怪先手，用户败
                wild_ohko_chance = 1.0 if min_damage_to_user >= user_hp else (
                    (max_damage_to_user - user_hp) / (max_damage_to_user - min_damage_to_user)
                    if max_damage_to_user > min_damage_to_user else 0.0
                ) if max_damage_to_user >= user_hp else 0.0
                # 考虑野怪招式的命中率
                effective_wild_ohko_chance = wild_ohko_chance * (wild_move_accuracy / 100.0)
                win_score = -effective_wild_ohko_chance * 2.0
            else:
                # 速度相同，各50%先手概率
                user_ohko_chance = 1.0 if min_damage_to_wild >= wild_hp else (
                    (max_damage_to_wild - wild_hp) / (max_damage_to_wild - min_damage_to_wild)
                    if max_damage_to_wild > min_damage_to_wild else 0.0
                ) if max_damage_to_wild >= wild_hp else 0.0
                wild_ohko_chance = 1.0 if min_damage_to_user >= user_hp else (
                    (max_damage_to_user - user_hp) / (max_damage_to_user - min_damage_to_user)
                    if max_damage_to_user > min_damage_to_user else 0.0
                ) if max_damage_to_user >= user_hp else 0.0

                # 考虑命中率
                effective_user_ohko_chance = user_ohko_chance * (user_move_accuracy / 100.0)
                effective_wild_ohko_chance = wild_ohko_chance * (wild_move_accuracy / 100.0)

                # 各50%先手，计算期望胜率
                user_first_win = effective_user_ohko_chance
                wild_first_win = effective_wild_ohko_chance
                win_score = (user_first_win - wild_first_win) * 1.0
        else:
            # 正常战斗情况，没有一击必杀
            # 考虑命中率对平均伤害的影响
            avg_damage_to_wild_with_accuracy = avg_damage_to_wild * (user_move_accuracy / 100.0)
            avg_damage_to_user_with_accuracy = avg_damage_to_user * (wild_move_accuracy / 100.0)

            # 玩家打死野怪需要几下？ (向上取整)
            # 使用考虑命中率的平均伤害
            avg_turns_to_kill_wild = math.ceil(wild_hp / max(1, avg_damage_to_wild_with_accuracy)) if avg_damage_to_wild_with_accuracy > 0 else float('inf')

            # 野怪打死玩家需要几下？
            avg_turns_to_kill_user = math.ceil(user_hp / max(1, avg_damage_to_user_with_accuracy)) if avg_damage_to_user_with_accuracy > 0 else float('inf')

            # 使用平均回合数作为主要参考
            turns_to_kill_wild = avg_turns_to_kill_wild
            turns_to_kill_user = avg_turns_to_kill_user

            # 情况 A: 玩家斩杀回合数 明显少于 野怪 -> 必胜
            if turns_to_kill_wild < turns_to_kill_user:
                # 优势巨大
                win_score = 2.0 + (turns_to_kill_user - turns_to_kill_wild)

                # 情况 B: 野怪斩杀回合数 明显少于 玩家 -> 必败
            elif turns_to_kill_wild > turns_to_kill_user:
                win_score = -2.0 - (turns_to_kill_wild - turns_to_kill_user)

            # 情况 C: 斩杀回合数相同 (例如都要 3 刀死) -> 拼速度
            else:  # turns_to_kill_wild == turns_to_kill_user
                if user_pokemon.stats.speed > wild_pokemon.stats.speed:
                    # 我先手，我先打出第 N 刀 -> 我赢
                    win_score = 1.5  # 速度优势
                elif user_pokemon.stats.speed < wild_pokemon.stats.speed:
                    # 对面先手，对面先打出第 N 刀 -> 我输
                    win_score = -1.5  # 速度劣势
                else:
                    # 同速，纯随机
                    win_score = 0.0

            # 考虑伤害波动对胜率的影响，结合命中率
            adjusted_damage_ratio = (avg_damage_to_wild * (user_move_accuracy / 100.0)) / max(1, avg_damage_to_user * (wild_move_accuracy / 100.0))
            if adjusted_damage_ratio > 1.5:
                # 用户伤害远高于野怪，胜率增加
                win_score += (adjusted_damage_ratio - 1.0) * 0.5
            elif adjusted_damage_ratio < 2/3:
                # 用户伤害远低于野怪，败率增加
                win_score -= (1.0 - adjusted_damage_ratio) * 0.5

        # ----------------------
        # 4. 引入随机性 (Crit, Miss, Damage Roll) 并平滑胜率
        # ----------------------

        # 使用 Sigmoid 函数将 win_score 映射到 0-1
        # 调整 coefficient (0.8) 可以控制胜率曲线的陡峭程度
        # score = 0 -> 50%
        # score = 2 -> 83%
        # score = -2 -> 16%

        sigmoid_k = 0.8
        base_win_rate = 1 / (1 + math.exp(-sigmoid_k * win_score))

        # 考虑命中率和暴击的干扰 (95% 命中, 6.25% 暴击)
        # 我们不进行模拟，而是将胜率向 50% 收缩一点点，表示意外发生的可能性
        # 比如 99% 的胜率修正为 98%，保留一点翻车概率

        final_win_rate = base_win_rate * 0.96 + 0.02  # 压缩区间到 [2%, 98%]

        return round(final_win_rate * 100, 1), round((1 - final_win_rate) * 100, 1)

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
        user_items:UserItems = self.user_repo.get_user_items(user_id)
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
