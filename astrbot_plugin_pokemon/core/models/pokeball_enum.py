from enum import Enum
from typing import TYPE_CHECKING, Dict, Callable, Any
from datetime import datetime
import pytz
import random

if TYPE_CHECKING:
    from ..models.pokemon_models import WildPokemonInfo
    from ...infrastructure.repositories.abstract_repository import AbstractPokemonRepository, AbstractUserPokemonRepository


class PokeballType(Enum):
    """精灵球类型枚举"""
    MASTER_BALL = 1        # 大师球 - 100% 捕捉成功率
    ULTRA_BALL = 2         # 高级球 - 2x 捕捉成功率
    GREAT_BALL = 3         # 超级球 - 1.5x 捕捉成功率
    POKE_BALL = 4          # 普通精灵球 - 1x 捕捉成功率
    SAFARI_BALL = 5        # 狩猎球 - 1.5x (特定区域使用)
    NET_BALL = 6           # 捕网球 - 3x针对水/虫系宝可梦，1x其他
    DIVE_BALL = 7          # 潜水球 - 3.5x针对水上/钓鱼时遇到的宝可梦，1x其他
    NEST_BALL = 8          # 巢穴球 - 根据宝可梦等级变化 (40-level)/10，最高3.9x
    REPEAT_BALL = 9        # 重复球 - 3x针对已捕捉过的宝可梦种类，1x其他
    TIMER_BALL = 10        # 计时球 - 捕捉率随回合增加，最高4x
    LUXURY_BALL = 11       # 豪华球 - 捕捉成功后初始友好度+200
    PREMIER_BALL = 12      # 纪念球 - 1x 捕捉成功率
    DUSK_BALL = 13         # 黑暗球 - 夜晚(18:00-6:00)时3.5x，其他时间1x
    HEAL_BALL = 14         # 治愈球 - 捕捉成功后立即治愈
    QUICK_BALL = 15        # 先机球 - 首回合4x，其他回合1x
    CHERISH_BALL = 16      # 贵重球 - 1x 捕捉成功率


