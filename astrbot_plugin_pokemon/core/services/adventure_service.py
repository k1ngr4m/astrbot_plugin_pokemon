import math
import random
from itertools import accumulate
from typing import Dict, Any, List, Tuple

from .exp_service import ExpService
from .pokemon_service import PokemonService
from ..models.common_models import BaseResult
from ...interface.response.answer_enum import AnswerEnum
from ..models.pokemon_models import WildPokemonInfo, PokemonStats, PokemonIVs, PokemonEVs, \
    UserPokemonInfo, WildPokemonEncounterLog, PokemonMoves
from ..models.user_models import UserTeam, UserItems
from ...infrastructure.repositories.abstract_repository import (
    AbstractAdventureRepository, AbstractPokemonRepository, AbstractUserRepository, AbstractTeamRepository
)
from ..models.adventure_models import AdventureResult, LocationInfo, BattleResult
from astrbot.api import logger


class AdventureService:
    """冒险区域相关的业务逻辑服务"""

    def __init__(
            self,
            adventure_repo: AbstractAdventureRepository,
            pokemon_repo: AbstractPokemonRepository,
            team_repo: AbstractTeamRepository,
            pokemon_service: PokemonService,
            user_repo: AbstractUserRepository,
            exp_service: ExpService,
            config: Dict[str, Any]
    ):
        self.adventure_repo = adventure_repo
        self.pokemon_repo = pokemon_repo
        self.team_repo = team_repo
        self.pokemon_service = pokemon_service
        self.user_repo = user_repo
        self.exp_service = exp_service
        self.config = config
        # ----------------------
        # 宝可梦属性克制表（第三世代及之后全属性，key: 攻击属性, value: {防御属性: 克制系数}）
        # ----------------------
        self.TYPE_CHART = {
            'normal': {'rock': 0.5, 'ghost': 0.0, 'steel': 0.5},
            'fire': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 2.0, 'bug': 2.0, 'rock': 0.5, 'dragon': 0.5, 'steel': 2.0},
            'water': {'fire': 2.0, 'water': 0.5, 'grass': 0.5, 'ground': 2.0, 'rock': 2.0, 'dragon': 0.5},
            'electric': {'water': 2.0, 'electric': 0.5, 'grass': 0.5, 'ground': 0.0, 'flying': 2.0, 'dragon': 0.5},
            'grass': {'fire': 0.5, 'water': 2.0, 'grass': 0.5, 'poison': 0.5, 'ground': 2.0, 'flying': 0.5, 'bug': 0.5, 'rock': 2.0, 'dragon': 0.5, 'steel': 0.5},
            'ice': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 0.5, 'ground': 2.0, 'flying': 2.0, 'dragon': 2.0, 'steel': 0.5},
            'fighting': {'normal': 2.0, 'ice': 2.0, 'poison': 0.5, 'flying': 0.5, 'psychic': 0.5, 'bug': 0.5, 'rock': 2.0, 'ghost': 0.0, 'dark': 2.0, 'steel': 2.0, 'fairy': 0.5},
            'poison': {'grass': 2.0, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'ghost': 0.5, 'steel': 0.0, 'fairy': 2.0},
            'ground': {'fire': 2.0, 'electric': 2.0, 'grass': 0.5, 'poison': 2.0, 'flying': 0.0, 'bug': 0.5, 'rock': 2.0, 'steel': 2.0},
            'flying': {'electric': 0.5, 'grass': 2.0, 'fighting': 2.0, 'bug': 2.0, 'rock': 0.5, 'steel': 0.5},
            'psychic': {'fighting': 2.0, 'poison': 2.0, 'psychic': 0.5, 'dark': 0.0, 'steel': 0.5},
            'bug': {'fire': 0.5, 'grass': 2.0, 'fighting': 0.5, 'poison': 0.5, 'flying': 0.5, 'psychic': 2.0, 'ghost': 0.5, 'dark': 2.0, 'steel': 0.5, 'fairy': 0.5},
            'rock': {'fire': 2.0, 'ice': 2.0, 'fighting': 0.5, 'ground': 0.5, 'flying': 2.0, 'bug': 2.0, 'steel': 0.5},
            'ghost': {'normal': 0.0, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5},
            'dragon': {'dragon': 2.0, 'steel': 0.5, 'fairy': 0.0},
            'dark': {'fighting': 0.5, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5, 'fairy': 0.5},
            'steel': {'fire': 0.5, 'water': 0.5, 'electric': 0.5, 'ice': 2.0, 'rock': 2.0, 'steel': 0.5, 'fairy': 2.0},
            'fairy': {'fighting': 2.0, 'poison': 0.5, 'bug': 0.5, 'dragon': 2.0, 'dark': 2.0, 'steel': 0.5}
        }

    def get_all_locations(self) -> BaseResult[List[LocationInfo]]:
        """
        获取所有可冒险的区域列表
        Returns:
            包含区域列表的字典
        """

        locations = self.adventure_repo.get_all_locations()

        if not locations:
            return BaseResult(
                success=True,
                message=AnswerEnum.ADVENTURE_NO_LOCATIONS.value,
            )

        formatted_locations: List[LocationInfo] = []
        for location in locations:
            location_info: LocationInfo = LocationInfo(
                id=location.id,
                name=location.name,
                description=location.description or "暂无描述",
                min_level=location.min_level,
                max_level=location.max_level
            )
            formatted_locations.append(location_info)


        return BaseResult(
            success=True,
            message=AnswerEnum.ADVENTURE_LOCATIONS_FOUND.value,
            data=formatted_locations
        )


    def adventure_in_location(self, user_id: str, location_id: int) -> BaseResult[AdventureResult]:
        """
        在指定区域进行冒险，随机刷新一只野生宝可梦
        Args:
            user_id: 用户ID
            location_id: 区域ID
        Returns:
            包含冒险结果的字典
        """
        # 1. 获取区域信息
        location = self.adventure_repo.get_location_by_id(location_id)
        if not location:
            return BaseResult(
                success=False,
                message=AnswerEnum.ADVENTURE_LOCATION_NOT_FOUND.value.format(location_id=location_id)
            )
        # 2 获取该区域的宝可梦列表
        location_pokemon_list = self.adventure_repo.get_location_pokemon_by_location_id(location_id)
        if not location_pokemon_list:
            return BaseResult(
                success=False,
                message=AnswerEnum.ADVENTURE_LOCATION_NO_POKEMON.value.format(location_name=location.name)
            )
        # 3. 权重随机选择宝可梦（使用itertools.accumulate简化累加逻辑）
        encounter_rates = [ap.encounter_rate for ap in location_pokemon_list]
        total_rate = sum(encounter_rates)
        random_value = random.uniform(0, total_rate)

        # 累加概率，找到第一个超过随机值的宝可梦
        for idx, cumulative_rate in enumerate(accumulate(encounter_rates)):
            if random_value <= cumulative_rate:
                selected_location_pokemon = location_pokemon_list[idx]
                break
        else:
            # 兜底：如果循环未触发break（理论上不会发生），取最后一个
            selected_location_pokemon = location_pokemon_list[-1]

        # 4. 生成宝可梦等级（使用变量名简化赋值）
        min_level = selected_location_pokemon.min_level
        max_level = selected_location_pokemon.max_level
        wild_pokemon_level = random.randint(min_level, max_level)
        # 5. 创建野生宝可梦（直接使用返回结果，无需额外处理）
        wild_pokemon_result = self.pokemon_service.create_single_pokemon(
            species_id=selected_location_pokemon.pokemon_species_id,
            max_level=wild_pokemon_level,
            min_level=wild_pokemon_level
        )
        if not wild_pokemon_result.success:
            return BaseResult(
                success=False,
                message=wild_pokemon_result.message
            )
        wild_pokemon = wild_pokemon_result.data
        wild_pokemon_info = WildPokemonInfo(
                id=0,
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
                moves=PokemonMoves(
                    move1_id=wild_pokemon.moves.move1_id,
                    move2_id=wild_pokemon.moves.move2_id,
                    move3_id=wild_pokemon.moves.move3_id,
                    move4_id=wild_pokemon.moves.move4_id,
                )
        )
        wild_pokemon_id = self.pokemon_repo.add_wild_pokemon(wild_pokemon_info)

        self.pokemon_repo.add_user_encountered_wild_pokemon(
            user_id=user_id,
            wild_pokemon_id = wild_pokemon_id,
            location_id=location.id,
            encounter_rate=selected_location_pokemon.encounter_rate,
        )
        return BaseResult(
            success=True,
            message=AnswerEnum.ADVENTURE_SUCCESS.value,
            data=AdventureResult(
                wild_pokemon=wild_pokemon_info,
                location=LocationInfo(
                    id=location.id,
                    name=location.name,
                ),
            )
        )

    def adventure_in_battle(self, user_id: str, wild_pokemon_info: WildPokemonInfo) -> BaseResult:
        """
        处理用户与野生宝可梦战斗的结果。

        :param user_id: 用户ID
        :param wild_pokemon_info: 野生宝可梦信息
        :return: 战斗结果
        """
        # 检查用户是否有设置队伍
        user_team_data: UserTeam = self.team_repo.get_user_team(user_id)
        user = self.user_repo.get_user_by_id(user_id)
        if not user_team_data:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_TEAM_NOT_SET.value,
            )

        user_team_list: List[int] = user_team_data.team_pokemon_ids

        # 开始战斗，传入玩家的队伍
        result = self.start_battle(user_id, wild_pokemon_info, user_team_list)
        return result

    def start_battle(self, user_id: str, wild_pokemon_info: WildPokemonInfo, user_team_list: List[int] = None) -> BaseResult[BattleResult]:
        """
        开始一场与野生宝可梦的战斗
        Args:
            user_id: 用户ID
            wild_pokemon_info: 野生宝可梦数据
            user_team_list: 用户队伍中的宝可梦ID列表
        Returns:
            包含战斗结果的字典
        """

        user_pokemon_id = user_team_list[0]
        user_pokemon_info = self.user_repo.get_user_pokemon_by_id(user_id, user_pokemon_id)
        # 计算战斗胜率
        user_win_rate, wild_win_rate = self.calculate_battle_win_rate(user_pokemon_info, wild_pokemon_info)

        # 随机决定战斗结果
        import random
        result = "success" if random.random() * 100 < user_win_rate else "fail"

        # 处理经验值（仅在胜利时）
        exp_details = {}
        if self.exp_service and result == "success":
            # 计算宝可梦获得的经验值
            pokemon_exp_gained = self.exp_service.calculate_pokemon_exp_gain(wild_pokemon_id=wild_pokemon_info.id, wild_pokemon_level=wild_pokemon_info.level, battle_result=result)
            # 获取用户队伍中的所有宝可梦
            user_team_data:UserTeam = self.team_repo.get_user_team(user_id)
            team_pokemon_results = []
            team_pokemon_ids=user_team_data.team_pokemon_ids
            # 更新队伍中所有宝可梦的经验值
            if team_pokemon_ids:
                team_pokemon_results = self.exp_service.update_team_pokemon_after_battle(
                    user_id, team_pokemon_ids, pokemon_exp_gained)

            exp_details = {
                "pokemon_exp": team_pokemon_results[0] if team_pokemon_results else {"success": False, "message": AnswerEnum.TEAM_GET_NO_TEAM.value},
                "team_pokemon_results": team_pokemon_results
            }

        elif self.exp_service and result != "success":
            # 战斗失败时不获得经验
            exp_details = {
                "pokemon_exp": {"success": True, "exp_gained": 0, "message": AnswerEnum.BATTLE_FAILURE_NO_EXP.value},
                "user_exp": {"success": True, "exp_gained": 0, "message": AnswerEnum.BATTLE_FAILURE_NO_EXP.value},
                "team_pokemon_results": []
            }

        # 更新野生宝可梦遇到日志 - 标记为已战斗
        # 获取最近的野生宝可梦遇到记录
        recent_encounters: List[WildPokemonEncounterLog] = self.pokemon_repo.get_user_encounters(user_id, limit=5)
        encounter_log_id = None
        for encounter in recent_encounters:
            if (encounter.wild_pokemon_id == wild_pokemon_info.id and
                encounter.is_battled == 0):  # 未战斗的记录
                encounter_log_id = encounter.id
                break
        if encounter_log_id:
            battle_outcome = "win" if result == "success" else "lose"
            self.pokemon_repo.update_encounter_log(
                log_id=encounter_log_id,
                is_battled=1,
                battle_result=battle_outcome
            )

        return BaseResult(
            success=True,
            message=AnswerEnum.BATTLE_SUCCESS.value,
            data=BattleResult(
                user_pokemon={
                    "name": user_pokemon_info.name,
                    "species": user_pokemon_info.species_id,
                    "level": user_pokemon_info.level,
                    "hp": user_pokemon_info.stats.hp,
                    "attack": user_pokemon_info.stats.attack,
                    "defense": user_pokemon_info.stats.defense,
                    "speed": user_pokemon_info.stats.speed
                },
                wild_pokemon={
                    "name": wild_pokemon_info.name,
                    "level": wild_pokemon_info.level,
                    "hp": wild_pokemon_info.stats.hp,
                    "attack": wild_pokemon_info.stats.attack,
                    "defense": wild_pokemon_info.stats.defense,
                    "speed": wild_pokemon_info.stats.speed
                },
                win_rates={
                    "user_win_rate": user_win_rate,
                    "wild_win_rate": wild_win_rate
                },
                result=result,
                exp_details=exp_details
            )
        )


    def calculate_type_effectiveness(self, attacker_types: List[str], defender_types: List[str]) -> float:
        """
        计算属性克制系数
        攻击方对防御方的总克制系数（取双属性的乘积，如火焰+飞行对岩石：2.0×2.0=4.0）
        """
        effectiveness = 1.0
        for attacker_type in attacker_types:
            type_name = attacker_type.lower()
            if type_name in self.TYPE_CHART:
                for defender_type in defender_types:
                    def_type_name = defender_type.lower()
                    effectiveness *= self.TYPE_CHART[type_name].get(def_type_name, 1.0)
        return effectiveness

    def calculate_battle_win_rate(self, user_pokemon: UserPokemonInfo, wild_pokemon: WildPokemonInfo,
                                  skill_type: str = 'special') -> Tuple[float, float]:
        """
        计算宝可梦战斗胜率 (基于真实伤害公式与击杀回合数模拟)

        Args:
            user_pokemon: 攻击方宝可梦数据
            wild_pokemon: 防御方宝可梦数据
            skill_type: 用户选用的技能类型 ('physical' 或 'special')

        Returns:
            Tuple[float, float]: (攻击方胜率%, 防御方胜率%)
        """

        # ----------------------
        # 辅助函数：标准宝可梦伤害公式
        # ----------------------
        def calculate_damage(attacker_level, atk_stat, def_stat, power, type_effectiveness):
            # 宝可梦伤害公式:
            # Damage = ((((2 * Level / 5 + 2) * Attack * Power / Defense) / 50) + 2) * Modifier
            # 这里假设技能威力 Power 为 80 (标准强力技能，如喷射火焰/十万伏特)
            # 随机数 (0.85-1.0) 我们将在最后计算胜率概率时考虑，这里取期望值 0.925

            base_damage = ((2 * attacker_level / 5 + 2) * power * atk_stat / max(1, def_stat)) / 50 + 2
            final_damage = base_damage * type_effectiveness * 0.925  # 0.925是随机浮动的平均值
            return final_damage
        print(f"user_pokemon: {user_pokemon}")
        print(f"wild_pokemon: {wild_pokemon}")
        # ----------------------
        # 1. 准备数据
        # ----------------------

        # 获取属性类型
        user_types = self.pokemon_repo.get_pokemon_types(user_pokemon.species_id) or ['normal']
        wild_types = self.pokemon_repo.get_pokemon_types(wild_pokemon.species_id) or ['normal']

        # 计算属性克制倍率
        # 玩家对野怪的克制
        user_type_mod = self.calculate_type_effectiveness(user_types, wild_types)
        # 野怪对玩家的克制
        wild_type_mod = self.calculate_type_effectiveness(wild_types, user_types)

        # 确定攻防属性
        # 玩家：指定了物理/特殊
        user_atk_val = user_pokemon.stats.attack if skill_type == 'physical' else user_pokemon.stats.sp_attack
        wild_def_val_for_user = wild_pokemon.stats.defense if skill_type == 'physical' else wild_pokemon.stats.sp_defense

        # 野怪：智能选择它较高的攻击属性 (模拟野生宝可梦使用本系高攻技能)
        if wild_pokemon.stats.attack > wild_pokemon.stats.sp_attack:
            wild_atk_val = wild_pokemon.stats.attack
            user_def_val_for_wild = user_pokemon.stats.defense
        else:
            wild_atk_val = wild_pokemon.stats.sp_attack
            user_def_val_for_wild = user_pokemon.stats.sp_defense

        # 假设技能威力 (使用标准威力80，如果有本系加成 STAB 则 x1.5)
        # 这里简化处理：默认双方都使用威力 80 的技能
        move_power = 80

        # ----------------------
        # 2. 计算每回合伤害 (DPT)
        # ----------------------

        # 玩家对野怪造成的单发伤害
        damage_to_wild = calculate_damage(
            user_pokemon.level, user_atk_val, wild_def_val_for_user, move_power, user_type_mod
        )

        # 野怪对玩家造成的单发伤害
        damage_to_user = calculate_damage(
            wild_pokemon.level, wild_atk_val, user_def_val_for_wild, move_power, wild_type_mod
        )

        # ----------------------
        # 3. 计算击杀所需回合数 (Turns to Kill)
        # ----------------------

        # HP 修正：确保 HP 至少为 1
        user_hp = max(1, user_pokemon.stats.hp)
        wild_hp = max(1, wild_pokemon.stats.hp)

        # 玩家打死野怪需要几下？ (向上取整)
        turns_to_kill_wild = math.ceil(wild_hp / max(1, damage_to_wild))

        # 野怪打死玩家需要几下？
        turns_to_kill_user = math.ceil(user_hp / max(1, damage_to_user))

        # ----------------------
        # 4. 速度修正与胜率计算
        # ----------------------

        # 获取速度
        user_speed = user_pokemon.stats.speed
        wild_speed = wild_pokemon.stats.speed

        # 核心逻辑：谁先手？
        # 如果速度相同，视为50%概率先手
        user_is_faster = user_speed >= wild_speed

        # 这里的 win_score 不是最终胜率，而是一个胜势积分
        # 积分越高，胜率越接近 100%
        win_score = 0.0

        # 情况 A: 玩家斩杀回合数 明显少于 野怪 (例如玩家2刀死，野怪要5刀) -> 必胜
        if turns_to_kill_wild < turns_to_kill_user:
            # 优势巨大
            win_score = 2.0 + (turns_to_kill_user - turns_to_kill_wild)

            # 情况 B: 野怪斩杀回合数 明显少于 玩家 -> 必败
        elif turns_to_kill_wild > turns_to_kill_user:
            win_score = -2.0 - (turns_to_kill_wild - turns_to_kill_user)

        # 情况 C: 斩杀回合数相同 (例如都要 3 刀死) -> 拼速度
        else:  # turns_to_kill_wild == turns_to_kill_user
            if user_speed > wild_speed:
                # 我先手，我先打出第 N 刀 -> 我赢
                win_score = 1.5  # 速度优势
            elif user_speed < wild_speed:
                # 对面先手，对面先打出第 N 刀 -> 我输
                win_score = -1.5  # 速度劣势
            else:
                # 同速，纯随机
                win_score = 0.0

        # ----------------------
        # 5. 引入随机性 (Crit, Miss, Damage Roll) 并平滑胜率
        # ----------------------

        # 使用 Sigmoid 函数将 win_score 映射到 0-1
        # 调整 coefficient (0.8) 可以控制胜率曲线的陡峭程度
        # score = 0 -> 50%
        # score = 2 -> 83%
        # score = -2 -> 16%

        sigmoid_k = 0.8
        base_win_rate = 1 / (1 + math.exp(-sigmoid_k * win_score))

        # 考虑命中率和暴击的干扰 (95% 命中, 6.25% 暴击)
        # 我们不进行模拟，而是将胜率向 50% 收缩一点点，表示意外发生的可能性
        # 比如 99% 的胜率修正为 98%，保留一点翻车概率

        final_win_rate = base_win_rate * 0.96 + 0.02  # 压缩区间到 [2%, 98%]

        return round(final_win_rate * 100, 1), round((1 - final_win_rate) * 100, 1)

    def calculate_catch_success_rate(self, user_id: str, wild_pokemon: WildPokemonInfo, item_id: str) -> Dict[str, Any]:
        """
        计算捕捉成功率
        Args:
            user_id: 用户ID
            wild_pokemon: 野生宝可梦数据
        Returns:
            float: 捕捉成功率（0-1之间）
        """
        # 检查用户背包中的道具
        user_items:UserItems = self.user_repo.get_user_items(user_id)
        pokeball_item = None
        user_item_list = user_items.items
        if item_id is not None:
            # 用户指定了特定的道具ID
            for item in user_item_list:
                if item.item_id == item_id and int(item.category_id) == 34 and item.quantity > 0:
                    pokeball_item = item
                    break
        else:
            # 用户未指定道具ID，自动寻找第一个可用的精灵球
            for item in user_item_list:
                if int(item.category_id) == 34 and item.quantity > 0:
                    pokeball_item = item
                    break

        if not pokeball_item:
            if item_id is not None:
                message = f"❌ 找不到ID为 {item_id} 的精灵球或该道具不存在，无法进行捕捉！请检查道具ID或先通过签到或其他方式获得精灵球。"
            else:
                message = AnswerEnum.USER_POKEBALLS_EMPTY.value
            return {"success": False, "message": message}

        # 根据精灵球类型调整基础捕捉率
        ball_multiplier = 1.0  # 普通精灵球
        if pokeball_item.name_zh == '超级球':
            ball_multiplier = 1.5
        elif pokeball_item.name_zh == '高级球':
            ball_multiplier = 2.0
        elif pokeball_item.name_zh == '大师球':
            ball_multiplier = 255

        # 边界条件：当前HP不能小于0或大于最大HP，基础捕获率范围0~255
        max_hp = wild_pokemon.stats.hp
        # 假设current_hp为随机值，正态分布，均值为最大HP的3/4，标准差为最大HP的1/4
        temp_current_hp = int(random.gauss(max_hp * 3 / 4, max_hp / 4))
        current_hp = max(0, min(max_hp, temp_current_hp))  # 确保在有效范围内
        base_capture_rate = int(self.pokemon_repo.get_pokemon_capture_rate(wild_pokemon.species_id))

        status = "none"
        # 异常状态倍率映射
        status_multipliers = {
            "none": 1.0,
            "paralysis": 1.2,
            "burn": 1.2,
            "poison": 1.2,
            "sleep": 1.5,
            "freeze": 1.5
        }
        status_multi = status_multipliers.get(status.lower(), 1.0)

        # 计算核心公式
        if current_hp == 0:
            catch_value = 0  # 濒死宝可梦无法捕捉
        else:
            hp_term = 3 * max_hp - 2 * current_hp
            numerator = hp_term * base_capture_rate * ball_multiplier * status_multi
            denominator = 3 * max_hp
            catch_value = int(numerator // denominator)  # 向下取整

        # 判定值上限为255（超过则100%成功）
        catch_value = min(catch_value, 255)
        # 计算成功率（随机数0~255，共256种可能）
        success_rate = (catch_value / 256) if catch_value > 0 else 0.0

        return {
            "success": True,
            "message": f"判定值为{catch_value}，捕捉成功率为{round(success_rate, 2)}%",
            "data": {
                "catch_value": catch_value,
                "success_rate": round(success_rate, 2),
                "pokeball_item": pokeball_item,
            }
        }
