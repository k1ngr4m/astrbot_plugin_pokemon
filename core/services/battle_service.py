import math
from typing import Dict, Any, Tuple, List

from ..domain.pokemon_models import WildPokemonInfo, UserPokemonInfo
from ..domain.user_models import UserTeam
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository,
)

from .exp_service import ExpService

class BattleService:
    """
    封装宝可梦战斗相关的业务逻辑
    包含属性克制计算、战力评分模型和胜率计算
    """

    def __init__(
        self,
        user_repo: AbstractUserRepository,
        pokemon_repo: AbstractPokemonRepository,
        team_repo,
        config: Dict[str, Any],
        exp_service = ExpService
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.team_repo = team_repo
        self.config = config
        self.exp_service = exp_service

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


    def calculate_battle_win_rate(
        self,
        user_pokemon: UserPokemonInfo,
        wild_pokemon: WildPokemonInfo,
        skill_type: str = 'special'
    ) -> Tuple[float, float]:
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