class PokeballStrategy:
    """精灵球捕捉策略类"""

    @staticmethod
    def get_master_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """大师球 - 255倍数（确保捕捉成功）"""
        return 255.0

    @staticmethod
    def get_ultra_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """高级球 - 2倍"""
        return 2.0

    @staticmethod
    def get_great_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """超级球 - 1.5倍"""
        return 1.5

    @staticmethod
    def get_poke_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """普通精灵球 - 1倍"""
        return 1.0

    @staticmethod
    def get_safari_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """狩猎球 - 1.5倍（特定区域使用，这里简化为固定1.5倍）"""
        return 1.5

    @staticmethod
    def get_net_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """捕网球 - 3倍针对水/虫系宝可梦，1倍其他"""
        pokemon_types = [t.lower() for t in pokemon_repo.get_pokemon_types(wild_pokemon.species_id) or ['normal']]
        if 'water' in pokemon_types or 'bug' in pokemon_types:
            return 3.0
        return 1.0

    @staticmethod
    def get_dive_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """潜水球 - 3.5倍针对水上/钓鱼时遇到的宝可梦，1倍其他"""
        # 这里先按3.5倍处理，可以根据具体情境调整
        return 3.5

    @staticmethod
    def get_nest_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """巢穴球 - 捕捉率根据宝可梦等级变化 (40-level)/10，最高3.9倍 (level 1)，最低1倍 (level 30+)"""
        level = wild_pokemon.level
        # 根据公式 (40 - level) / 10 计算倍数，最低为1.0
        calculated_multiplier = max(1.0, (40 - level) / 10)
        return min(3.9, calculated_multiplier)  # 最高3.9倍

    @staticmethod
    def get_repeat_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', user_id: str, user_pokemon_repo: 'AbstractUserPokemonRepository', **kwargs) -> float:
        """重复球 - 3倍针对已捕捉过的宝可梦种类，1倍其他"""
        # 注意：这个方法由 _create_repeat_ball_strategy 包装器调用，参数是显式传递的，需要 **kwargs 来兼容调用
        pokedex_result = user_pokemon_repo.get_user_pokedex_ids(user_id)
        if pokedex_result and wild_pokemon.species_id in pokedex_result.get("caught", set()):
            return 3.0
        return 1.0

    @staticmethod
    def get_timer_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """计时球 - 捕捉率随回合增加，最高4倍"""
        # 这里先按1倍处理，实际应用中可能需要根据战斗回合数调整
        return 1.0

    @staticmethod
    def get_luxury_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """豪华球 - 1倍（基础捕捉率不变）"""
        return 1.0

    @staticmethod
    def get_premier_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """纪念球 - 1倍"""
        return 1.0

    @staticmethod
    def get_dusk_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """黑暗球 - 夜晚(18:00-6:00)时3.5倍，其他时间1倍"""
        # 获取当前北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')  # 北京时间
        current_time = datetime.now(beijing_tz)
        current_hour = current_time.hour

        # 如果当前时间在18:00-6:00之间（晚上6点到早上6点），使用3.5倍数
        if 18 <= current_hour <= 23 or 0 <= current_hour < 6:
            return 3.5
        return 1.0

    @staticmethod
    def get_heal_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """治愈球 - 1倍（基础捕捉率不变）"""
        return 1.0

    @staticmethod
    def get_quick_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """先机球 - 首回合4倍，其他回合1倍"""
        # 这里先按4倍处理，实际应用中可能需要判断是否为战斗首回合
        return 4.0

    @staticmethod
    def get_cherish_ball_multiplier(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """贵重球 - 1倍"""
        return 1.0


class PokeballCalculator:
    """精灵球捕捉率计算器"""

    def __init__(self):
        self.multiplier_strategies: Dict[int, Callable] = {
            PokeballType.MASTER_BALL.value: PokeballStrategy.get_master_ball_multiplier,
            PokeballType.ULTRA_BALL.value: PokeballStrategy.get_ultra_ball_multiplier,
            PokeballType.GREAT_BALL.value: PokeballStrategy.get_great_ball_multiplier,
            PokeballType.POKE_BALL.value: PokeballStrategy.get_poke_ball_multiplier,
            PokeballType.SAFARI_BALL.value: PokeballStrategy.get_safari_ball_multiplier,
            PokeballType.NET_BALL.value: PokeballStrategy.get_net_ball_multiplier,
            PokeballType.DIVE_BALL.value: PokeballStrategy.get_dive_ball_multiplier,
            PokeballType.NEST_BALL.value: PokeballStrategy.get_nest_ball_multiplier,
            PokeballType.REPEAT_BALL.value: self._create_repeat_ball_strategy(),
            PokeballType.TIMER_BALL.value: PokeballStrategy.get_timer_ball_multiplier,
            PokeballType.LUXURY_BALL.value: PokeballStrategy.get_luxury_ball_multiplier,
            PokeballType.PREMIER_BALL.value: PokeballStrategy.get_premier_ball_multiplier,
            PokeballType.DUSK_BALL.value: PokeballStrategy.get_dusk_ball_multiplier,
            PokeballType.HEAL_BALL.value: PokeballStrategy.get_heal_ball_multiplier,
            PokeballType.QUICK_BALL.value: PokeballStrategy.get_quick_ball_multiplier,
            PokeballType.CHERISH_BALL.value: PokeballStrategy.get_cherish_ball_multiplier,
        }

    def _create_repeat_ball_strategy(self):
        """创建需要额外参数的重复球策略"""
        def strategy(wild_pokemon: 'WildPokemonInfo', pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
            # 这里的 **kwargs 已经包含了调用方传入的所有额外参数
            return PokeballStrategy.get_repeat_ball_multiplier(
                wild_pokemon, pokemon_repo,
                kwargs.get('user_id', ''),
                kwargs.get('user_pokemon_repo', None)
            )
        return strategy

    def get_ball_multiplier(self, ball_id: int, wild_pokemon: 'WildPokemonInfo',
                           pokemon_repo: 'AbstractPokemonRepository', **kwargs) -> float:
        """获取精灵球的捕捉倍数"""
        strategy = self.multiplier_strategies.get(ball_id)

        if strategy:
            # 统一传递 kwargs，策略方法需要能够接收或忽略这些参数
            return strategy(wild_pokemon, pokemon_repo, **kwargs)

        # 如果不在策略字典中，返回默认倍数
        return 1.0