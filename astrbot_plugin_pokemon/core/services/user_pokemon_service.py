import random
from typing import Dict, Any

from .pokemon_service import PokemonService
from ..models.common_models import BaseResult
from ...infrastructure.repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractItemRepository,
)

from ...utils.utils import get_today, userid_to_base32
from ...core.models.user_models import User
from ...core.models.pokemon_models import UserPokemonInfo, PokemonDetail, PokemonStats
from ...interface.response.answer_enum import AnswerEnum

class UserPokemonService:
    """封装与用户宝可梦相关的业务逻辑"""
    def __init__(
            self,
            user_repo: AbstractUserRepository,
            pokemon_repo: AbstractPokemonRepository,
            item_repo: AbstractItemRepository,
            pokemon_service: PokemonService,
            config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.item_repo = item_repo
        self.pokemon_service = pokemon_service
        self.config = config

    def init_select_pokemon(self, user_id: str, pokemon_id: int) -> BaseResult:
        """
        初始化选择宝可梦。
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            一个包含成功状态和消息的BaseResult对象。
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_NOT_REGISTERED.value
            )
        if user.init_selected:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_ALREADY_INITIALIZED_POKEMON.value
            )

        # 检查宝可梦是否存在
        pokemon_template = self.pokemon_repo.get_pokemon_by_id(pokemon_id)
        if not pokemon_template:
            return BaseResult(
                success=False,
                message=AnswerEnum.POKEMON_NOT_FOUND.value
            )

        new_pokemon = self.pokemon_service.create_single_pokemon(pokemon_id, 1, 1)

        if not new_pokemon["success"]:
            return BaseResult(
                success=False,
                message=new_pokemon.message,
            )
        new_pokemon_data: PokemonDetail = new_pokemon.data
        user_pokemon_info = UserPokemonInfo(
            id = 0,
            species_id = new_pokemon_data["base_pokemon"].id,
            name = new_pokemon_data["base_pokemon"].name_zh,
            gender = new_pokemon_data["gender"],
            level = new_pokemon_data["level"],
            exp = new_pokemon_data["exp"],
            stats = new_pokemon_data["stats"],
            ivs = new_pokemon_data["ivs"],
            evs = new_pokemon_data["evs"],
            moves = new_pokemon_data["moves"],
        )

        # 创建用户宝可梦记录，使用模板数据完善实例
        self.user_repo.create_user_pokemon(user_id, user_pokemon_info,)

        # 更新用户的初始选择状态
        self.user_repo.update_init_select(user_id, pokemon_id)

        return BaseResult(
            success=True,
            message=AnswerEnum.POKEMON_INIT_SELECT_SUCCESS.value,
            data={
                "pokemon_name": pokemon_template.name_zh
            }
        )

    def get_user_specific_pokemon(self, user_id: str, pokemon_id: int) -> BaseResult[UserPokemonInfo]:
        """
        获取用户特定宝可梦的详细信息
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID（数字ID）
        Returns:
            包含宝可梦详细信息的字典
        """
        # 获取特定宝可梦的信息
        pokemon_data: UserPokemonInfo = self.user_repo.get_user_pokemon_by_id(user_id, int(pokemon_id))
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
        user_pokemon_list = self.user_repo.get_user_pokemon(user_id)

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
            ))

        return BaseResult(
            success=True,
            message=AnswerEnum.USER_POKEMON_ALL_POKEMON_SUCCESS.value,
            data=formatted_pokemon
        )
