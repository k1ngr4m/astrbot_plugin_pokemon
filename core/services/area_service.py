import random
from typing import Dict, Any, List, Optional
from ..repositories.abstract_repository import (
    AbstractAreaRepository, AbstractItemTemplateRepository, AbstractUserRepository
)
from ..domain.area import AdventureArea, AreaPokemon
from ..utils import get_now


class AreaService:
    """冒险区域相关的业务逻辑服务"""

    def __init__(
            self,
            area_repo: AbstractAreaRepository,
            item_template_repo: AbstractItemTemplateRepository,
            user_repo: AbstractUserRepository,
            config: Dict[str, Any]
    ):
        self.area_repo = area_repo
        self.item_template_repo = item_template_repo
        self.user_repo = user_repo
        self.config = config

    def _calculate_pokemon_stats(self, base_stats: Dict[str, int], level: int) -> Dict[str, int]:
        """
        计算宝可梦的属性值（用于野生宝可梦）
        Args:
            base_stats: 基础属性值字典，包括hp, attack, defense, sp_attack, sp_defense, speed
            level: 宝可梦等级
        Returns:
            包含各项属性值的字典
        """
        # 为野生宝可梦生成独立的IV值（每项0-31均匀随机，符合官方设定）
        ivs = {
            'hp': random.randint(0, 31),
            'attack': random.randint(0, 31),
            'defense': random.randint(0, 31),
            'sp_attack': random.randint(0, 31),
            'sp_defense': random.randint(0, 31),
            'speed': random.randint(0, 31)
        }

        # 野生宝可梦初始努力值为0
        evs = {
            'hp': 0,
            'attack': 0,
            'defense': 0,
            'sp_attack': 0,
            'sp_defense': 0,
            'speed': 0
        }

        # 计算HP值
        # 宝可梦的HP计算公式：int((种族值*2 + 个体值 + 努力值/4) * 等级/100) + 等级 + 10
        hp = int((base_stats['hp'] * 2 + ivs['hp'] + evs['hp'] // 4) * level / 100) + level + 10
        # 确保HP至少为基础值的一半（向下取整后至少为1）
        min_hp = max(1, base_stats['hp'] // 2)
        current_hp = max(min_hp, hp)

        # 计算其他属性值（非HP属性使用不同的计算公式）
        # 非HP属性计算公式：int(((种族值*2 + 个体值 + 努力值/4) * 等级/100) + 5)
        attack = int(((base_stats['attack'] * 2 + ivs['attack'] + evs['attack'] // 4) * level / 100) + 5)
        defense = int(((base_stats['defense'] * 2 + ivs['defense'] + evs['defense'] // 4) * level / 100) + 5)
        sp_attack = int(((base_stats['sp_attack'] * 2 + ivs['sp_attack'] + evs['sp_attack'] // 4) * level / 100) + 5)
        sp_defense = int(((base_stats['sp_defense'] * 2 + ivs['sp_defense'] + evs['sp_defense'] // 4) * level / 100) + 5)
        speed = int(((base_stats['speed'] * 2 + ivs['speed'] + evs['speed'] // 4) * level / 100) + 5)

        return {
            'hp': current_hp,
            'attack': attack,
            'defense': defense,
            'sp_attack': sp_attack,
            'sp_defense': sp_defense,
            'speed': speed,
            'ivs': ivs,
            'evs': evs
        }

    def get_all_areas(self) -> Dict[str, Any]:
        """
        获取所有可冒险的区域列表
        Returns:
            包含区域列表的字典
        """
        try:
            areas = self.area_repo.get_all_areas()

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
                    "name": area.name,
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

    def get_area_detail(self, area_code: str) -> Dict[str, Any]:
        """
        获取特定区域的详细信息，包括该区域可遇见的宝可梦
        Args:
            area_code: 区域代码
        Returns:
            包含区域详细信息的字典
        """
        try:
            # 验证区域代码格式
            if not (area_code.startswith('A') and len(area_code) == 4 and area_code[1:].isdigit()):
                return {
                    "success": False,
                    "message": "区域代码格式不正确（应为A开头的四位数，如A001）"
                }

            # 获取区域信息
            area = self.area_repo.get_area_by_code(area_code)
            if not area:
                return {
                    "success": False,
                    "message": f"未找到区域 {area_code}"
                }

            # 获取该区域的宝可梦列表
            area_pokemon_list = self.area_repo.get_area_pokemon_by_area_code(area_code)

            # 获取宝可梦详细信息
            pokemon_details = []
            for area_pokemon in area_pokemon_list:
                pokemon_template = self.item_template_repo.get_pokemon_by_id(area_pokemon.pokemon_species_id)
                if pokemon_template:
                    pokemon_details.append({
                        "species_id": pokemon_template.id,
                        "name": pokemon_template.name_cn,
                        "encounter_rate": area_pokemon.encounter_rate,
                        "min_level": area_pokemon.min_level,
                        "max_level": area_pokemon.max_level
                    })

            # 按遇见概率排序
            pokemon_details.sort(key=lambda x: x["encounter_rate"], reverse=True)

            return {
                "success": True,
                "area": {
                    "area_code": area.area_code,
                    "name": area.name,
                    "description": area.description or "暂无描述",
                    "min_level": area.min_level,
                    "max_level": area.max_level
                },
                "pokemon_list": pokemon_details,
                "pokemon_count": len(pokemon_details)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取区域详情失败: {str(e)}"
            }

    def adventure_in_area(self, user_id: str, area_code: str) -> Dict[str, Any]:
        """
        在指定区域进行冒险，随机刷新一只野生宝可梦
        Args:
            user_id: 用户ID
            area_code: 区域代码
        Returns:
            包含冒险结果的字典
        """
        try:
            # 首先验证用户是否存在
            user = self.user_repo.get_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "message": "用户不存在"
                }

            # 验证区域代码格式
            if not (area_code.startswith('A') and len(area_code) == 4 and area_code[1:].isdigit()):
                return {
                    "success": False,
                    "message": "区域代码格式不正确（应为A开头的四位数，如A001）"
                }

            # 获取区域信息
            area = self.area_repo.get_area_by_code(area_code)
            if not area:
                return {
                    "success": False,
                    "message": f"未找到区域 {area_code}"
                }

            # 获取该区域的宝可梦列表
            area_pokemon_list = self.area_repo.get_area_pokemon_by_area_code(area_code)
            if not area_pokemon_list:
                return {
                    "success": False,
                    "message": f"区域 {area.name} 中暂无野生宝可梦"
                }

            # 根据遇见概率随机选择一只宝可梦
            total_rate = sum(ap.encounter_rate for ap in area_pokemon_list)
            random_value = random.uniform(0, total_rate)

            selected_area_pokemon = None
            cumulative_rate = 0

            for area_pokemon in area_pokemon_list:
                cumulative_rate += area_pokemon.encounter_rate
                if random_value <= cumulative_rate:
                    selected_area_pokemon = area_pokemon
                    break

            # 如果没有选中，选择最后一个（兜底）
            if not selected_area_pokemon:
                selected_area_pokemon = area_pokemon_list[-1]

            # 获取选中宝可梦的详细信息
            pokemon_template = self.item_template_repo.get_pokemon_by_id(selected_area_pokemon.pokemon_species_id)
            if not pokemon_template:
                return {
                    "success": False,
                    "message": "无法获取野生宝可梦信息"
                }

            # 根据区域设置随机等级
            min_level = selected_area_pokemon.min_level
            max_level = selected_area_pokemon.max_level
            wild_pokemon_level = random.randint(min_level, max_level)

            # 计算野生宝可梦的属性值
            base_stats = {
                'hp': pokemon_template.base_hp,
                'attack': pokemon_template.base_attack,
                'defense': pokemon_template.base_defense,
                'sp_attack': pokemon_template.base_sp_attack,
                'sp_defense': pokemon_template.base_sp_defense,
                'speed': pokemon_template.base_speed
            }
            stats = self._calculate_pokemon_stats(base_stats, wild_pokemon_level)

            return {
                "success": True,
                "message": f"在 {area.name} 中遇到了野生的 {pokemon_template.name_cn}！",
                "wild_pokemon": {
                    "species_id": pokemon_template.id,
                    "name": pokemon_template.name_cn,
                    "level": wild_pokemon_level,
                    "encounter_rate": selected_area_pokemon.encounter_rate,
                    # 属性值
                    "hp": stats['hp'],
                    "attack": stats['attack'],
                    "defense": stats['defense'],
                    "sp_attack": stats['sp_attack'],
                    "sp_defense": stats['sp_defense'],
                    "speed": stats['speed'],
                    "ivs": stats['ivs'],
                    "evs": stats['evs']
                },
                "area": {
                    "area_code": area.area_code,
                    "name": area.name
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"冒险过程中发生错误: {str(e)}"
            }