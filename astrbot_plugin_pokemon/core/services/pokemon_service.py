import random
from typing import Dict, Any, Optional
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.infrastructure.repositories.abstract_repository import (
    AbstractPokemonRepository, )

from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.pokemon_models import PokemonCreateResult, PokemonDetail, PokemonStats, PokemonIVs, \
    PokemonEVs, WildPokemonInfo


class PokemonService:
    """封装与宝可梦相关的业务逻辑"""

    HP_FORMULA_CONSTANT = 10  # HP计算公式常量
    NON_HP_FORMULA_CONSTANT = 5  # 非HP属性计算公式常量

    def __init__(
            self,
            pokemon_repo: AbstractPokemonRepository,
            config: Dict[str, Any]
    ):
        self.pokemon_repo = pokemon_repo
        self.config = config

    def create_single_pokemon(self, species_id: int, max_level: int, min_level: int) -> PokemonCreateResult:
        """
        创建一个新的宝可梦实例，使用指定的宝可梦ID和等级范围
        Args:
            species_id (int): 宝可梦的ID
            max_level (int): 宝可梦的最大等级
            min_level (int): 宝可梦的最小等级
        Returns:
            包含宝可梦信息的字典
        """

        # 局部函数：生成0-31的随机IV
        def generate_iv() -> int:
            return random.randint(0, 31)

        # 局部函数：计算属性值（提取重复的计算公式）
        def calculate_stat(base: int, iv: int, ev: int, level: int, is_hp: bool = False) -> int:
            """
            根据种族值、IV、EV、等级计算最终属性值
            Args:
                base: 种族值
                iv: 个体值
                ev: 努力值
                level: 等级
                is_hp: 是否为HP属性（HP公式不同）
            """
            base_calculation = (base * 2 + iv + ev // 4) * level / 100
            if is_hp:
                return int(base_calculation) + level + self.HP_FORMULA_CONSTANT
            return int(base_calculation) + self.NON_HP_FORMULA_CONSTANT

        # 1. 获取宝可梦模板
        pokemon_template = self.pokemon_repo.get_pokemon_by_id(species_id)
        if not pokemon_template:
            return PokemonCreateResult(
                success=False,
                message="无法获取宝可梦信息",
                data=None
            )

        # 2. 生成基础信息
        gender = self.determine_pokemon_gender(pokemon_template.gender_rate)
        level = random.randint(min_level, max_level)
        exp = 0
        moves = None

        # 3. 生成IV和EV（使用局部函数简化）
        ivs = {
            "hp": generate_iv(),
            "attack": generate_iv(),
            "defense": generate_iv(),
            "sp_attack": generate_iv(),
            "sp_defense": generate_iv(),
            "speed": generate_iv()
        }
        evs = {key: 0 for key in ivs.keys()}  # 简化EV初始化（与IV键一致）

        # 4. 获取种族值
        base_stats = {
            "hp": pokemon_template.base_stats["base_hp"],
            "attack": pokemon_template.base_stats["base_attack"],
            "defense": pokemon_template.base_stats["base_defense"],
            "sp_attack": pokemon_template.base_stats["base_sp_attack"],
            "sp_defense": pokemon_template.base_stats["base_sp_defense"],
            "speed": pokemon_template.base_stats["base_speed"]
        }

        # 5. 计算最终属性（使用局部函数，避免重复代码）
        stats = {
            "hp": calculate_stat(base_stats["hp"], ivs["hp"], evs["hp"], level, is_hp=True),
            "attack": calculate_stat(base_stats["attack"], ivs["attack"], evs["attack"], level),
            "defense": calculate_stat(base_stats["defense"], ivs["defense"], evs["defense"], level),
            "sp_attack": calculate_stat(base_stats["sp_attack"], ivs["sp_attack"], evs["sp_attack"], level),
            "sp_defense": calculate_stat(base_stats["sp_defense"], ivs["sp_defense"], evs["sp_defense"], level),
            "speed": calculate_stat(base_stats["speed"], ivs["speed"], evs["speed"], level)
        }

        # 6. 确保HP最小值（原逻辑保留，优化写法）
        stats["hp"] = max(1, stats["hp"], base_stats["hp"] // 2)

        # 7. 返回结果（统一键名格式，IV/EV使用一致的键）
        result = PokemonCreateResult(
            success=True,
            message="宝可梦生成成功",
            data= PokemonDetail(
                base_pokemon=pokemon_template,
                gender=gender,
                level=level,
                exp=exp,
                stats= PokemonStats(
                    hp=stats["hp"],
                    attack=stats["attack"],
                    defense=stats["defense"],
                    sp_attack=stats["sp_attack"],
                    sp_defense=stats["sp_defense"],
                    speed=stats["speed"],
                ),
                ivs= PokemonIVs(
                    hp_iv=ivs["hp"],
                    attack_iv=ivs["attack"],
                    defense_iv=ivs["defense"],
                    sp_attack_iv=ivs["sp_attack"],
                    sp_defense_iv=ivs["sp_defense"],
                    speed_iv=ivs["speed"],
                ),
                evs= PokemonEVs(
                    hp_ev=evs["hp"],
                    attack_ev=evs["attack"],
                    defense_ev=evs["defense"],
                    sp_attack_ev=evs["sp_attack"],
                    sp_defense_ev=evs["sp_defense"],
                    speed_ev=evs["speed"],
                ),
                moves= moves
            )
        )
        return result

    def get_user_encountered_wild_pokemon(self, user_id: str) -> Optional[WildPokemonInfo]:
        """
        获取用户当前遇到的野生宝可梦
        Args:
            user_id (str): 用户ID
        Returns:
            WildPokemonInfo: 野生宝可梦的详细信息
        """
        encountered_wild_pokemon = self.pokemon_repo.get_user_encountered_wild_pokemon(user_id)
        if not encountered_wild_pokemon:
            return None
        wild_pokemon_id = encountered_wild_pokemon.wild_pokemon_id
        wild_pokemon_info = self.pokemon_repo.get_wild_pokemon_by_id(wild_pokemon_id)
        return wild_pokemon_info

    def add_user_encountered_wild_pokemon(self, user_id: str, wild_pokemon: WildPokemonInfo):
        """
        添加用户当前遇到的野生宝可梦
        Args:
            user_id (str): 用户ID
            wild_pokemon (PokemonDetail): 野生宝可梦的详细信息
        """
        self.pokemon_repo.add_user_encountered_wild_pokemon(user_id, wild_pokemon)

    def determine_pokemon_gender(self, gender_rate: int) -> str:
        """
        根据gender_rate编码判定宝可梦性别
        :param gender_rate: 性别比率编码（-1/0/1/2/4/6/8）
        :return: 性别标识（M=雄性，F=雌性，N=无性别）
        """
        # 定义性别比率映射：(编码, 描述, 雄性概率, 雌性概率)
        gender_mapping = {
            -1: ("无性别", 0.0, 0.0),
            0: ("仅雌性", 0.0, 1.0),
            1: ("1雌:7雄", 0.875, 0.125),
            2: ("1雌:3雄", 0.75, 0.25),
            4: ("1雌:1雄", 0.5, 0.5),
            6: ("3雌:1雄", 0.25, 0.75),
            8: ("仅雄性", 1.0, 0.0)
        }

        # 检查编码是否有效，默认无性别
        if gender_rate not in gender_mapping:
            return "N"

        desc, male_prob, female_prob = gender_mapping[gender_rate]

        # 无性别判定
        if male_prob == 0.0 and female_prob == 0.0:
            return "N"
        # 仅雌性判定
        elif male_prob == 0.0 and female_prob == 1.0:
            return "F"
        # 仅雄性判定
        elif male_prob == 1.0 and female_prob == 0.0:
            return "M"
        # 雌雄混合判定（基于概率随机选择）
        else:
            # 生成0~1的随机数，根据概率区间判定
            random_val = random.random()
            if random_val < male_prob:
                return "M"
            else:
                return "F"