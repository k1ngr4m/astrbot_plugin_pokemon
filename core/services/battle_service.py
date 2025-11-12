import math
from typing import Dict, Any, Tuple, List
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository,
)

class BattleService:
    """
    封装宝可梦战斗相关的业务逻辑
    包含属性克制计算、战力评分模型和胜率计算
    """

    def __init__(
        self,
        user_repo: AbstractUserRepository,
        pokemon_repo: AbstractPokemonRepository,
        config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
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
        attacker_pokemon: Dict[str, Any],
        defender_pokemon: Dict[str, Any],
        skill_type: str = 'special'
    ) -> Tuple[float, float]:
        """
        计算宝可梦战斗胜率
        Args:
            attacker_pokemon: 攻击方宝可梦数据
            defender_pokemon: 防御方宝可梦数据
            skill_type: 技能类型 ('physical' 或 'special')，决定使用攻击/防御还是特攻/特防
        Returns:
            Tuple[float, float]: (攻击方胜率%, 防御方胜率%)
        """
        # 获取宝可梦的属性类型
        attacker_types = self.pokemon_repo.get_pokemon_types(attacker_pokemon['species_id'])
        defender_types = self.pokemon_repo.get_pokemon_types(defender_pokemon['species_id'])

        # 如果获取不到类型数据，使用默认的普通属性
        if not attacker_types:
            attacker_types = ['normal']
        if not defender_types:
            defender_types = ['normal']

        # ----------------------
        # 步骤1：计算属性克制系数（攻击方对防御方的总克制系数）
        # ----------------------
        self_type_modifier = self.calculate_type_effectiveness(attacker_types, defender_types)
        # 防御方对攻击方的克制系数
        opp_type_modifier = self.calculate_type_effectiveness(defender_types, attacker_types)
        # ----------------------
        # 步骤2：计算攻防能力（结合等级、属性修正）
        # ----------------------

        # 攻击方输出属性：按技能类型选择
        atk_stat_attacker = 'attack' if skill_type == 'physical' else 'sp_attack'
        # 防御方输出属性：取自身物攻和特攻的最大值（贴合实际定位）
        atk_stat_defender = 'attack' if defender_pokemon['attack'] > defender_pokemon['sp_attack'] else 'sp_attack'
        def_stat = 'defense' if skill_type == 'physical' else 'sp_defense'
        # 等级修正系数（等级差距影响，避免碾压）
        self_level_mod = attacker_pokemon['level'] / 50  # 等级50修正1.0，等级100修正2.0，等级25修正0.5
        opp_level_mod = defender_pokemon['level'] / 50

        # 攻击方输出能力 = 攻击属性值 × 等级修正 × 属性克制系数
        self_offense = attacker_pokemon[atk_stat_attacker] * self_level_mod * self_type_modifier
        opp_offense = defender_pokemon[atk_stat_defender] * opp_level_mod * opp_type_modifier  # 防御方用自己的核心输出属性
        # 防御方承伤能力 = 防御属性值 × 等级修正
        self_defense = attacker_pokemon[def_stat] * self_level_mod
        opp_defense = defender_pokemon[def_stat] * opp_level_mod

        # 有效战力 = 输出能力 / 承伤能力（比值越大，战力越强）
        self_effective_power = self_offense / self_defense if self_defense > 0 else 0
        opp_effective_power = opp_offense / opp_defense if opp_defense > 0 else 0
        # ----------------------
        # 步骤3：速度先手权修正（速度快的获得额外战力加成）
        # ----------------------
        speed_ratio = attacker_pokemon['speed'] / max(defender_pokemon['speed'], 1)
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

    def start_battle(self, user_id: str, wild_pokemon: Dict[str, Any], pokemon_id: str = None) -> Dict[str, Any]:
        """
        开始一场与野生宝可梦的战斗
        Args:
            user_id: 用户ID
            wild_pokemon: 野生宝可梦数据
            pokemon_id: 用户选择的宝可梦ID（如果为None则使用队伍中的第一只）
        Returns:
            包含战斗结果的字典
        """
        try:
            # 获取用户信息
            user = self.user_repo.get_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "message": "用户不存在"
                }

            # 获取用户宝可梦（如果未指定则使用队伍中的第一只）
            user_pokemon = None
            if pokemon_id:
                user_pokemon = self.user_repo.get_user_pokemon_by_id(pokemon_id)
            else:
                # 获取用户的第一只宝可梦（作为默认战斗宝可梦）
                user_pokemon_list = self.user_repo.get_user_pokemon(user_id)
                if user_pokemon_list:
                    user_pokemon = user_pokemon_list[0]

            if not user_pokemon:
                return {
                    "success": False,
                    "message": "您没有可用的宝可梦进行战斗"
                }

            # 计算战斗胜率
            user_win_rate, wild_win_rate = self.calculate_battle_win_rate(user_pokemon, wild_pokemon)

            # 随机决定战斗结果
            import random
            result = "胜利" if random.random() * 100 < user_win_rate else "失败"

            # 返回战斗结果
            battle_result = {
                "success": True,
                "message": f"战斗结束！用户宝可梦 {user_pokemon['nickname']} vs 野生宝可梦 {wild_pokemon['name']}",
                "battle_details": {
                    "user_pokemon": {
                        "name": user_pokemon['nickname'],
                        "species": user_pokemon['species_name'],
                        "level": user_pokemon['level'],
                        "hp": user_pokemon.get('current_hp', 0),
                        "attack": user_pokemon.get('attack', 0),
                        "defense": user_pokemon.get('defense', 0),
                        "speed": user_pokemon.get('speed', 0)
                    },
                    "wild_pokemon": {
                        "name": wild_pokemon['name'],
                        "level": wild_pokemon['level'],
                        "hp": wild_pokemon.get('hp', 0),
                        "attack": wild_pokemon.get('attack', 0),
                        "defense": wild_pokemon.get('defense', 0),
                        "speed": wild_pokemon.get('speed', 0)
                    },
                    "win_rates": {
                        "user_win_rate": user_win_rate,
                        "wild_win_rate": wild_win_rate
                    },
                    "result": result
                }
            }

            return battle_result

        except Exception as e:
            return {
                "success": False,
                "message": f"战斗过程中发生错误: {str(e)}"
            }