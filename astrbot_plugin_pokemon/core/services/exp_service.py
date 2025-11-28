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

    def get_required_exp_for_level(self, level: int) -> int:
        """
        计算达到指定等级所需的总经验值（基于n³公式）
        """
        if level <= 1:
            return 1
        return level ** 3

    def get_exp_needed_for_next_level(self, current_level: int) -> int:
        """
        计算从当前等级升到下一级所需的经验值
        """
        if current_level < 1:
            return 1
        return self.get_required_exp_for_level(current_level + 1) - self.get_required_exp_for_level(current_level)

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

    def calculate_user_exp_gain(self, wild_pokemon_level: int, battle_result: str) -> int:
        """
        计算用户在战斗后获得的经验值
        根据新规则，玩家不获得经验
        """
        # 根据新规则，玩家不获得经验
        return 0

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

    def update_pokemon_after_battle(self, user_id: str, pokemon_id: int, exp_gained: int) -> Dict[str, Any]:
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

        return {
            "success": True,
            "exp_gained": exp_gained,
            "level_up_info": level_up_info,
            "pokemon_id": pokemon_id,
            "pokemon_name": pokemon_data.name or '未知宝可梦'
        }

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
        new_hp = calculate_stat(base_hp, hp_iv, hp_ev, new_level, is_hp=True)
        # 非HP属性: ((种族值 × 2 + IV + EV ÷ 4) × 等级) ÷ 100 + 5
        new_attack = calculate_stat(base_attack, attack_iv, attack_ev, new_level)
        new_defense = calculate_stat(base_defense, defense_iv, defense_ev, new_level)
        new_sp_attack = calculate_stat(base_sp_attack, sp_attack_iv, sp_attack_ev, new_level)
        new_sp_defense = calculate_stat(base_sp_defense, sp_defense_iv, sp_defense_ev, new_level)
        new_speed = calculate_stat(base_speed, speed_iv, speed_ev, new_level)
        new_pokemon_attributes = {
            'hp': new_hp,
            'attack': new_attack,
            'defense': new_defense,
            'sp_attack': new_sp_attack,
            'sp_defense': new_sp_defense,
            'speed': new_speed,
        }
        # 更新宝可梦的属性
        self.user_pokemon_repo.update_pokemon_attributes(new_pokemon_attributes, pokemon_id, user_id)
        return True

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

    def update_team_pokemon_after_battle(self, user_id: str, team_pokemon_ids: list, exp_gained: int) -> list:
        """
        战斗后更新队伍中所有宝可梦的经验值和等级
        """
        results = []
        for pokemon_id in team_pokemon_ids:
            result = self.update_pokemon_after_battle(user_id, int(pokemon_id), exp_gained)
            results.append(result)
        return results

    def check_learnable_moves(self, species_id: int, current_level: int, new_level: int, current_moves) -> tuple[list, list]:
        """
        检查宝可梦在升级过程中可以学习的新技能
        """
        return self._check_and_learn_new_moves(species_id, current_level, new_level, current_moves)

    def add_move_to_pokemon(self, moves, new_move_id: int) -> tuple:
        """
        将新技能添加到宝可梦的技能列表中
        """
        return self._add_move_to_pokemon(moves, new_move_id)

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