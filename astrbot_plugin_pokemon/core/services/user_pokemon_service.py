import random
from typing import Dict, Any, Optional

from astrbot.api import logger

from ..models.common_models import BaseResult
from ...infrastructure.repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractItemRepository, AbstractUserPokemonRepository,
)

from ...utils.utils import get_today, userid_to_base32
from ...core.models.user_models import User
from ...core.models.pokemon_models import UserPokemonInfo, PokemonDetail, PokemonStats, WildPokemonInfo
from ...interface.response.answer_enum import AnswerEnum

class UserPokemonService:
    """封装与用户宝可梦相关的业务逻辑"""
    def __init__(
            self,
            user_repo: AbstractUserRepository,
            pokemon_repo: AbstractPokemonRepository,
            item_repo: AbstractItemRepository,
            user_pokemon_repo: AbstractUserPokemonRepository,
            config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.item_repo = item_repo
        self.user_pokemon_repo = user_pokemon_repo
        self.config = config

    def init_select_pokemon(self, user_id: str, new_pokemon: PokemonDetail) -> BaseResult:
        """
        初始化选择宝可梦。
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
            new_pokemon: 新创建的宝可梦详情
        Returns:
            一个包含成功状态和消息的BaseResult对象。
        """
        user_pokemon_info = UserPokemonInfo(
            id = 0,
            species_id = new_pokemon.base_pokemon.id,
            name = new_pokemon.base_pokemon.name_zh,
            gender = new_pokemon.gender,
            level = new_pokemon.level,
            exp = new_pokemon.exp,
            stats = new_pokemon.stats,
            ivs = new_pokemon.ivs,
            evs = new_pokemon.evs,
            moves = new_pokemon.moves,
            nature_id = new_pokemon.nature_id,
        )
        # 创建用户宝可梦记录，使用模板数据完善实例
        pokemon_new_id = self.user_pokemon_repo.create_user_pokemon(user_id, user_pokemon_info)

        # 更新用户的初始选择状态
        pokemon_id = new_pokemon.base_pokemon.id
        self.user_repo.update_init_select(user_id, pokemon_id)

        return BaseResult(
            success=True,
            message=AnswerEnum.POKEMON_INIT_SELECT_SUCCESS.value,
            data={
                "pokemon_name": new_pokemon.base_pokemon.name_zh,
                "pokemon_id": pokemon_new_id,
            }
        )

    def get_user_pokemon_by_id(self, user_id: str, pokemon_id: int) -> BaseResult[UserPokemonInfo]:
        """
        获取用户特定宝可梦的详细信息
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID（数字ID）
        Returns:
            包含宝可梦详细信息的字典
        """
        # 获取特定宝可梦的信息
        pokemon_data: UserPokemonInfo = self.user_pokemon_repo.get_user_pokemon_by_id(user_id, int(pokemon_id))
        if not pokemon_data:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_POKEMON_NOT_FOUND.value
            )


        return BaseResult(
            success=True,
            message="",
            data=pokemon_data
        )

    def get_user_all_pokemon(self, user_id: str) -> BaseResult[list[UserPokemonInfo]]:
        """
        获取用户的所有宝可梦信息
        Args:
            user_id: 用户ID
        Returns:
            包含用户宝可梦信息的字典
        """
        user_pokemon_list = self.user_pokemon_repo.get_user_pokemon(user_id)

        if not user_pokemon_list:
            return BaseResult(
                success=True,
                message=AnswerEnum.USER_POKEMONS_NOT_FOUND.value,
            )

        # 格式化返回数据
        formatted_pokemon = []
        for pokemon in user_pokemon_list:
            formatted_pokemon.append(UserPokemonInfo(
                id = pokemon["id"],
                species_id = pokemon["species_id"],
                name = pokemon["name"],
                level = pokemon["level"],
                exp = pokemon["exp"],
                gender = pokemon["gender"],
                stats=pokemon["stats"],
                ivs = pokemon["ivs"],
                evs = pokemon["evs"],
                moves = pokemon["moves"],
                nature_id=pokemon["nature_id"],
            ))

        return BaseResult(
            success=True,
            message=AnswerEnum.USER_POKEMON_ALL_POKEMON_SUCCESS.value,
            data=formatted_pokemon
        )

    def get_user_pokemon_paged(self, user_id: str, page: int = 1, page_size: int = 20) -> BaseResult[dict]:
        """
        分页获取用户宝可梦信息
        Args:
            user_id: 用户ID
            page: 页码 (从1开始)
            page_size: 每页数量
        Returns:
            包含分页数据和元信息的字典
        """
        offset = (page - 1) * page_size
        user_pokemon_list = self.user_pokemon_repo.get_user_pokemon_paged(user_id, page_size, offset)

        # 获取总数用于计算页数
        total_count = self.user_pokemon_repo.get_user_pokemon_count(user_id)

        # 格式化返回数据
        formatted_pokemon = []
        for pokemon in user_pokemon_list:
            formatted_pokemon.append(UserPokemonInfo(
                id = pokemon.id,
                species_id = pokemon.species_id,
                name = pokemon.name,
                level = pokemon.level,
                exp = pokemon.exp,
                gender = pokemon.gender,
                stats=pokemon.stats,
                ivs = pokemon.ivs,
                evs = pokemon.evs,
                moves = pokemon.moves,
                nature_id=pokemon.nature_id,
                caught_time=pokemon.caught_time
            ))

        # 计算总页数
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

        return BaseResult(
            success=True,
            message=AnswerEnum.USER_POKEMON_ALL_POKEMON_SUCCESS.value if formatted_pokemon else AnswerEnum.USER_POKEMONS_NOT_FOUND.value,
            data={
                "pokemon_list": formatted_pokemon,
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages
            }
        )

    def update_user_pokemon_moves(self, user_id: str, pokemon_id: int, moves) -> BaseResult:
        """
        更新用户宝可梦的技能
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
            moves: 技能对象
        Returns:
            BaseResult
        """
        try:
            # 将PokemonMoves对象分解为单独字段进行更新
            self.user_pokemon_repo._update_user_pokemon_fields(
                user_id,
                pokemon_id,
                move1_id=moves.move1_id,
                move2_id=moves.move2_id,
                move3_id=moves.move3_id,
                move4_id=moves.move4_id
            )
            return BaseResult(
                success=True,
                message="技能更新成功"
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"更新技能失败: {str(e)}"
            )

    def create_user_pokemon(self, user_id: str, pokemon_info: UserPokemonInfo) -> BaseResult:
        """
        创建用户宝可梦记录
        Args:
            user_id: 用户ID
            pokemon_info: 宝可梦信息
        Returns:
            BaseResult
        """
        try:
            pid = self.user_pokemon_repo.create_user_pokemon(user_id, pokemon_info)
            return BaseResult(
                success=True,
                message=AnswerEnum.USER_POKEMON_CREATED.value,
                data = pid
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"创建用户宝可梦失败: {str(e)}"
            )

    def _create_and_save_caught_pokemon(self, user_id: str, wild: WildPokemonInfo) -> Any | None:
        """创建并保存捕捉到的宝可梦 (封装Repo操作)"""
        info = UserPokemonInfo(
            id=0, species_id=wild.species_id, name=wild.name,
            level=wild.level, exp=wild.exp, gender=wild.gender,
            stats=wild.stats, ivs=wild.ivs, evs=wild.evs, moves=wild.moves
            , nature_id=wild.nature_id
        )
        pid = self.user_pokemon_repo.create_user_pokemon(user_id, info)
        return self.user_pokemon_repo.get_user_pokemon_by_id(user_id, pid)

    def get_user_pokedex_ids(self, user_id: str) -> BaseResult[dict]:
        """
        获取用户宝可梦图鉴IDs
        Args:
            user_id: 用户ID
        Returns:
            包含用户宝可梦图鉴IDs的字典
        """
        user_progress = self.user_pokemon_repo.get_user_pokedex_ids(user_id)
        if not user_progress:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_POKEMON_NOT_FOUND.value
            )
        return BaseResult(
            success=True,
            message=AnswerEnum.USER_POKEMON_POKEDEX_IDS_SUCCESS.value,
            data=user_progress
        )

    def get_user_encountered_wild_pokemon(self, user_id: str) -> Optional[WildPokemonInfo]:
        """
        获取用户当前遇到的野生宝可梦
        Args:
            user_id (str): 用户ID
        Returns:
            Optional[WildPokemonInfo]: 野生宝可梦的详细信息，如果不存在则返回None
        """
        encountered_wild_pokemon = self.user_pokemon_repo.get_user_encountered_wild_pokemon(user_id)
        if not encountered_wild_pokemon:
            return None
        wild_pokemon_id = encountered_wild_pokemon.wild_pokemon_id
        wild_pokemon_info = self.pokemon_repo.get_wild_pokemon_by_id(wild_pokemon_id)
        return wild_pokemon_info

    def get_user_current_trainer_encounter(self, user_id: str) -> Optional[int]:
        """
        获取用户当前遭遇的训练家ID
        Args:
            user_id (str): 用户ID
        Returns:
            Optional[int]: 训练家ID，如果不存在则返回None
        """
        return self.user_pokemon_repo.get_user_current_trainer_encounter(user_id)

    def set_user_current_trainer_encounter(self, user_id: str, trainer_id: int) -> None:
        """
        设置用户当前遭遇的训练家
        Args:
            user_id (str): 用户ID
            trainer_id (int): 训练家ID
        """
        self.user_pokemon_repo.set_user_current_trainer_encounter(user_id, trainer_id)

    def clear_user_current_trainer_encounter(self, user_id: str) -> None:
        """
        清除用户当前遭遇的训练家
        Args:
            user_id (str): 用户ID
        """
        self.user_pokemon_repo.clear_user_current_trainer_encounter(user_id)
