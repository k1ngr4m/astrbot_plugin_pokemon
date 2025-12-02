from typing import Dict, Any

from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.pokemon_models import PokemonBaseStats, PokemonMoves
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.infrastructure.repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractTeamRepository, AbstractMoveRepository,
    AbstractUserPokemonRepository,
)

class ExpService:
    """经验系统服务类，处理用户和宝可梦的经验值逻辑"""

    def __init__(
        self,
        user_repo: AbstractUserRepository,
        pokemon_repo: AbstractPokemonRepository,
        team_repo: AbstractTeamRepository,
        move_repo: AbstractMoveRepository,
        user_pokemon_repo: AbstractUserPokemonRepository,
        config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.team_repo = team_repo
        self.move_repo = move_repo
        self.user_pokemon_repo = user_pokemon_repo
        self.config = config

    # 计算达到指定等级所需的总经验值（基于n³公式）
    def get_required_exp_for_level(self, level: int) -> int:
        """
        计算达到指定等级所需的总经验值（基于n³公式）
        """
        if level <= 1:
            return 1
        return level ** 3

    # 计算从当前等级升到下一级所需的经验值
    def get_exp_needed_for_next_level(self, current_level: int) -> int:
        """
        计算从当前等级升到下一级所需的经验值
        """
        if current_level < 1:
            return 1
        return self.get_required_exp_for_level(current_level + 1) - self.get_required_exp_for_level(current_level)

    # 计算野生宝可梦在战斗后获得的经验值
    def calculate_pokemon_exp_gain(self, wild_pokemon_id: int, wild_pokemon_level: int, battle_result: str) -> int:
        """
        根据野生宝可梦等级和战斗结果计算经验值获取
        胜利时获得经验，失败时不获得经验
        公式：(基础经验值 × 野生宝可梦等级) ÷ 7
        """
        # 基础经验值从数据库获取
        base_exp = self.pokemon_repo.get_base_exp(wild_pokemon_id)

        # 如果胜利，获得经验值；如果失败，不获得经验值
        if battle_result == "success":
            exp_gained = (base_exp * wild_pokemon_level) // 7
            return max(1, exp_gained)  # 确保至少获得1点经验
        else:
            return 0  # 失败时不获得经验

    # 计算野生宝可梦在战斗后获得的EV奖励
    def calculate_pokemon_ev_gain(self, wild_pokemon_species_id: int, battle_result: str) -> Dict[str, int]:
        """
        根据野生宝可梦的effort数据计算EV奖励
        Args:
            wild_pokemon_species_id: 野生宝可梦的物种ID
            battle_result: 战斗结果 ("success" 或其他)
        Returns:
            Dict[str, int]: 包含hp_ev, attack_ev, defense_ev等EV奖励的字典
        """
        # 只有战斗胜利时才获得EV
        if battle_result != "success":
            return {
                "hp_ev": 0,
                "attack_ev": 0,
                "defense_ev": 0,
                "sp_attack_ev": 0,
                "sp_defense_ev": 0,
                "speed_ev": 0
            }

        # 获取野生宝可梦的物种数据，包括effort字段
        wild_pokemon_species = self.pokemon_repo.get_pokemon_by_id(wild_pokemon_species_id)
        if not wild_pokemon_species:
            return {
                "hp_ev": 0,
                "attack_ev": 0,
                "defense_ev": 0,
                "sp_attack_ev": 0,
                "sp_defense_ev": 0,
                "speed_ev": 0
            }

        # 解析effort JSON字段
        import json
        try:
            effort_data = json.loads(wild_pokemon_species.effort) if wild_pokemon_species.effort else []
        except json.JSONDecodeError:
            effort_data = []

        # 初始化EV奖励
        ev_rewards = {
            "hp_ev": 0,
            "attack_ev": 0,
            "defense_ev": 0,
            "sp_attack_ev": 0,
            "sp_defense_ev": 0,
            "speed_ev": 0
        }

        # stat_id 到字段的映射
        stat_id_to_field = {
            1: "hp_ev",
            2: "attack_ev",
            3: "defense_ev",
            4: "sp_attack_ev",
            5: "sp_defense_ev",
            6: "speed_ev"
        }

        # 根据effort数据添加EV奖励
        for effort in effort_data:
            stat_id = effort.get("stat_id", 0)
            value = effort.get("value", 0)

            if stat_id in stat_id_to_field:
                field_name = stat_id_to_field[stat_id]
                ev_rewards[field_name] += value

        return ev_rewards

    # 检查宝可梦是否升级
    def check_pokemon_level_up(self, current_level: int, current_exp: int) -> Dict[str, Any]:
        """
        检查宝可梦是否升级
        返回包含升级信息的字典
        """
        levels_gained = 0
        new_level = current_level
        remaining_exp = current_exp

        # 检查是否能升级多级
        while new_level < 100 and remaining_exp >= self.get_required_exp_for_level(new_level + 1):
            new_level += 1
            levels_gained += 1
            # 扣除升级所需的经验
            remaining_exp = remaining_exp - self.get_exp_needed_for_next_level(new_level - 1)

        new_level = min(100, new_level)
        return {
            "should_level_up": levels_gained > 0,
            "levels_gained": levels_gained,
            "new_level": new_level,
            "new_exp": remaining_exp,
            "required_exp_for_next": self.get_required_exp_for_level(new_level + 1) if new_level < 100 else 0
        }

    # 战斗后更新宝可梦的经验值和等级（考虑EV值）
    def update_pokemon_after_battle(self, user_id: str, pokemon_id: int, exp_gained: int, ev_gained: Dict[str, int] = None) -> Dict[str, Any]:
        """
        战斗后更新宝可梦的经验值和等级
        """
        # 获取用户宝可梦信息
        pokemon_data = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_data:
            return {"success": False, "message": "宝可梦不存在"}

        current_level = pokemon_data.level
        current_exp = pokemon_data.exp
        new_total_exp = current_exp + exp_gained

        # 如果有EV奖励，更新EV值
        if ev_gained:
            # 验证EV值在合理范围内
            for key in ev_gained:
                if ev_gained[key] < 0:
                    ev_gained[key] = 0

            # 更新宝可梦的EV值
            self._update_pokemon_ev(user_id, pokemon_id, ev_gained)
            # 根据新的EV值重新计算属性
            self._calculate_and_update_pokemon_stats(pokemon_id, pokemon_data.species_id, current_level, user_id)

        # 检查是否升级
        level_up_info = self.check_pokemon_level_up(current_level, new_total_exp)
        # 使用宝可梦的数字ID，而不是短码ID
        # 从数据库返回的数据中获取数字ID
        pokemon_id = pokemon_data.id

        # 更新宝可梦数据
        self.user_pokemon_repo.update_user_pokemon_exp(level_up_info["new_level"], level_up_info["new_exp"], pokemon_id, user_id)

        # 如果有升级，更新属性
        if level_up_info.get("levels_gained", 0) > 0:
            self._calculate_and_update_pokemon_stats(pokemon_id, pokemon_data.species_id, level_up_info["new_level"], user_id)

            # 升级后检查并学习新技能 - 使用升级前和升级后的等级
            move_learning_result = self.learn_moves_after_level_up_with_levels(user_id, pokemon_data.id, current_level, level_up_info["new_level"])
            level_up_info["move_learning_result"] = move_learning_result

            # 检查是否可以进化
            evolution_info = self.check_evolution(user_id, pokemon_id, level_up_info["new_level"])
            level_up_info["evolution_info"] = evolution_info

        return {
            "success": True,
            "exp_gained": exp_gained,
            "ev_gained": ev_gained or {"hp_ev": 0, "attack_ev": 0, "defense_ev": 0, "sp_attack_ev": 0, "sp_defense_ev": 0, "speed_ev": 0},
            "level_up_info": level_up_info,
            "pokemon_id": pokemon_id,
            "pokemon_name": pokemon_data.name or '未知宝可梦'
        }

    # 更新宝可梦的EV值（考虑单个属性的上限252和总和的上限510）
    def _update_pokemon_ev(self, user_id: str, pokemon_id: int, ev_gained: Dict[str, int]) -> bool:
        """
        更新宝可梦的EV值（考虑单个属性的上限252和总和的上限510）
        """
        # 获取当前宝可梦的EV数据
        pokemon_data = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_data:
            return False

        # 计算新的EV值（考虑上限）
        new_hp_ev = min(252, pokemon_data.evs.hp_ev + ev_gained.get("hp_ev", 0))
        new_attack_ev = min(252, pokemon_data.evs.attack_ev + ev_gained.get("attack_ev", 0))
        new_defense_ev = min(252, pokemon_data.evs.defense_ev + ev_gained.get("defense_ev", 0))
        new_sp_attack_ev = min(252, pokemon_data.evs.sp_attack_ev + ev_gained.get("sp_attack_ev", 0))
        new_sp_defense_ev = min(252, pokemon_data.evs.sp_defense_ev + ev_gained.get("sp_defense_ev", 0))
        new_speed_ev = min(252, pokemon_data.evs.speed_ev + ev_gained.get("speed_ev", 0))

        # 计算EV总和
        total_new_ev = new_hp_ev + new_attack_ev + new_defense_ev + new_sp_attack_ev + new_sp_defense_ev + new_speed_ev

        # 如果总和超过510，需要按照一定规则减少EV
        if total_new_ev > 510:
            # 计算需要减少的EV总量
            excess_ev = total_new_ev - 510

            # 按比例减少各项EV
            ev_values = [new_hp_ev, new_attack_ev, new_defense_ev, new_sp_attack_ev, new_sp_defense_ev, new_speed_ev]
            total_old = sum(ev_values)
            if total_old > 0:
                new_hp_ev = int(new_hp_ev * 510 / total_old)
                new_attack_ev = int(new_attack_ev * 510 / total_old)
                new_defense_ev = int(new_defense_ev * 510 / total_old)
                new_sp_attack_ev = int(new_sp_attack_ev * 510 / total_old)
                new_sp_defense_ev = int(new_sp_defense_ev * 510 / total_old)
                new_speed_ev = int(new_speed_ev * 510 / total_old)

                # 为了确保总和不超过510，再做一次检查和调整
                total_after_reduction = new_hp_ev + new_attack_ev + new_defense_ev + new_sp_attack_ev + new_sp_defense_ev + new_speed_ev
                if total_after_reduction > 510:
                    # 从最大的EV值开始减少，直到总和为510
                    ev_list = [new_hp_ev, new_attack_ev, new_defense_ev, new_sp_attack_ev, new_sp_defense_ev, new_speed_ev]
                    ev_names = ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']

                    # 按EV值降序排序索引
                    sorted_indices = sorted(range(6), key=lambda i: ev_list[i], reverse=True)

                    excess = total_after_reduction - 510
                    for i in sorted_indices:
                        if excess <= 0:
                            break
                        reduction = min(excess, ev_list[i])
                        ev_list[i] -= reduction
                        excess -= reduction

                    # 更新值
                    new_hp_ev, new_attack_ev, new_defense_ev, new_sp_attack_ev, new_sp_defense_ev, new_speed_ev = ev_list

        # 更新数据库中的EV值
        ev_data = {
            'hp_ev': new_hp_ev,
            'attack_ev': new_attack_ev,
            'defense_ev': new_defense_ev,
            'sp_attack_ev': new_sp_attack_ev,
            'sp_defense_ev': new_sp_defense_ev,
            'speed_ev': new_speed_ev
        }

        self.user_pokemon_repo.update_user_pokemon_ev(ev_data, pokemon_id, user_id)
        return True

    # 检查宝可梦是否满足进化条件
    def check_evolution(self, user_id: str, pokemon_id: int, new_level: int) -> Dict[str, Any]:
        """
        检查宝可梦是否满足进化条件
        返回包含进化信息的字典
        """
        # 获取用户宝可梦信息
        pokemon_data = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_data:
            return {"can_evolve": False, "message": "宝可梦不存在"}

        # 获取宝可梦的进化信息 - 查找满足等级要求的进化信息
        evolution_data = self.pokemon_repo.get_pokemon_evolutions(pokemon_data.species_id, new_level)

        if evolution_data:
            # 检查是否满足进化条件（主要检查等级条件）
            for evolution in evolution_data:
                # 检查等级条件
                if evolution.minimum_level > 0 and new_level >= evolution.minimum_level:
                    # 获取进化后的宝可梦信息
                    evolved_species = self.pokemon_repo.get_pokemon_by_id(evolution.evolved_species_id)
                    if evolved_species:
                        return {
                            "can_evolve": True,
                            "message": f"你的宝可梦 {pokemon_data.name} 已经达到{new_level}级，可以进化为 {evolved_species.name_zh} 了！",
                            "evolved_species_id": evolution.evolved_species_id,
                            "evolved_species_name": evolved_species.name_zh,
                            "evolution_id": evolution.id
                        }

        return {"can_evolve": False, "message": "宝可梦暂无符合的进化条件"}

    # 根据新的等级计算并更新宝可梦的属性
    def _calculate_and_update_pokemon_stats(self, pokemon_id: int, species_id: int, new_level: int, user_id: str) -> bool:
        """
        根据新的等级计算并更新宝可梦的属性
        使用官方宝可梦公式: ((种族值 × 2 + IV + EV ÷ 4) × 等级) ÷ 100 + 5 或 + 10 (HP)
        """
        def calculate_stat(base: int, iv: int, ev: int, level: int, is_hp: bool = False) -> int:
            """
            根据种族值、IV、EV、等级计算最终属性值
            Args:
                base: 种族值
                iv: 个体值
                ev: 努力值
                level: 等级
                is_hp: 是否为HP属性（HP公式不同）
            """
            base_calculation = (base * 2 + iv + ev // 4) * level / 100
            if is_hp:
                return int(base_calculation) + level + 10
            return int(base_calculation) + 5

        # 获取宝可梦的种族值
        species_data = self.pokemon_repo.get_pokemon_by_id(species_id)
        if not species_data:
            return False

        # 获取宝可梦的IV和EV值
        pokemon_data = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_data:
            return False

        # 获取各种族值
        base_data: PokemonBaseStats = species_data.base_stats
        base_hp = base_data.base_hp
        base_attack = base_data.base_attack
        base_defense = base_data.base_defense
        base_sp_attack = base_data.base_sp_attack
        base_sp_defense = base_data.base_sp_defense
        base_speed = base_data.base_speed

        # 获取IV值
        hp_iv = pokemon_data.ivs.hp_iv
        attack_iv = pokemon_data.ivs.attack_iv
        defense_iv = pokemon_data.ivs.defense_iv
        sp_attack_iv = pokemon_data.ivs.sp_attack_iv
        sp_defense_iv = pokemon_data.ivs.sp_defense_iv
        speed_iv = pokemon_data.ivs.speed_iv

        # 获取EV值
        hp_ev = pokemon_data.evs.hp_ev
        attack_ev = pokemon_data.evs.attack_ev
        defense_ev = pokemon_data.evs.defense_ev
        sp_attack_ev = pokemon_data.evs.sp_attack_ev
        sp_defense_ev = pokemon_data.evs.sp_defense_ev
        speed_ev = pokemon_data.evs.speed_ev

        # 根据公式计算新属性值
        # HP: ((种族值 × 2 + IV + EV ÷ 4) × 等级) ÷ 100 + 等级 + 10
        base_hp_val = calculate_stat(base_hp, hp_iv, hp_ev, new_level, is_hp=True)
        # 非HP属性: ((种族值 × 2 + IV + EV ÷ 4) × 等级) ÷ 100 + 5
        base_attack_val = calculate_stat(base_attack, attack_iv, attack_ev, new_level)
        base_defense_val = calculate_stat(base_defense, defense_iv, defense_ev, new_level)
        base_sp_attack_val = calculate_stat(base_sp_attack, sp_attack_iv, sp_attack_ev, new_level)
        base_sp_defense_val = calculate_stat(base_sp_defense, sp_defense_iv, sp_defense_ev, new_level)
        base_speed_val = calculate_stat(base_speed, speed_iv, speed_ev, new_level)

        # 创建基础属性对象
        base_stats_obj = PokemonStats(
            hp=base_hp_val,
            attack=base_attack_val,
            defense=base_defense_val,
            sp_attack=base_sp_attack_val,
            sp_defense=base_sp_defense_val,
            speed=base_speed_val
        )

        # 应用性格修正
        # 导入NatureService并应用性格修正
        from ..core.services.nature_service import NatureService
        from ..infrastructure.repositories.sqlite_nature_repo import SqliteNatureRepository

        temp_nature_repo = SqliteNatureRepository(self.user_pokemon_repo.db_path)
        temp_nature_service = NatureService(temp_nature_repo)

        # 应用性格修正
        final_stats = temp_nature_service.apply_nature_modifiers(base_stats_obj, pokemon_data.nature_id)

        # 更新宝可梦的属性
        new_pokemon_attributes = {
            'hp': final_stats.hp,
            'attack': final_stats.attack,
            'defense': final_stats.defense,
            'sp_attack': final_stats.sp_attack,
            'sp_defense': final_stats.sp_defense,
            'speed': final_stats.speed,
        }
        self.user_pokemon_repo.update_pokemon_attributes(new_pokemon_attributes, pokemon_id, user_id)
        return True

    # 检查宝可梦在升级过程中可以学习的新技能
    def _check_and_learn_new_moves(self, species_id: int, current_level: int, new_level: int, current_moves: PokemonMoves) -> tuple[list, list]:
        """
        检查宝可梦在升级过程中可以学习的新技能
        返回：(所有可学习的技能列表, 新学会的技能列表)
        """
        # 获取从current_level到new_level之间可以学会的所有技能
        all_learnable_moves = self.move_repo.get_level_up_moves(species_id, new_level)

        # 获取在升级过程中新学会的技能（在当前等级+1到新等级之间新增的技能）
        new_learned_moves = []
        if current_level < new_level:
            new_learned_moves = self.move_repo.get_moves_learned_in_level_range(species_id, current_level, new_level)
        else:
            # 如果等级没变，没有新技能
            new_learned_moves = []

        return all_learnable_moves, new_learned_moves

    # 将新技能添加到宝可梦的技能列表中
    def _add_move_to_pokemon(self, moves: PokemonMoves, new_move_id: int) -> tuple[PokemonMoves, bool]:
        """
        将新技能添加到宝可梦的技能列表中
        返回：(更新后的PokemonMoves对象, 是否成功添加)
        """
        # 检查是否已经有4个技能
        current_moves = [moves.move1_id, moves.move2_id, moves.move3_id, moves.move4_id]

        # 查找空槽位
        for i, move_id in enumerate(current_moves):
            if move_id is None or move_id == 0:
                # 找到空槽位，添加新技能
                if i == 0:
                    moves.move1_id = new_move_id
                elif i == 1:
                    moves.move2_id = new_move_id
                elif i == 2:
                    moves.move3_id = new_move_id
                elif i == 3:
                    moves.move4_id = new_move_id
                return moves, True

        # 如果没有空槽位，返回False，表示无法直接添加
        return moves, False

    # 宝可梦升级后检查并学习新技能（使用升级前和升级后的等级）
    def learn_moves_after_level_up_with_levels(self, user_id: str, pokemon_id: int, old_level: int, new_level: int) -> Dict[str, Any]:
        """
        宝可梦升级后检查并学习新技能（使用升级前和升级后的等级）
        返回包含学习的新技能信息的字典
        """
        # 获取用户宝可梦信息
        pokemon_data = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_data:
            return {"success": False, "message": "宝可梦不存在", "new_moves": []}

        # 检查可以学习的新技能
        all_learnable_moves, new_learned_moves = self._check_and_learn_new_moves(
            pokemon_data.species_id, old_level, new_level, pokemon_data.moves
        )

        if not new_learned_moves:
            # 没有新技能要学习
            return {
                "success": True,
                "message": "没有新技能可以学习",
                "new_moves": [],
                "requires_choice": False
            }

        # 检查当前技能槽是否还有空位
        current_moves_list = [pokemon_data.moves.move1_id, pokemon_data.moves.move2_id,
                            pokemon_data.moves.move3_id, pokemon_data.moves.move4_id]

        # 检查是否有重复技能，过滤掉已经拥有的技能
        filtered_new_moves = []
        for new_move_id in new_learned_moves:
            if new_move_id not in current_moves_list and new_move_id is not None and new_move_id != 0:
                filtered_new_moves.append(new_move_id)

        empty_slots_count = sum(1 for move_id in current_moves_list if move_id is None or move_id == 0)

        if empty_slots_count >= len(filtered_new_moves):
            if not filtered_new_moves:
                # 如果所有新技能都已经拥有，返回没有新技能学习
                return {
                    "success": True,
                    "message": "没有新技能可以学习",
                    "new_moves": [],
                    "requires_choice": False
                }

            # 如果有足够空位，直接添加所有新技能
            updated_moves = PokemonMoves(
                move1_id=pokemon_data.moves.move1_id,
                move2_id=pokemon_data.moves.move2_id,
                move3_id=pokemon_data.moves.move3_id,
                move4_id=pokemon_data.moves.move4_id
            )

            for new_move_id in filtered_new_moves:
                updated_moves, success = self._add_move_to_pokemon(updated_moves, new_move_id)
                if success:
                    # 获取技能信息用于返回
                    move_info = self.move_repo.get_move_by_id(new_move_id)
                    if not move_info:
                        move_info = {"id": new_move_id, "name_zh": f"技能{new_move_id}", "name_en": f"Move{new_move_id}"}

            # 更新宝可梦的技能
            self.user_pokemon_repo.update_pokemon_moves(updated_moves, pokemon_data.id, user_id)

            return {
                "success": True,
                "message": f"已自动学习{len(filtered_new_moves)}个新技能",
                "new_moves": [{"id": move_id, "name": self.move_repo.get_move_by_id(move_id)["name_zh"]
                              if self.move_repo.get_move_by_id(move_id) else f"技能{move_id}"}
                              for move_id in filtered_new_moves],
                "requires_choice": False
            }
        else:
            # 如果技能槽满了，需要玩家选择替换哪个技能（同样过滤掉重复的技能）
            if not filtered_new_moves:
                # 如果所有新技能都已经拥有，返回没有新技能学习
                return {
                    "success": True,
                    "message": "没有新技能可以学习",
                    "new_moves": [],
                    "requires_choice": False
                }
            else:
                return {
                    "success": True,
                    "message": "有新技能可以学习，但技能槽已满，需要选择替换",
                    "new_moves": [{"id": move_id, "name": self.move_repo.get_move_by_id(move_id)["name_zh"]
                                  if self.move_repo.get_move_by_id(move_id) else f"技能{move_id}"}
                                  for move_id in filtered_new_moves],
                    "requires_choice": True
                }

    # 宝可梦升级后检查并学习新技能（使用升级后的等级）
    def learn_new_moves_after_level_up(self, user_id: str, pokemon_id: int, new_level: int) -> Dict[str, Any]:
        """
        宝可梦升级后检查并学习新技能
        返回包含学习的新技能信息的字典
        """
        # 获取用户宝可梦信息
        pokemon_data = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_data:
            return {"success": False, "message": "宝可梦不存在", "new_moves": []}

        # 检查可以学习的新技能 - 使用宝可梦当前的等级（这在等级已更新后使用）
        all_learnable_moves, new_learned_moves = self._check_and_learn_new_moves(
            pokemon_data.species_id, pokemon_data.level, new_level, pokemon_data.moves
        )

        if not new_learned_moves:
            # 没有新技能要学习
            return {
                "success": True,
                "message": "没有新技能可以学习",
                "new_moves": [],
                "requires_choice": False
            }

        # 检查当前技能槽是否还有空位
        current_moves_list = [pokemon_data.moves.move1_id, pokemon_data.moves.move2_id,
                            pokemon_data.moves.move3_id, pokemon_data.moves.move4_id]

        # 检查是否有重复技能，过滤掉已经拥有的技能
        filtered_new_moves = []
        for new_move_id in new_learned_moves:
            if new_move_id not in current_moves_list and new_move_id is not None and new_move_id != 0:
                filtered_new_moves.append(new_move_id)

        empty_slots_count = sum(1 for move_id in current_moves_list if move_id is None or move_id == 0)

        if empty_slots_count >= len(filtered_new_moves):
            if not filtered_new_moves:
                # 如果所有新技能都已经拥有，返回没有新技能学习
                return {
                    "success": True,
                    "message": "没有新技能可以学习",
                    "new_moves": [],
                    "requires_choice": False
                }

            # 如果有足够空位，直接添加所有新技能
            updated_moves = PokemonMoves(
                move1_id=pokemon_data.moves.move1_id,
                move2_id=pokemon_data.moves.move2_id,
                move3_id=pokemon_data.moves.move3_id,
                move4_id=pokemon_data.moves.move4_id
            )

            for new_move_id in filtered_new_moves:
                updated_moves, success = self._add_move_to_pokemon(updated_moves, new_move_id)
                if success:
                    # 获取技能信息用于返回
                    move_info = self.move_repo.get_move_by_id(new_move_id)
                    if not move_info:
                        move_info = {"id": new_move_id, "name_zh": f"技能{new_move_id}", "name_en": f"Move{new_move_id}"}

            # 更新宝可梦的技能
            self.user_pokemon_repo.update_pokemon_moves(updated_moves, pokemon_data.id, user_id)

            return {
                "success": True,
                "message": f"已自动学习{len(filtered_new_moves)}个新技能",
                "new_moves": [{"id": move_id, "name": self.move_repo.get_move_by_id(move_id)["name_zh"]
                              if self.move_repo.get_move_by_id(move_id) else f"技能{move_id}"}
                              for move_id in filtered_new_moves],
                "requires_choice": False
            }
        else:
            # 如果技能槽满了，需要玩家选择替换哪个技能（同样过滤掉重复的技能）
            if not filtered_new_moves:
                # 如果所有新技能都已经拥有，返回没有新技能学习
                return {
                    "success": True,
                    "message": "没有新技能可以学习",
                    "new_moves": [],
                    "requires_choice": False
                }
            else:
                return {
                    "success": True,
                    "message": "有新技能可以学习，但技能槽已满，需要选择替换",
                    "new_moves": [{"id": move_id, "name": self.move_repo.get_move_by_id(move_id)["name_zh"]
                                  if self.move_repo.get_move_by_id(move_id) else f"技能{move_id}"}
                                  for move_id in filtered_new_moves],
                    "requires_choice": True
                }

    # 战斗后更新队伍中所有宝可梦的经验值和等级（考虑EV值）
    def update_team_pokemon_after_battle(self, user_id: str, team_pokemon_ids: list, exp_gained: int, ev_gained: Dict[str, int] = None) -> list:
        """
        战斗后更新队伍中所有宝可梦的经验值和等级
        """
        results = []
        for pokemon_id in team_pokemon_ids:
            result = self.update_pokemon_after_battle(user_id, int(pokemon_id), exp_gained, ev_gained)
            results.append(result)
        return results

    # 检查宝可梦在升级过程中可以学习的新技能（使用升级前和升级后的等级）
    def check_learnable_moves(self, species_id: int, current_level: int, new_level: int, current_moves) -> tuple[list, list]:
        """
        检查宝可梦在升级过程中可以学习的新技能
        """
        return self._check_and_learn_new_moves(species_id, current_level, new_level, current_moves)

    # 将新技能添加到宝可梦的技能列表中（考虑技能槽是否已满）
    def add_move_to_pokemon(self, moves, new_move_id: int) -> tuple:
        """
        将新技能添加到宝可梦的技能列表中
        """
        return self._add_move_to_pokemon(moves, new_move_id)

    # 战斗后更新用户的经验值和等级（考虑EV值）
    def update_user_after_battle(self, user_id: str, exp_gained: int) -> Dict[str, Any]:
        """
        战斗后更新用户的经验值和等级
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 计算新的总经验
        new_total_exp = user.exp + exp_gained
        current_level = user.level

        # 检查用户可以升到多少级
        new_level = current_level
        while new_level < 100 and new_total_exp >= self.get_required_exp_for_level(new_level + 1):
            new_level += 1

        levels_gained = new_level - current_level

        # 计算剩余经验（升级后剩余的经验）
        if new_level > current_level:
            # 如果升级了，计算升级后的剩余经验
            remaining_exp = new_total_exp - self.get_required_exp_for_level(new_level)
        else:
            # 没有升级，保留原来的逻辑
            remaining_exp = new_total_exp

        # 更新用户数据
        self.user_repo.update_user_exp(new_level, remaining_exp, user_id)

        return {
            "success": True,
            "exp_gained": exp_gained,
            "levels_gained": max(0, levels_gained),
            "new_level": new_level,
            "new_exp": remaining_exp
        }