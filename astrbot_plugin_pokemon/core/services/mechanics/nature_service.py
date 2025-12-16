import random
from typing import Dict, Any, Optional

from ...models.pokemon_models import PokemonStats
from ....infrastructure.repositories.abstract_repository import AbstractNatureRepository


class NatureService:
    """性格服务，处理性格相关的业务逻辑"""

    # 平衡性格ID集合 (decreased_stat_id == increased_stat_id)
    BALANCED_NATURE_IDS = {1, 7, 13, 19, 25}  # 勤奋, 坦率, 害羞, 浮躁, 认真

    # stat_id 映射
    STAT_ID_MAP = {
        2: "attack",
        3: "defense",
        4: "sp_attack",
        5: "sp_defense",
        6: "speed"
    }

    def __init__(self, nature_repo: AbstractNatureRepository):
        self.nature_repo = nature_repo
        self._all_natures = None  # 缓存所有性格数据

    def _load_all_natures(self) -> None:
        """加载所有性格数据到缓存"""
        if self._all_natures is None:
            self._all_natures = self.nature_repo.get_all_natures()

    def get_nature_name_by_id(self, nature_id: int) -> Optional[str]:
        """根据性格ID获取性格名称"""
        self._load_all_natures()
        if not self._all_natures:
            return None

        nature = next((n for n in self._all_natures if n['id'] == nature_id), None)
        return nature['name_zh'] if nature else None

    def get_random_nature(self) -> Dict[str, Any]:
        """随机获取一个性格"""
        self._load_all_natures()
        nature = random.choice(self._all_natures)
        return nature

    def apply_nature_modifiers(self, stats: PokemonStats, nature_id: int) -> PokemonStats:
        """根据性格修正属性值"""
        # 如果是平衡性格，直接返回原属性
        if nature_id in self.BALANCED_NATURE_IDS:
            return stats

        # 获取性格数据
        nature = self.nature_repo.get_nature_by_id(nature_id)
        if not nature:
            return stats

        decreased_stat_id = nature.get('decreased_stat_id')
        increased_stat_id = nature.get('increased_stat_id')

        # 创建新的stats对象以避免修改原始对象
        new_stats = PokemonStats(
            hp=stats.hp,
            attack=stats.attack,
            defense=stats.defense,
            sp_attack=stats.sp_attack,
            sp_defense=stats.sp_defense,
            speed=stats.speed
        )

        # 应用提升修正 (×1.1)
        if increased_stat_id in self.STAT_ID_MAP:
            stat_name = self.STAT_ID_MAP[increased_stat_id]
            current_value = getattr(new_stats, stat_name)
            setattr(new_stats, stat_name, int(current_value * 1.1))

        # 应用降低修正 (×0.9)
        if decreased_stat_id in self.STAT_ID_MAP:
            stat_name = self.STAT_ID_MAP[decreased_stat_id]
            current_value = getattr(new_stats, stat_name)
            setattr(new_stats, stat_name, max(1, int(current_value * 0.9)))  # 最小值为1

        return new_stats