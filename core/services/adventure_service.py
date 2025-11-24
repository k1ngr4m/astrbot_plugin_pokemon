import random
from itertools import accumulate
from typing import Dict, Any, List, Optional

from .pokemon_service import PokemonService
from ..domain.pokemon_models import WildPokemonInfo, PokemonStats, PokemonIVs, PokemonEVs, PokemonMoves
from ..repositories.abstract_repository import (
    AbstractAdventureRepository, AbstractPokemonRepository, AbstractUserRepository
)
from ..domain.adventure_models import AdventureArea, AreaPokemon, AdventureResult, AreaInfo
from ..utils import get_now


class AdventureService:
    """冒险区域相关的业务逻辑服务"""

    def __init__(
            self,
            adventure_repo: AbstractAdventureRepository,
            pokemon_repo: AbstractPokemonRepository,
            pokemon_service: PokemonService,
            user_repo: AbstractUserRepository,
            config: Dict[str, Any]
    ):
        self.adventure_repo = adventure_repo
        self.pokemon_repo = pokemon_repo
        self.pokemon_service = pokemon_service
        self.user_repo = user_repo
        self.config = config

    def get_all_areas(self) -> Dict[str, Any]:
        """
        获取所有可冒险的区域列表
        Returns:
            包含区域列表的字典
        """
        try:
            areas = self.adventure_repo.get_all_areas()

            if not areas:
                return {
                    "success": True,
                    "message": "暂无可用的冒险区域",
                    "areas": []
                }

            formatted_areas = []
            for area in areas:
                formatted_areas.append({
                    "area_code": area.area_code,
                    "area_name": area.area_name,
                    "description": area.description or "暂无描述",
                    "min_level": area.min_level,
                    "max_level": area.max_level
                })

            return {
                "success": True,
                "areas": formatted_areas,
                "count": len(formatted_areas),
                "message": f"共有 {len(formatted_areas)} 个可冒险区域"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取区域列表失败: {str(e)}"
            }

    def adventure_in_area(self, user_id: str, area_code: str) -> AdventureResult:
        """
        在指定区域进行冒险，随机刷新一只野生宝可梦
        Args:
            user_id: 用户ID
            area_code: 区域代码
        Returns:
            包含冒险结果的字典
        """
        # 统一错误返回函数（减少重复代码）
        def error_response(message: str) -> AdventureResult:
            return AdventureResult(
                success=False,
                message=message,
                wild_pokemon=None,
                area=None
            )
        try:
            # 3. 获取区域信息
            area = self.adventure_repo.get_area_by_code(area_code)
            if not area:
                return error_response(f"未找到区域 {area_code}")
            # 4. 获取该区域的宝可梦列表
            area_pokemon_list = self.adventure_repo.get_area_pokemon_by_area_code(area_code)
            if not area_pokemon_list:
                return error_response(f"区域 {area.area_name}) 中暂无野生宝可梦")
            # 5. 权重随机选择宝可梦（使用itertools.accumulate简化累加逻辑）
            encounter_rates = [ap.encounter_rate for ap in area_pokemon_list]
            total_rate = sum(encounter_rates)
            random_value = random.uniform(0, total_rate)

            # 累加概率，找到第一个超过随机值的宝可梦
            for idx, cumulative_rate in enumerate(accumulate(encounter_rates)):
                if random_value <= cumulative_rate:
                    selected_area_pokemon = area_pokemon_list[idx]
                    break
            else:
                # 兜底：如果循环未触发break（理论上不会发生），取最后一个
                selected_area_pokemon = area_pokemon_list[-1]

            # 6. 生成宝可梦等级（使用变量名简化赋值）
            min_level = selected_area_pokemon.min_level
            max_level = selected_area_pokemon.max_level
            wild_pokemon_level = random.randint(min_level, max_level)
            # 7. 创建野生宝可梦（直接使用返回结果，无需额外处理）
            wild_pokemon_result = self.pokemon_service.create_single_pokemon(
                species_id=selected_area_pokemon.pokemon_species_id,
                max_level=wild_pokemon_level,
                min_level=wild_pokemon_level
            )
            if not wild_pokemon_result.success:
                return error_response(wild_pokemon_result.message)
            wild_pokemon = wild_pokemon_result.data
            wild_pokemon_info = WildPokemonInfo(
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
            self.pokemon_repo.add_user_encountered_wild_pokemon(
                user_id=user_id,
                wild_pokemon_id = wild_pokemon_info.id,
                location_id=area.id,
                encounter_rate=selected_area_pokemon.encounter_rate,
            )



            # 8. 构造返回结果（直接复用create_single_pokemon的计算结果）
            result = AdventureResult(
                success=True,
                message=f"在 {area.area_name} 中遇到了野生的 {wild_pokemon_info.name}！",
                wild_pokemon=wild_pokemon_info,
                area=AreaInfo(
                    area_code=area.area_code,
                    area_name=area.area_name,
                )
            )
            return result

        except Exception as e:
            return error_response(f"冒险过程中发生错误: {str(e)}")