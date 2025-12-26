import random
from typing import Dict, Any, Optional, List

from astrbot.api import logger
from .exp_service import ExpService
from ...models.common_models import BaseResult
from ....infrastructure.repositories.abstract_repository import (
    AbstractPokemonRepository, AbstractMoveRepository, AbstractUserPokemonRepository)

from ...models.pokemon_models import PokemonCreateResult, \
    PokemonDetail, PokemonStats, PokemonIVs, \
    PokemonEVs, WildPokemonInfo, PokemonMoves, PokemonSpecies
from ....interface.response.answer_enum import AnswerEnum
from .nature_service import NatureService


class PokemonService:
    """封装与宝可梦相关的业务逻辑"""

    HP_FORMULA_CONSTANT = 10  # HP计算公式常量
    NON_HP_FORMULA_CONSTANT = 5  # 非HP属性计算公式常量

    def __init__(
            self,
            pokemon_repo: AbstractPokemonRepository,
            move_repo: AbstractMoveRepository,
            user_pokemon_repo: AbstractUserPokemonRepository,
            config: Dict[str, Any],
            nature_service: NatureService = None,
            exp_service: ExpService = None
    ):
        self.pokemon_repo = pokemon_repo
        self.move_repo = move_repo
        self.user_pokemon_repo = user_pokemon_repo
        self.config = config
        self.nature_service = nature_service
        self.exp_service = exp_service

    @staticmethod
    # 静态方法：生成0-31的随机IV
    def generate_iv() -> int:
        return random.randint(0, 31)

    # 移出内部函数，改为方法
    def _calculate_stat(self, base: int, iv: int, ev: int, level: int, is_hp: bool = False) -> int:
        base_calculation = (base * 2 + iv + ev // 4) * level / 100
        if is_hp:
            return int(base_calculation) + level + self.HP_FORMULA_CONSTANT
        return int(base_calculation) + self.NON_HP_FORMULA_CONSTANT

    def create_single_pokemon(self, species_id: int, max_level: int, min_level: int) -> BaseResult[PokemonDetail]:
        """
        创建一个新的宝可梦实例，使用指定的宝可梦ID和等级范围
        Args:
            species_id (int): 宝可梦的ID
            max_level (int): 宝可梦的最大等级
            min_level (int): 宝可梦的最小等级
        Returns:
            包含宝可梦信息的字典
        """
        # 1. 获取宝可梦模板
        pokemon_template = self.pokemon_repo.get_pokemon_by_id(species_id)
        if not pokemon_template:
            return BaseResult(
                success=False,
                message="无法获取宝可梦信息",
            )

        # 2. 生成基础信息
        gender = self.determine_pokemon_gender(pokemon_template.gender_rate)
        level = random.randint(min_level, max_level)
        # exp = 0
        growth_rate_id = pokemon_template.growth_rate_id if pokemon_template.growth_rate_id else 2
        exp = self.exp_service.get_required_exp_for_level(level, growth_rate_id)

        # 获取招式
        move_list = self.move_repo.get_level_up_moves(species_id, level)
        # 填充到4个位置，不足的补None
        while len(move_list) < 4:
            move_list.append(None)

        moves = PokemonMoves(
            move1_id=move_list[0],
            move2_id=move_list[1],
            move3_id=move_list[2],
            move4_id=move_list[3]
        )

        # 3. 生成IV和EV（使用局部函数简化）
        ivs = {
            "hp": self.generate_iv(),
            "attack": self.generate_iv(),
            "defense": self.generate_iv(),
            "sp_attack": self.generate_iv(),
            "sp_defense": self.generate_iv(),
            "speed": self.generate_iv()
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

        # 5. 计算基础属性（使用局部函数，避免重复代码）
        base_stats_calculated = {
            "hp": self._calculate_stat(base_stats["hp"], ivs["hp"], evs["hp"], level, is_hp=True),
            "attack": self._calculate_stat(base_stats["attack"], ivs["attack"], evs["attack"], level),
            "defense": self._calculate_stat(base_stats["defense"], ivs["defense"], evs["defense"], level),
            "sp_attack": self._calculate_stat(base_stats["sp_attack"], ivs["sp_attack"], evs["sp_attack"], level),
            "sp_defense": self._calculate_stat(base_stats["sp_defense"], ivs["sp_defense"], evs["sp_defense"], level),
            "speed": self._calculate_stat(base_stats["speed"], ivs["speed"], evs["speed"], level)
        }

        # 6. 获取并应用性格
        nature = self.nature_service.get_random_nature()
        nature_id = nature['id']

        # 创建基础属性对象用于修正
        base_stats_obj = PokemonStats(
            hp=base_stats_calculated["hp"],
            attack=base_stats_calculated["attack"],
            defense=base_stats_calculated["defense"],
            sp_attack=base_stats_calculated["sp_attack"],
            sp_defense=base_stats_calculated["sp_defense"],
            speed=base_stats_calculated["speed"]
        )
        # 应用性格修正
        final_stats = self.nature_service.apply_nature_modifiers(base_stats_obj, nature_id)


        # 7. 确保HP最小值（原逻辑保留，优化写法）
        final_stats.hp = max(1, final_stats.hp, base_stats["hp"] // 2)

        # 8. 返回结果（统一键名格式，IV/EV使用一致的键）
        result = BaseResult(
            success=True,
            message=AnswerEnum.POKEMON_CREATE_SUCCESS.value,
            data= PokemonDetail(
                base_pokemon=pokemon_template,
                gender=gender,
                level=level,
                exp=exp,
                stats= final_stats,
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
                moves= moves,
                nature_id=nature_id,
            )
        )
        return result

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

    def get_pokedex_view(self, user_id: str, page: int = 1, page_size: int = 20, return_data: bool = False) -> str:
        """
        获取用户的图鉴视图
        :param user_id: 用户ID
        :param page: 页码
        :param page_size: 每页数量
        :param return_data: 是否返回数据结构而不是文本
        :return: 图鉴视图字符串或数据结构
        """
        # 1. 获取所有宝可梦 (使用简化的获取方法以提高性能)
        all_species = self.pokemon_repo.get_all_pokemon_simple()

        # 2. 获取用户进度
        user_progress = self.user_pokemon_repo.get_user_pokedex_ids(user_id)
        caught_set = user_progress['caught']
        seen_set = user_progress['seen']

        # 3. 统计总数
        total_count = len(all_species)
        caught_count = len(caught_set)
        seen_count = len(seen_set)

        # 4. 分页切片
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_species = all_species[start_idx:end_idx]

        if not page_species:
            if return_data:
                return {
                    "list": [],
                    "page_info": {
                        "current_page": page,
                        "total_count": total_count,
                        "caught_count": caught_count,
                        "seen_count": seen_count,
                        "total_pages": max(1, (total_count + page_size - 1) // page_size)
                    }
                }
            return "图鉴页码超出范围。"

        if return_data:
            # 返回数据结构用于图片生成
            pokemon_list = []
            for sp in page_species:
                sp_id = sp.id
                pokemon_list.append({
                    "id": sp_id,
                    "sprite_id": sp_id,
                    "name": sp.name_zh if sp_id in seen_set else "???",
                    "caught": sp_id in caught_set,
                    "seen": sp_id in seen_set
                })

            return {
                "list": pokemon_list,
                "page_info": {
                    "current_page": page,
                    "total_count": total_count,
                    "caught_count": caught_count,
                    "seen_count": seen_count,
                    "total_pages": max(1, (total_count + page_size - 1) // page_size)
                }
            }
        else:
            # 5. 构建显示文本
            lines = [f"📖 宝可梦图鉴 (第 {page} 页)"]
            lines.append(f"收集进度: 🟢 捕捉 {caught_count} / 👁️ 遇见 {seen_count} / 🌐 总计 {total_count}")
            lines.append("-" * 20)

            for sp in page_species:
                sp_id = sp.id
                if sp_id in caught_set:
                    icon = "🟢" # 已捕捉
                    name = sp.name_zh
                elif sp_id in seen_set:
                    icon = "👁️" # 仅遇见
                    name = sp.name_zh
                else:
                    icon = "❓" # 未知
                    name = "???"

                # 格式: #001 🟢 妙蛙种子
                lines.append(f"#{sp_id:04d} {icon} {name}")

            lines.append("-" * 20)
            lines.append("提示: 输入 /图鉴 [M名字/ID] 查看详细资料")

            return "\n\n".join(lines)

    # ==========直接返回repo层==========
    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[PokemonSpecies]:
        """
        根据宝可梦ID获取宝可梦物种信息
        Args:
            pokemon_id (int): 宝可梦ID
        Returns:
            PokemonSpecies: 宝可梦物种信息
        """
        return self.pokemon_repo.get_pokemon_by_id(pokemon_id)

    def get_pokemon_by_name(self, pokemon_name: str) -> Optional[PokemonSpecies]:
        """
        根据宝可梦名称获取宝可梦物种信息
        Args:
            pokemon_name (str): 宝可梦名称
        Returns:
            PokemonSpecies: 宝可梦物种信息
        """
        return self.pokemon_repo.get_pokemon_by_name(pokemon_name)

    def get_pokemon_types(self, pokemon_id: int) -> List[str]:
        """
        根据宝可梦ID获取宝可梦的类型
        Args:
            pokemon_id (int): 宝可梦ID
        Returns:
            List[str]: 宝可梦的类型列表
        """
        return self.pokemon_repo.get_pokemon_types(pokemon_id)
