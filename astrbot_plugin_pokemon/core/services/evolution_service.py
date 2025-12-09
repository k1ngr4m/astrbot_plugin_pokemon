from typing import Dict, Any, Optional, Tuple
from astrbot.api import logger
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.pokemon_models import (
    UserPokemonInfo, PokemonIVs, PokemonEVs, PokemonStats, PokemonMoves, PokemonEvolution
)
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.services.nature_service import NatureService
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.infrastructure.repositories.abstract_repository import (
    AbstractUserPokemonRepository, AbstractPokemonRepository, AbstractNatureRepository
)


class EvolutionService:
    """宝可梦进化服务类"""

    def __init__(
            self,
            user_pokemon_repo: AbstractUserPokemonRepository,
            pokemon_repo: AbstractPokemonRepository,
            nature_service: NatureService,
    ):
        self.user_pokemon_repo = user_pokemon_repo
        self.pokemon_repo = pokemon_repo
        self.nature_service = nature_service

    def evolve_pokemon(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        执行宝可梦进化
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            Dict: 进化结果信息
        """
        try:
            # 1. 获取当前宝可梦信息
            current_pokemon = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
            if not current_pokemon:
                return {"success": False, "message": "找不到该宝可梦"}

            # 2. 查找有效的进化路线
            valid_evolution, error_msg = self._get_valid_evolution(current_pokemon)
            if not valid_evolution:
                return {"success": False, "message": error_msg or "该宝可梦当前无法进化"}

            # 3. 获取进化后的物种信息
            evolved_species = self.pokemon_repo.get_pokemon_by_id(valid_evolution.evolved_species_id)
            if not evolved_species:
                logger.error(f"[Evolution] Target species {valid_evolution.evolved_species_id} not found.")
                return {"success": False, "message": "进化数据缺失，无法完成进化"}

            # 4. 核心逻辑：计算进化后的数值
            # 进化后：种族值改变，等级/个体值/努力值/性格保持不变
            new_stats = self._calculate_new_stats(
                evolved_species.base_stats,
                current_pokemon.ivs,
                current_pokemon.evs,
                current_pokemon.level,
                current_pokemon.nature_id  # 使用原来的性格
            )

            # 6. 写入数据库
            self.user_pokemon_repo._update_user_pokemon_fields(
                user_id, pokemon_id,
                species_id=evolved_species.id,
                nickname=evolved_species.name_zh,
                hp=new_stats.hp,
                attack=new_stats.attack,
                defense=new_stats.defense,
                sp_attack=new_stats.sp_attack,
                sp_defense=new_stats.sp_defense,
                speed=new_stats.speed,
            )

            logger.info(f"User {user_id}'s Pokemon {current_pokemon.name} evolved into {evolved_species.name_zh}")

            return {
                "success": True,
                "message": f"✨ 恭喜！你的 {current_pokemon.name} 成功进化成了 {evolved_species.name_zh}！",
                "original_name": current_pokemon.name,
                "evolved_name": evolved_species.name_zh,
                "evolved_species_id": evolved_species.id,
                "new_stats": new_stats.__dict__
            }

        except Exception as e:
            logger.exception(f"Evolution failed for user {user_id}, pokemon {pokemon_id}")
            return {"success": False, "message": f"系统错误: {str(e)}"}

    def check_evolution_status(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        检查宝可梦的进化状态（用于查询是否可进化）
        """
        current_pokemon = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not current_pokemon:
            return {"can_evolve": False, "message": "宝可梦不存在"}

        valid_evolution, _ = self._get_valid_evolution(current_pokemon)

        if valid_evolution:
            evolved_species = self.pokemon_repo.get_pokemon_by_id(valid_evolution.evolved_species_id)
            if evolved_species:
                return {
                    "can_evolve": True,
                    "message": f"⚡ {current_pokemon.name} 现在的力量已经足以进化为 {evolved_species.name_zh}！",
                    "evolved_species_id": evolved_species.id,
                    "evolved_species_name": evolved_species.name_zh
                }

        return {
            "can_evolve": False,
            "message": f"{current_pokemon.name} 暂时还不能进化。"
        }

    def _get_valid_evolution(self, pokemon: UserPokemonInfo) -> Tuple[Optional[PokemonEvolution], Optional[str]]:
        """
        辅助方法：检查宝可梦是否满足进化条件
        Returns:
            (Evolution对象, 错误信息)
        """
        # 获取所有可能的进化路线（包括等级进化、道具进化等）
        evolutions = self.pokemon_repo.get_pokemon_evolutions(pokemon.species_id, pokemon.level)

        if not evolutions:
            return None, "该宝可梦没有进化形态"

        # 遍历所有进化路线，找到第一条满足条件的
        # TODO: 未来在此处扩展逻辑，支持 亲密度进化(happiness)、道具进化(item_id) 等
        for evo in evolutions:
            # 逻辑：等级进化 (Level Up)
            if evo.minimum_level and evo.minimum_level > 0:
                if pokemon.level >= evo.minimum_level:
                    return evo, None

            # 可以在此添加 elif 处理其他进化方式

        return None, "尚未满足进化条件（等级不足）"

    def _calculate_new_stats(self, base_stats, ivs: PokemonIVs, evs: PokemonEVs, level: int, nature_id: int = 1) -> PokemonStats:
        """
        根据种族值、个体值、努力值和等级计算属性值
        HP公式: ((种族值 × 2 + IV + EV ÷ 4) × 等级) ÷ 100 + 等级 + 10
        其他公式: ((种族值 × 2 + IV + EV ÷ 4) × 等级) ÷ 100 + 5
        """

        def _calc(base: int, iv: int, ev: int, lvl: int, is_hp: bool = False) -> int:
            # 核心计算部分 (使用整除 //)
            core_val = ((base * 2 + iv + (ev // 4)) * lvl) // 100
            if is_hp:
                return core_val + lvl + 10
            else:
                return core_val + 5

        # 创建基础属性对象
        base_stats_obj = PokemonStats(
            hp=_calc(base_stats.base_hp, ivs.hp_iv, evs.hp_ev, level, is_hp=True),
            attack=_calc(base_stats.base_attack, ivs.attack_iv, evs.attack_ev, level),
            defense=_calc(base_stats.base_defense, ivs.defense_iv, evs.defense_ev, level),
            sp_attack=_calc(base_stats.base_sp_attack, ivs.sp_attack_iv, evs.sp_attack_ev, level),
            sp_defense=_calc(base_stats.base_sp_defense, ivs.sp_defense_iv, evs.sp_defense_ev, level),
            speed=_calc(base_stats.base_speed, ivs.speed_iv, evs.speed_ev, level)
        )

        # 如果需要应用性格修正，创建并使用NatureService

        # 应用性格修正
        final_stats = self.nature_service.apply_nature_modifiers(base_stats_obj, nature_id)

        return final_stats