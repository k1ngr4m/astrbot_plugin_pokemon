import random
from typing import Dict, Any, Optional
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.infrastructure.repositories.abstract_repository import (
    AbstractPokemonRepository, AbstractMoveRepository)

from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.pokemon_models import PokemonCreateResult, \
    PokemonDetail, PokemonStats, PokemonIVs, \
    PokemonEVs, WildPokemonInfo, PokemonMoves, PokemonSpecies


class PokemonService:
    """封装与宝可梦相关的业务逻辑"""

    HP_FORMULA_CONSTANT = 10  # HP计算公式常量
    NON_HP_FORMULA_CONSTANT = 5  # 非HP属性计算公式常量

    def __init__(
            self,
            pokemon_repo: AbstractPokemonRepository,
            move_repo: AbstractMoveRepository,
            config: Dict[str, Any]
    ):
        self.pokemon_repo = pokemon_repo
        self.move_repo = move_repo
        self.config = config

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

        # 5. 计算最终属性（使用局部函数，避免重复代码）
        stats = {
            "hp": self._calculate_stat(base_stats["hp"], ivs["hp"], evs["hp"], level, is_hp=True),
            "attack": self._calculate_stat(base_stats["attack"], ivs["attack"], evs["attack"], level),
            "defense": self._calculate_stat(base_stats["defense"], ivs["defense"], evs["defense"], level),
            "sp_attack": self._calculate_stat(base_stats["sp_attack"], ivs["sp_attack"], evs["sp_attack"], level),
            "sp_defense": self._calculate_stat(base_stats["sp_defense"], ivs["sp_defense"], evs["sp_defense"], level),
            "speed": self._calculate_stat(base_stats["speed"], ivs["speed"], evs["speed"], level)
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

    def get_pokedex_view(self, user_id: str, page: int = 1, page_size: int = 20) -> str:
        """
        获取用户的图鉴视图
        :param user_id: 用户ID
        :param page: 页码
        :param page_size: 每页数量
        :return: 图鉴视图字符串
        """
        # 1. 获取所有宝可梦 (使用简化的获取方法以提高性能)
        all_species = self.pokemon_repo.get_all_pokemon_simple()

        # 2. 获取用户进度
        user_progress = self.pokemon_repo.get_user_pokedex_ids(user_id)
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
            return "图鉴页码超出范围。"

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
        lines.append("提示: 输入 /图鉴 <名字/ID> 查看详细资料")

        return "\n\n".join(lines)

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
