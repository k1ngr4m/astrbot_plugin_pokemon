import math
import random
from itertools import accumulate
from typing import Dict, Any, List, Tuple

from .exp_service import ExpService
from .pokemon_service import PokemonService
from ..models.common_models import BaseResult
from ...interface.response.answer_enum import AnswerEnum
from ..models.pokemon_models import WildPokemonInfo, PokemonStats, PokemonIVs, PokemonEVs, \
    UserPokemonInfo, WildPokemonEncounterLog
from ..models.user_models import UserTeam, UserItems
from ...infrastructure.repositories.abstract_repository import (
    AbstractAdventureRepository, AbstractPokemonRepository, AbstractUserRepository, AbstractTeamRepository
)
from ..models.adventure_models import AdventureResult, LocationInfo
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
            config: Dict[str, Any]
    ):
        self.adventure_repo = adventure_repo
        self.pokemon_repo = pokemon_repo
        self.team_repo = team_repo
        self.pokemon_service = pokemon_service
        self.user_repo = user_repo
        self.exp_service = exp_service
        self.config = config
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
            message=AnswerEnum.ADVENTURE_LOCATIONS_FOUND.value.format(len(formatted_locations)),
            data=formatted_locations
        )


    def adventure_in_location(self, user_id: str, location_id: int) -> AdventureResult:
        """
        在指定区域进行冒险，随机刷新一只野生宝可梦
        Args:
            user_id: 用户ID
            location_id: 区域ID
        Returns:
            包含冒险结果的字典
        """
        # 统一错误返回函数（减少重复代码）
        def error_response(message: str) -> AdventureResult:
            return AdventureResult(
                success=False,
                message=message,
                wild_pokemon=None,
                location=None
            )
        try:
            # 3. 获取区域信息
            location = self.adventure_repo.get_location_by_id(location_id)
            if not location:
                return error_response(f"未找到区域 {location_id}")
            # 4. 获取该区域的宝可梦列表
            location_pokemon_list = self.adventure_repo.get_location_pokemon_by_location_id(location_id)
            if not location_pokemon_list:
                return error_response(f"区域 {location.name} 中暂无野生宝可梦")
            # 5. 权重随机选择宝可梦（使用itertools.accumulate简化累加逻辑）
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

            # 6. 生成宝可梦等级（使用变量名简化赋值）
            min_level = selected_location_pokemon.min_level
            max_level = selected_location_pokemon.max_level
            wild_pokemon_level = random.randint(min_level, max_level)
            # 7. 创建野生宝可梦（直接使用返回结果，无需额外处理）
            wild_pokemon_result = self.pokemon_service.create_single_pokemon(
                species_id=selected_location_pokemon.pokemon_species_id,
                max_level=wild_pokemon_level,
                min_level=wild_pokemon_level
            )
            if not wild_pokemon_result.success:
                return error_response(wild_pokemon_result.message)
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
                    moves = None,
            )
            wild_pokemon_id = self.pokemon_repo.add_wild_pokemon(wild_pokemon_info)

            self.pokemon_repo.add_user_encountered_wild_pokemon(
                user_id=user_id,
                wild_pokemon_id = wild_pokemon_id,
                location_id=location.id,
                encounter_rate=selected_location_pokemon.encounter_rate,
            )



            # 8. 构造返回结果（直接复用create_single_pokemon的计算结果）
            result = AdventureResult(
                success=True,
                message=f"在 {location.name} 中遇到了野生的 {wild_pokemon_info.name}！",
                wild_pokemon=wild_pokemon_info,
                location=LocationInfo(
                    location_id=location.id,
                    location_name=location.name,
                )
            )
            return result

        except Exception as e:
            return error_response(f"冒险过程中发生错误: {str(e)}")

    def adventure_in_battle(self, user_id: str, wild_pokemon_info: WildPokemonInfo) -> Dict[str, Any]:
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
            return {
                "success": False,
                "message": AnswerEnum.USER_TEAM_NOT_SET.value,
            }

        user_team_list: List[int] = user_team_data.team_pokemon_ids

        # 开始战斗，传入玩家的队伍
        result = self.start_battle(user_id, wild_pokemon_info, user_team_list)
        if result["success"]:
            battle_details = result["battle_details"]
            user_pokemon = battle_details["user_pokemon"]
            wild_pokemon_data = battle_details["wild_pokemon"]
            win_rates = battle_details["win_rates"]
            battle_result = "胜利" if battle_details["result"] == "success" else "失败"
            exp_details = battle_details["exp_details"]

            message = "⚔️ 宝可梦战斗开始！\n\n"
            message += f"👤 我方宝可梦: {user_pokemon['name']} (Lv.{user_pokemon['level']})\n"
            message += f"野生宝可梦: {wild_pokemon_data['name']} (Lv.{wild_pokemon_data['level']})\n\n"

            message += "📊 战斗胜率分析:\n"
            message += f"我方胜率: {win_rates['user_win_rate']}%\n"
            message += f"野生胜率: {win_rates['wild_win_rate']}%\n\n"

            message += f"🎯 战斗结果: {battle_result}\n"

            # 添加经验值信息
            if exp_details:
                team_pokemon_results = exp_details.get("team_pokemon_results", [])
                user_exp_info = exp_details.get("user_exp", {})

                if team_pokemon_results:
                    message += f"\n📈 经验值获取:\n"
                    for i, pokemon_result in enumerate(team_pokemon_results):
                        if pokemon_result.get("success"):
                            exp_gained = pokemon_result.get("exp_gained", 0)
                            pokemon_name = pokemon_result.get("pokemon_name", f"宝可梦{i+1}")
                            message += f"  {pokemon_name} 获得了 {exp_gained} 点经验值\n"

                            level_up_info = pokemon_result.get("level_up_info", {})
                            if level_up_info.get("should_level_up"):
                                levels_gained = level_up_info.get("levels_gained", 0)
                                new_level = level_up_info.get("new_level", 0)
                                message += f"  🎉 恭喜 {pokemon_name} 升级了！等级提升 {levels_gained} 级，现在是 {new_level} 级！\n"

                if user_exp_info.get("success"):
                    user_exp_gained = user_exp_info.get("exp_gained", 0)
                    if user_exp_gained > 0:  # 只有在获得经验时才显示
                        user_levels_gained = user_exp_info.get("levels_gained", 0)
                        new_user_level = user_exp_info.get("new_level", user.level)
                        message += f"  训练家获得了 {user_exp_gained} 点经验值"
                        if user_levels_gained > 0:
                            message += f"，等级提升 {user_levels_gained} 级，现在是 {new_user_level} 级！\n"
                        else:
                            message += "\n"

            # 更新野生宝可梦遇到日志 - 标记为已战斗
            try:
                # 获取最近的野生宝可梦遇到记录
                recent_encounters: List[WildPokemonEncounterLog] = self.pokemon_repo.get_user_encounters(user_id, limit=5)
                encounter_log_id = None
                for encounter in recent_encounters:
                    if (encounter.wild_pokemon_id == wild_pokemon_info.id and
                        encounter.is_battled == 0):  # 未战斗的记录
                        encounter_log_id = encounter.id
                        break
                if encounter_log_id:
                    battle_outcome = "win" if "胜利" in battle_result else "lose"
                    self.pokemon_repo.update_encounter_log(
                        log_id=encounter_log_id,
                        is_battled=1,
                        battle_result=battle_outcome
                    )
                return {
                    "success": True,
                    "message": message,
                }
            except Exception as e:
                logger.error(f"更新野生宝可梦遇到日志（战斗）时出错: {e}")
                return {
                    "success": False,
                    "message": "更新野生宝可梦遇到日志（战斗）时出错",
                }

    def start_battle(self, user_id: str, wild_pokemon_info: WildPokemonInfo, user_team_list: List[int] = None) -> Dict[str, Any]:
        """
        开始一场与野生宝可梦的战斗
        Args:
            user_id: 用户ID
            wild_pokemon_info: 野生宝可梦数据
            user_team_list: 用户队伍中的宝可梦ID列表
        Returns:
            包含战斗结果的字典
        """
        try:
            user_pokemon_id = user_team_list[0]
            user_pokemon_info = self.user_repo.get_user_pokemon_by_id(user_id, user_pokemon_id)
            # 计算战斗胜率
            user_win_rate, wild_win_rate = self.calculate_battle_win_rate(user_pokemon_info, wild_pokemon_info)

            # 随机决定战斗结果
            import random
            result = "success" if random.random() * 100 < user_win_rate else "fail"

            # 处理经验值（仅在胜利时）
            exp_details = {}
            if self.exp_service and result == "success":
                # 计算宝可梦获得的经验值
                pokemon_exp_gained = self.exp_service.calculate_pokemon_exp_gain(wild_pokemon_id=wild_pokemon_info.id, wild_pokemon_level=wild_pokemon_info.level, battle_result=result)
                # user_exp_gained = self.exp_service.calculate_user_exp_gain(wild_pokemon_info.level, result)
                # 获取用户队伍中的所有宝可梦
                user_team_data:UserTeam = self.team_repo.get_user_team(user_id)
                team_pokemon_results = []
                team_pokemon_ids=user_team_data.team_pokemon_ids
                # 更新队伍中所有宝可梦的经验值
                if team_pokemon_ids:
                    team_pokemon_results = self.exp_service.update_team_pokemon_after_battle(
                        user_id, team_pokemon_ids, pokemon_exp_gained)

                # 更新用户经验值（如果用户获得经验）
                # user_update_result = {"success": True, "exp_gained": 0}
                # if user_exp_gained > 0:
                #     user_update_result = self.exp_service.update_user_after_battle(user_id, user_exp_gained)

                exp_details = {
                    "pokemon_exp": team_pokemon_results[0] if team_pokemon_results else {"success": False, "message": "未找到队伍中的宝可梦"},
                    # "user_exp": user_update_result,
                    "team_pokemon_results": team_pokemon_results
                }
            elif self.exp_service and result != "success":
                # 战斗失败时不获得经验
                exp_details = {
                    "pokemon_exp": {"success": True, "exp_gained": 0, "message": "战斗失败，未获得经验值"},
                    "user_exp": {"success": True, "exp_gained": 0, "message": "战斗失败，未获得经验值"},
                    "team_pokemon_results": []
                }

            # 返回战斗结果
            battle_result = {
                "success": True,
                "message": f"战斗结束！用户宝可梦 {user_pokemon_info.name} vs 野生宝可梦 {wild_pokemon_info.name}",
                "battle_details": {
                    "user_pokemon": {
                        "name": user_pokemon_info.name,
                        "species": user_pokemon_info.species_id,
                        "level": user_pokemon_info.level,
                        "hp": user_pokemon_info.stats.hp,
                        "attack": user_pokemon_info.stats.attack,
                        "defense": user_pokemon_info.stats.defense,
                        "speed": user_pokemon_info.stats.speed
                    },
                    "wild_pokemon": {
                        "name": wild_pokemon_info.name,
                        "level": wild_pokemon_info.level,
                        "hp": wild_pokemon_info.stats.hp,
                        "attack": wild_pokemon_info.stats.attack,
                        "defense": wild_pokemon_info.stats.defense,
                        "speed": wild_pokemon_info.stats.speed
                    },
                    "win_rates": {
                        "user_win_rate": user_win_rate,
                        "wild_win_rate": wild_win_rate
                    },
                    "result": result,
                    "exp_details": exp_details
                }
            }
            return battle_result

        except Exception as e:
            return {
                "success": False,
                "message": f"战斗过程中发生错误: {str(e)}"
            }

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

    def calculate_battle_win_rate(self, user_pokemon: UserPokemonInfo, wild_pokemon: WildPokemonInfo, skill_type: str = 'special') -> Tuple[float, float]:
        """
        计算宝可梦战斗胜率
        Args:
            user_pokemon: 攻击方宝可梦数据
            wild_pokemon: 防御方宝可梦数据
            skill_type: 技能类型 ('physical' 或 'special')，决定使用攻击/防御还是特攻/特防
        Returns:
            Tuple[float, float]: (攻击方胜率%, 防御方胜率%)
        """
        # 获取宝可梦的属性类型
        user_pokemon_types = self.pokemon_repo.get_pokemon_types(user_pokemon.species_id)
        wild_pokemon_types = self.pokemon_repo.get_pokemon_types(wild_pokemon.species_id)
        # 如果获取不到类型数据，使用默认的普通属性
        if not user_pokemon_types:
            user_pokemon_types = ['normal']
        if not wild_pokemon_types:
            wild_pokemon_types = ['normal']

        # ----------------------
        # 步骤1：计算属性克制系数（攻击方对防御方的总克制系数）
        # ----------------------
        self_type_modifier = self.calculate_type_effectiveness(user_pokemon_types, wild_pokemon_types)
        # 防御方对攻击方的克制系数
        opp_type_modifier = self.calculate_type_effectiveness(wild_pokemon_types, user_pokemon_types)
        # ----------------------
        # 步骤2：计算攻防能力（结合等级、属性修正）
        # ----------------------

        # 攻击方输出属性：按技能类型选择
        atk_stat_attacker = 'attack' if skill_type == 'physical' else 'sp_attack'
        # 防御方输出属性：取自身物攻和特攻的最大值（贴合实际定位）
        atk_stat_defender = 'attack' if wild_pokemon.stats.attack > wild_pokemon.stats.sp_attack else 'sp_attack'
        def_stat = 'defense' if skill_type == 'physical' else 'sp_defense'
        # 等级修正系数（等级差距影响，避免碾压）
        self_level_mod = user_pokemon.level / 50  # 等级50修正1.0，等级100修正2.0，等级25修正0.5
        opp_level_mod = wild_pokemon.level / 50

        # 攻击方输出能力 = 攻击属性值 × 等级修正 × 属性克制系数
        self_offense = user_pokemon.stats[atk_stat_attacker] * self_level_mod * self_type_modifier
        opp_offense = wild_pokemon.stats[atk_stat_defender] * opp_level_mod * opp_type_modifier  # 防御方用自己的核心输出属性
        # 防御方承伤能力 = 防御属性值 × 等级修正
        self_defense = user_pokemon.stats[def_stat] * self_level_mod
        opp_defense = wild_pokemon.stats[def_stat] * opp_level_mod

        # 有效战力 = 输出能力 / 承伤能力（比值越大，战力越强）
        self_effective_power = self_offense / self_defense if self_defense > 0 else 0
        opp_effective_power = opp_offense / opp_defense if opp_defense > 0 else 0
        # ----------------------
        # 步骤3：速度先手权修正（速度快的获得额外战力加成）
        # ----------------------
        speed_ratio = user_pokemon.stats.speed / max(wild_pokemon.stats.speed, 1)
        self_speed_bonus = 0.0  # 初始化，避免未定义
        opp_speed_bonus = 0.0

        if speed_ratio > 1.0:
            # 用对数缩放，速度比1.5时加成≈8%，速度比2.0时加成≈10%，更平滑
            self_speed_bonus = min(0.1, math.log(speed_ratio) * 0.15)
            self_effective_power *= (1 + self_speed_bonus)  # 关键：用加成放大攻击方战力

        elif speed_ratio < 1.0:
            opp_speed_bonus = min(0.1, math.log(1 / speed_ratio) * 0.15)
            opp_effective_power *= (1 + opp_speed_bonus)  # 关键：用加成放大防御方战力

        # ----------------------
        # 步骤4：换算胜率（基于战力比，用Sigmoid函数平滑映射到0-1）
        # ----------------------
        power_diff = self_effective_power - opp_effective_power
        # Sigmoid函数：将差值映射到0-1，斜率控制胜率对战力差的敏感度（0.15为经验值）
        self_win_rate = 1 / (1 + math.exp(-0.15 * power_diff))
        # 修正极端胜率（避免0%或100%，保留随机性）
        self_win_rate = max(0.05, min(0.95, self_win_rate))
        opp_win_rate = 1 - self_win_rate
        return round(self_win_rate * 100, 1), round(opp_win_rate * 100, 1)

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
