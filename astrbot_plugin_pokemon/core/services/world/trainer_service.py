"""训练家服务类"""

import random
from typing import List, Optional, Dict, Any
from astrbot.api import logger
from ....infrastructure.repositories.sqlite_trainer_repo import SqliteTrainerRepository
from ....infrastructure.repositories.sqlite_pokemon_repo import SqlitePokemonRepository
from ....infrastructure.repositories.sqlite_user_pokemon_repo import SqliteUserPokemonRepository
from ....infrastructure.repositories.sqlite_user_repo import SqliteUserRepository
from ...models.trainer_models import Trainer, TrainerPokemon, TrainerEncounter, BattleTrainer
from ...models.pokemon_models import PokemonSpecies, UserPokemonInfo
from ..mechanics.pokemon_service import PokemonService

class TrainerService:
    """训练家服务类"""

    def __init__(self,
                 trainer_repo: SqliteTrainerRepository,
                 pokemon_repo: SqlitePokemonRepository,
                 user_pokemon_repo: SqliteUserPokemonRepository,
                 user_repo: SqliteUserRepository,
                 pokemon_service: PokemonService):
        self.trainer_repo = trainer_repo
        self.pokemon_repo = pokemon_repo
        self.user_pokemon_repo = user_pokemon_repo
        self.user_repo = user_repo
        self.pokemon_service = pokemon_service

    def get_trainer_by_id(self, trainer_id: int) -> Optional[Trainer]:
        """获取训练家信息"""
        return self.trainer_repo.get_trainer_by_id(trainer_id)

    def get_all_trainers(self) -> List[Trainer]:
        """获取所有训练家"""
        return self.trainer_repo.get_all_trainers()

    def get_trainers_at_location(self, location_id: int) -> List[Trainer]:
        """获取在特定位置的训练家"""
        location_records = self.trainer_repo.get_trainers_at_location(location_id)
        trainers = []
        for record in location_records:
            trainer = self.trainer_repo.get_trainer_by_id(record.trainer_id)
            if trainer:
                trainers.append(trainer)
        return trainers

    def get_trainer_with_pokemon(self, trainer_id: int) -> Optional[BattleTrainer]:
        """获取包含宝可梦的训练家信息用于战斗"""
        trainer = self.trainer_repo.get_trainer_by_id(trainer_id)
        if not trainer:
            return None

        # 获取训练家的宝可梦列表
        trainer_pokemon_list = self.trainer_repo.get_trainer_pokemon_by_trainer_id(trainer_id)

        # 将每个训练家的宝可梦转换为UserPokemonInfo对象
        pokemon_instances = []
        for trainer_pokemon in trainer_pokemon_list:
            # 生成特定等级的宝可梦实例
            pokemon_result = self.pokemon_service.create_single_pokemon(
                trainer_pokemon.pokemon_species_id,
                trainer_pokemon.level,
                trainer_pokemon.level,
            )
            # 检查结果是否成功
            if pokemon_result.success and pokemon_result.data:
                # 将PokemonDetail转换为UserPokemonInfo
                pokemon_detail = pokemon_result.data
                user_pokemon_info = UserPokemonInfo(
                    id=0,  # 新创建的宝可梦ID为0
                    species_id=pokemon_detail.base_pokemon.id,
                    name=pokemon_detail.base_pokemon.name_zh,
                    gender=pokemon_detail.gender,
                    level=pokemon_detail.level,
                    exp=pokemon_detail.exp,
                    stats=pokemon_detail.stats,
                    ivs=pokemon_detail.ivs,
                    evs=pokemon_detail.evs,
                    moves=pokemon_detail.moves,
                    nature_id=pokemon_detail.nature_id,
                    current_hp=pokemon_detail.stats.hp  # Initialize Full HP
                )
                pokemon_instances.append(user_pokemon_info)
            else:
                logger.warning(f"无法为训练家宝可梦创建实例: {trainer_pokemon.pokemon_species_id}, 等级: {trainer_pokemon.level}")

        return BattleTrainer(trainer=trainer, pokemon_list=pokemon_instances)

    def has_user_fought_trainer(self, user_id: str, trainer_id: int) -> bool:
        """检查用户是否已经与训练家战斗过"""
        return self.trainer_repo.has_user_fought_trainer(user_id, trainer_id)

    def record_trainer_encounter(self, user_id: str, trainer_id: int, battle_result: Optional[str] = None) -> int:
        """记录用户与训练家的遭遇"""
        encounter = TrainerEncounter(
            id=0,  # 这将由数据库自动生成
            user_id=user_id,
            trainer_id=trainer_id,
            encounter_time="",
            battle_result=battle_result
        )
        encounter_id = self.trainer_repo.create_trainer_encounter(encounter)
        return encounter_id

    def update_trainer_encounter_result(self, user_id: str, trainer_id: int, battle_result: str) -> None:
        """更新训练家遭遇结果"""
        encounter = self.trainer_repo.get_trainer_encounter_by_id(user_id, trainer_id)
        if encounter:
            self.trainer_repo.update_trainer_encounter(
                encounter.id,
                battle_result=battle_result
            )

    def get_random_trainer_at_location(self, location_id: int, user_id: str) -> Optional[Trainer]:
        """在特定位置随机获取一个训练家，允许战斗失败的用户再次挑战"""
        location_records = self.trainer_repo.get_trainers_at_location(location_id)

        # 过滤出用户未战胜过的训练家（包括未战斗过的）
        available_trainers = []
        for record in location_records:
            trainer = self.trainer_repo.get_trainer_by_id(record.trainer_id)
            if trainer:
                # 检查用户与该训练家的遭遇记录
                encounter = self.trainer_repo.get_trainer_encounter_by_id(user_id, trainer.id)
                # 只有当用户已经战胜过该训练家时，才不显示（防止玩家打完就没了）
                # 如果是未战斗过或者战斗失败（lose），仍然可以遇到
                if not encounter or encounter.battle_result != 'win':
                    # 根据遭遇率决定是否加入可选列表
                    if random.random() < record.encounter_rate:
                        available_trainers.append(trainer)

        if available_trainers:
            return random.choice(available_trainers)
        return None

    def calculate_trainer_battle_rewards(self, trainer: Trainer, last_pokemon_level: int) -> Dict[str, Any]:
        """计算训练家对战奖励"""
        # 金钱奖励 = 基础赏金 × 对方最后一只宝可梦等级
        money_reward = trainer.base_payout * last_pokemon_level

        # 经验值加成（击败训练家的宝可梦获得1.5倍经验）
        exp_multiplier = 1.5

        return {
            "money_reward": money_reward,
            "exp_multiplier": exp_multiplier
        }

    def handle_trainer_battle_win(self, user_id: str, trainer_id: int, money_reward: int) -> None:
        """处理训练家对战胜利逻辑"""
        # 更新遭遇记录
        self.update_trainer_encounter_result(user_id, trainer_id, "win")

        # 给用户增加金钱
        user = self.user_repo.get_user_by_id(user_id)
        if user:
            new_coins = user.coins + money_reward
            self.user_repo.update_user_coins(user_id, coins=new_coins)
