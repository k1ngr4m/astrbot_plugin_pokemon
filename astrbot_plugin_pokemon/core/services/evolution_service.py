from typing import Dict, Any, Optional
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.pokemon_models import (
    UserPokemonInfo, PokemonIVs, PokemonEVs, PokemonStats, PokemonMoves
)
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.infrastructure.repositories.abstract_repository import (
    AbstractUserPokemonRepository, AbstractPokemonRepository
)


class EvolutionService:
    """宝可梦进化服务类"""

    def __init__(
        self,
        user_pokemon_repo: AbstractUserPokemonRepository,
        pokemon_repo: AbstractPokemonRepository
    ):
        self.user_pokemon_repo = user_pokemon_repo
        self.pokemon_repo = pokemon_repo

    def evolve_pokemon(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        执行宝可梦进化
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            进化结果信息
        """
        # 获取当前宝可梦信息
        current_pokemon = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not current_pokemon:
            return {
                "success": False,
                "message": "宝可梦不存在"
            }

        # 检查是否有进化路线
        evolutions = self.pokemon_repo.get_pokemon_evolutions(current_pokemon.species_id, current_pokemon.level)

        if not evolutions:
            return {
                "success": False,
                "message": f"宝可梦 {current_pokemon.name} 还未满足进化条件"
            }

        # 找到第一个符合要求的进化
        evolution = None
        for evo in evolutions:
            if evo.minimum_level > 0 and current_pokemon.level >= evo.minimum_level:
                evolution = evo
                break

        # 获取进化后的物种信息
        evolved_species = self.pokemon_repo.get_pokemon_by_id(evolution.evolved_species_id)
        if not evolved_species:
            return {
                "success": False,
                "message": "进化后的宝可梦信息不存在"
            }



        # 计算新的属性值（因为种族值可能发生变化）
        new_stats = self._calculate_new_stats(
            evolved_species.base_stats,
            current_pokemon.ivs,
            current_pokemon.evs,
            current_pokemon.level
        )

        # 创建进化后的宝可梦数据
        evolved_pokemon_data = UserPokemonInfo(
            id=current_pokemon.id,
            species_id=evolved_species.id,
            name=evolved_species.name_zh,
            gender=current_pokemon.gender,
            level=current_pokemon.level,
            exp=current_pokemon.exp,
            stats=new_stats,
            ivs=current_pokemon.ivs,
            evs=current_pokemon.evs,
            moves=current_pokemon.moves,
            caught_time=current_pokemon.caught_time
        )

        # 更新宝可梦数据
        try:
            # 更新宝可梦的种族ID
            self.user_pokemon_repo.update_user_pokemon_after_evolution(
                user_id=user_id,
                pokemon_id=pokemon_id,
                pokemon_info=evolved_pokemon_data
            )

            return {
                "success": True,
                "message": f"宝可梦 {current_pokemon.name} 成功进化为 {evolved_species.name_zh}！",
                "original_name": current_pokemon.name,
                "evolved_name": evolved_species.name_zh,
                "evolved_species_id": evolved_species.id
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"进化失败: {str(e)}"
            }

    def _calculate_new_stats(self, base_stats, ivs: PokemonIVs, evs: PokemonEVs, level: int) -> PokemonStats:
        """
        根据种族值、个体值、努力值和等级计算属性值
        公式: ((种族值 × 2 + IV + EV ÷ 4) × 等级) ÷ 100 + constant
        """
        def calculate_stat(base: int, iv: int, ev: int, level: int, is_hp: bool = False) -> int:
            base_calculation = (base * 2 + iv + ev // 4) * level / 100
            if is_hp:
                return int(base_calculation) + level + 10
            return int(base_calculation) + 5

        new_hp = calculate_stat(base_stats.base_hp, ivs.hp_iv, evs.hp_ev, level, is_hp=True)
        new_attack = calculate_stat(base_stats.base_attack, ivs.attack_iv, evs.attack_ev, level)
        new_defense = calculate_stat(base_stats.base_defense, ivs.defense_iv, evs.defense_ev, level)
        new_sp_attack = calculate_stat(base_stats.base_sp_attack, ivs.sp_attack_iv, evs.sp_attack_ev, level)
        new_sp_defense = calculate_stat(base_stats.base_sp_defense, ivs.sp_defense_iv, evs.sp_defense_ev, level)
        new_speed = calculate_stat(base_stats.base_speed, ivs.speed_iv, evs.speed_ev, level)

        return PokemonStats(
            hp=new_hp,
            attack=new_attack,
            defense=new_defense,
            sp_attack=new_sp_attack,
            sp_defense=new_sp_defense,
            speed=new_speed
        )

    def check_evolution_status(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        检查宝可梦的进化状态
        """
        current_pokemon = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not current_pokemon:
            return {
                "can_evolve": False,
                "message": "宝可梦不存在"
            }

        # 检查是否有进化路线
        with self.pokemon_repo._get_connection() as conn:
            evolutions = conn.execute(
                """
                SELECT * FROM pokemon_evolutions
                WHERE pre_species_id = ? AND minimum_level <= ? AND isdel = 0
                """, (current_pokemon.species_id, current_pokemon.level)
            ).fetchall()

        if evolutions:
            for evo in evolutions:
                evo_dict = dict(evo)
                if evo_dict['minimum_level'] > 0 and current_pokemon.level >= evo_dict['minimum_level']:
                    evolved_species = self.pokemon_repo.get_pokemon_by_id(evo_dict['evolved_species_id'])
                    if evolved_species:
                        return {
                            "can_evolve": True,
                            "message": f"宝可梦 {current_pokemon.name} 可以进化为 {evolved_species.name_zh}",
                            "evolved_species_id": evolved_species.id,
                            "evolved_species_name": evolved_species.name_zh
                        }

        return {
            "can_evolve": False,
            "message": f"宝可梦 {current_pokemon.name} 暂时无法进化"
        }