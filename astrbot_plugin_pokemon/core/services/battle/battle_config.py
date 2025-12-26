import json
from typing import Dict, Any, List, Optional
from pathlib import Path


class BattleConfigLoader:
    """战斗配置加载器"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "battle_configs.json"

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def get_type_chart(self) -> Dict[str, Dict[str, float]]:
        """获取属性克制表"""
        return self.config.get("type_chart", {})

    def get_stat_names(self) -> Dict[str, str]:
        """获取属性名称映射"""
        return self.config.get("stat_names", {})

    def get_ailment_map(self) -> Dict[str, str]:
        """获取异常状态映射"""
        return self.config.get("ailment_map", {})

    def get_ailment_chinese_map(self) -> Dict[str, str]:
        """获取中文异常状态映射"""
        return self.config.get("ailment_chinese_map", {})

    def get_two_turn_moves_config(self) -> Dict[str, Any]:
        """获取蓄力技能配置"""
        return self.config.get("two_turn_moves_config", {})

    def get_protection_penetration(self) -> Dict[str, List[int]]:
        """获取保护穿透配置"""
        return self.config.get("protection_penetration", {})

    def get_constants(self) -> Dict[str, Any]:
        """获取常量配置"""
        return self.config.get("constants", {})

    def get_target_id_mapping(self) -> Dict[str, Any]:
        """获取目标ID映射"""
        return self.config.get("target_id_mapping", {})

    def get_item_category_info(self) -> List[Dict[str, Any]]:
        """获取物品类别信息，包含类别名称和pocket_id"""
        return self.config.get("item_categories", [])

    def get_mold_breaker_ignorable_ids(self) -> List[int]:
        """获取破格特性可无视的特性ID列表"""
        return self.config.get("mold_breaker_ignorable_ids", [])

    def get_damage_class_map(self) -> Dict[str, str]:
        """获取伤害类别映射"""
        return self.config.get("DAMAGE_CLASS_MAP", {})

    def get_stat_map(self) -> Dict[str, str]:
        """获取属性映射"""
        return self.config.get("STAT_MAP", {})

    def get_pocket_id_mapping(self) -> List[Dict[str, Any]]:
        """获取背包ID映射"""
        return self.config.get("pocket_id_mapping", [])

    def get_item_categories(self) -> List[Dict[str, Any]]:
        """获取物品类别映射（包含pocket_id信息）"""
        return self.config.get("item_categories", [])


# 初始化全局配置
battle_config = BattleConfigLoader()