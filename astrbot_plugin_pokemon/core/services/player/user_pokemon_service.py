import random
from typing import Dict, Any, Optional

from astrbot.api import logger

from ...models.common_models import BaseResult
from ....infrastructure.repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractItemRepository, AbstractUserPokemonRepository,
    AbstractPokemonAbilityRepository, AbstractUserItemRepository, AbstractMoveRepository,
)

from ....utils.utils import get_today, userid_to_base32
from ....core.models.user_models import User, UserItemInfo
from ....core.models.pokemon_models import UserPokemonInfo, PokemonDetail, PokemonStats, WildPokemonInfo
from ....interface.response.answer_enum import AnswerEnum

class UserPokemonService:
    """封装与用户宝可梦相关的业务逻辑"""
    def __init__(
            self,
            user_repo: AbstractUserRepository,
            pokemon_repo: AbstractPokemonRepository,
            item_repo: AbstractItemRepository,
            user_pokemon_repo: AbstractUserPokemonRepository,
            pokemon_ability_repo: AbstractPokemonAbilityRepository,
            user_item_repo: AbstractUserItemRepository,
            move_repo: AbstractMoveRepository,
            config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.item_repo = item_repo
        self.user_pokemon_repo = user_pokemon_repo
        self.pokemon_ability_repo = pokemon_ability_repo
        self.user_item_repo = user_item_repo
        self.move_repo = move_repo
        self.config = config

    def _assign_random_ability(self, species_id: int) -> int:
        """
        为宝可梦随机分配一个非隐藏特性
        Args:
            species_id: 宝可梦种族ID
        Returns:
            int: 特性ID
        """
        # 获取该宝可梦的非隐藏特性
        relations = self.pokemon_ability_repo.get_abilities_by_pokemon_id(species_id)
        non_hidden_abilities = [rel for rel in relations if rel.get('is_hidden', 0) == 0 and rel.get('slot') in [1, 2]]

        if non_hidden_abilities:
            # 随机选择一个非隐藏特性
            selected = random.choice(non_hidden_abilities)
            return selected['ability_id']
        else:
            # 如果没有非隐藏特性，从所有特性中随机选择
            if relations:
                selected = random.choice(relations)
                return selected['ability_id']

        # 如果没有任何特性关联，返回0
        return 0

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
        # 随机分配一个非隐藏特性
        ability_id = self._assign_random_ability(new_pokemon.base_pokemon.id)

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
            ability_id=ability_id,
        )
        # 创建用户宝可梦记录，使用模板数据完善实例
        pokemon_new_id = self.user_pokemon_repo.create_user_pokemon(user_id, user_pokemon_info)

        # 记录到图鉴历史
        self.user_pokemon_repo.record_pokedex_capture(user_id, new_pokemon.base_pokemon.id)

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
                gender = pokemon["gender"],
                level = pokemon["level"],
                exp = pokemon["exp"],
                stats=pokemon["stats"],
                ivs = pokemon["ivs"],
                evs = pokemon["evs"],
                moves = pokemon["moves"],
                nature_id=pokemon["nature_id"],
                ability_id=pokemon["ability_id"],
                held_item_id=pokemon["held_item_id"],
                caught_time=pokemon["caught_time"],
                happiness=pokemon["happiness"],
                current_hp=pokemon["current_hp"],
                current_pp1=pokemon["current_pp1"],
                current_pp2=pokemon["current_pp2"],
                current_pp3=pokemon["current_pp3"],
                current_pp4=pokemon["current_pp4"],
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
                ability_id=pokemon.ability_id,
                caught_time=pokemon.caught_time,
                happiness=pokemon.happiness,
                current_hp=pokemon.current_hp,
                current_pp1=pokemon.current_pp1,
                current_pp2=pokemon.current_pp2,
                current_pp3=pokemon.current_pp3,
                current_pp4=pokemon.current_pp4,
                is_favorite=pokemon.is_favorite,
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
            # 如果传入的宝可梦信息中没有特性ID，则随机分配一个
            if pokemon_info.ability_id == 0:
                pokemon_info.ability_id = self._assign_random_ability(pokemon_info.species_id)

            pid = self.user_pokemon_repo.create_user_pokemon(user_id, pokemon_info)
            # 记录到图鉴历史
            self.user_pokemon_repo.record_pokedex_capture(user_id, pokemon_info.species_id)
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
            , nature_id=wild.nature_id, ability_id=wild.ability_id,
            held_item_id=wild.held_item_id
        )
        pid = self.user_pokemon_repo.create_user_pokemon(user_id, info)
        # 记录到图鉴历史
        self.user_pokemon_repo.record_pokedex_capture(user_id, wild.species_id)
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

    def update_pokemon_happiness(self, user_id: str, pokemon_id: int, happiness: int) -> BaseResult:
        """
        更新宝可梦友好度
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
            happiness: 友好度值
        Returns:
            BaseResult
        """
        try:
            self.user_pokemon_repo.update_user_pokemon_happiness(user_id, pokemon_id, happiness)
            return BaseResult(
                success=True,
                message="宝可梦友好度更新成功"
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"更新宝可梦友好度失败: {str(e)}"
            )

    def heal_pokemon_fully(self, user_id: str, pokemon_id: int) -> BaseResult:
        """
        完全治愈宝可梦
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            BaseResult
        """
        try:
            self.user_pokemon_repo.update_user_pokemon_full_heal(user_id, pokemon_id)
            return BaseResult(
                success=True,
                message="宝可梦已完全治愈"
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"治愈宝可梦失败: {str(e)}"
            )

    def update_user_pokemon_full_heal(self, user_id: str, pokemon_id: int) -> BaseResult:
        """
        完全治愈用户宝可梦
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            BaseResult
        """
        try:
            self.user_pokemon_repo.update_user_pokemon_full_heal(user_id, pokemon_id)
            return BaseResult(
                success=True,
                message="宝可梦已完全治愈"
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"治愈宝可梦失败: {str(e)}"
            )

    def set_pokemon_favorite(self, user_id: str, pokemon_id: int, favorite: bool) -> BaseResult:
        """
        设置/取消宝可梦的收藏状态
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
            favorite: True为收藏，False为取消收藏
        Returns:
            BaseResult
        """
        # 先检查宝可梦是否存在
        pokemon_info = self.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_info.success:
            return pokemon_info

        # 更新收藏状态
        is_favorite = 1 if favorite else 0
        try:
            self.user_pokemon_repo.update_user_pokemon_favorite(user_id, pokemon_id, is_favorite)
            action = "收藏" if favorite else "取消收藏"
            return BaseResult(
                success=True,
                message=f"成功{action}宝可梦：{pokemon_info.data.name}",
                data={
                    "pokemon_id": pokemon_id,
                    "pokemon_name": pokemon_info.data.name,
                    "is_favorite": is_favorite
                }
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"设置收藏状态失败: {str(e)}"
            )

    def get_user_favorite_pokemon(self, user_id: str) -> BaseResult[list[UserPokemonInfo]]:
        """
        获取用户收藏的宝可梦列表
        Args:
            user_id: 用户ID
        Returns:
            包含用户收藏的宝可梦信息的列表
        """
        user_pokemon_list = self.user_pokemon_repo.get_user_favorite_pokemon(user_id)

        if not user_pokemon_list:
            return BaseResult(
                success=True,
                message=AnswerEnum.USER_POKEMONS_NOT_FOUND.value,
            )

        # 格式化返回数据
        formatted_pokemon = []
        for pokemon in user_pokemon_list:
            formatted_pokemon.append(UserPokemonInfo(
                id = pokemon.id,
                species_id = pokemon.species_id,
                name = pokemon.name,
                gender = pokemon.gender,
                level = pokemon.level,
                exp = pokemon.exp,
                stats=pokemon.stats,
                ivs = pokemon.ivs,
                evs = pokemon.evs,
                moves = pokemon.moves,
                nature_id=pokemon.nature_id,
                ability_id=pokemon.ability_id,
                held_item_id=pokemon.held_item_id,
                caught_time=pokemon.caught_time,
                happiness=pokemon.happiness,
                current_hp=pokemon.current_hp,
                current_pp1=pokemon.current_pp1,
                current_pp2=pokemon.current_pp2,
                current_pp3=pokemon.current_pp3,
                current_pp4=pokemon.current_pp4,
                is_favorite=pokemon.is_favorite,
            ))

        return BaseResult(
            success=True,
            message=AnswerEnum.USER_POKEMON_ALL_POKEMON_SUCCESS.value,
            data=formatted_pokemon
        )

    def get_user_favorite_pokemon_paged(self, user_id: str, page: int = 1, page_size: int = 20) -> BaseResult[dict]:
        """
        分页获取用户收藏的宝可梦信息
        Args:
            user_id: 用户ID
            page: 页码 (从1开始)
            page_size: 每页数量
        Returns:
            包含分页数据和元信息的字典
        """
        user_pokemon_list = self.user_pokemon_repo.get_user_favorite_pokemon_paged(user_id, page, page_size)

        # 获取总数用于计算页数
        total_pokemon_res = self.get_user_favorite_pokemon(user_id)
        total_count = len(total_pokemon_res.data) if total_pokemon_res.success and total_pokemon_res.data else 0

        # 计算总页数
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

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
                ability_id=pokemon.ability_id,
                caught_time=pokemon.caught_time,
                happiness=pokemon.happiness,
                current_hp=pokemon.current_hp,
                current_pp1=pokemon.current_pp1,
                current_pp2=pokemon.current_pp2,
                current_pp3=pokemon.current_pp3,
                current_pp4=pokemon.current_pp4,
                is_favorite=pokemon.is_favorite,
            ))

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

    def set_pokemon_held_item(self, user_id: str, pokemon_id: int, item_id: int) -> BaseResult:
        """
        为宝可梦装备持有物
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
            item_id: 道具ID
        Returns:
            BaseResult
        """
        from ..battle.battle_config import battle_config
        # 1. 检查宝可梦是否存在
        pokemon_result = self.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_result.success:
            return pokemon_result

        pokemon_info = pokemon_result.data

        # 2. 检查用户是否拥有该道具且数量大于0
        item_result: UserItemInfo = self.user_item_repo.get_user_item_by_id(user_id, item_id)
        # 内测用户直接带
        if user_id not in ['PJFGIZ2LGF2EUWRLGE4W6YLZNRQU4WRX', 'OFRUC32BLJGCWTSLMFREURTYMZHVG2TX']:
            if not item_result or item_result.quantity <= 0 :
                return BaseResult(
                    success=False,
                    message="您没有持有该道具"
                )

        # 3. 检查道具是否属于允许的背包类别 (pocket_id为1, 2, 5, 7)
        # 从配置获取物品类别信息
        item_category_info = battle_config.get_item_category_info()
        # 创建category_id到pocket_id的映射
        category_to_pocket = {cat['id']: cat['pocket_id'] for cat in item_category_info}

        item_pocket_id = category_to_pocket.get(item_result.category_id)

        # 检查pocket_id是否为1, 2, 5或7
        if item_pocket_id not in [1, 2, 5, 7]:
            return BaseResult(
                success=False,
                message="该道具不能作为持有物装备，请使用'道具'、'回复道具'、'树果'或'战斗道具'类别的道具"
            )

        # 4. 更新宝可梦的持有物
        try:
            self.user_pokemon_repo.update_user_pokemon_held_item(user_id, pokemon_id, item_id)

            # 获取道具名称
            item_info = self.item_repo.get_item_by_id(item_id)
            item_name = item_info.get('name_zh', '未知道具') if item_info else '未知道具'

            return BaseResult(
                success=True,
                message=f"成功为宝可梦 {pokemon_info.name} 装备了持有物：{item_name}",
                data={
                    "pokemon_id": pokemon_id,
                    "pokemon_name": pokemon_info.name,
                    "item_id": item_id,
                    "item_name": item_name
                }
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"装备持有物失败: {str(e)}"
            )

    def remove_pokemon_held_item(self, user_id: str, pokemon_id: int) -> BaseResult:
        """
        移除宝可梦的持有物
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            BaseResult
        """
        # 1. 检查宝可梦是否存在
        pokemon_result = self.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_result.success:
            return pokemon_result

        pokemon_info = pokemon_result.data

        # 2. 检查是否已装备持有物
        if pokemon_info.held_item_id <= 0:
            return BaseResult(
                success=False,
                message=f"宝可梦 {pokemon_info.name} 目前没有装备持有物"
            )

        # 3. 获取原有道具信息
        old_item_info = self.item_repo.get_item_by_id(pokemon_info.held_item_id)
        old_item_name = old_item_info.get('name_zh', '未知道具') if old_item_info else '未知道具'

        # 4. 移除持有物 (设置为0)
        try:
            self.user_pokemon_repo.update_user_pokemon_held_item(user_id, pokemon_id, 0)

            return BaseResult(
                success=True,
                message=f"成功移除宝可梦 {pokemon_info.name} 的持有物：{old_item_name}",
                data={
                    "pokemon_id": pokemon_id,
                    "pokemon_name": pokemon_info.name,
                    "removed_item_id": pokemon_info.held_item_id,
                    "removed_item_name": old_item_name
                }
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"移除持有物失败: {str(e)}"
            )

    def update_pokemon_nickname(self, user_id: str, pokemon_id: int, nickname: str) -> BaseResult:
        """
        更新宝可梦昵称
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
            nickname: 新昵称
        Returns:
            BaseResult
        """
        # 1. 检查宝可梦是否存在
        pokemon_result = self.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_result.success:
            return pokemon_result

        # 2. 检查昵称是否符合要求
        if not nickname or len(nickname.strip()) == 0:
            return BaseResult(
                success=False,
                message="昵称不能为空"
            )

        # 3. 检查昵称长度
        if len(nickname) > 8:  # 限制昵称长度为8个字
            return BaseResult(
                success=False,
                message="昵称长度不能超过8个字"
            )

        pokemon_info = pokemon_result.data

        # 4. 更新昵称
        try:
            self.user_pokemon_repo.update_user_pokemon_nickname(user_id, pokemon_id, nickname)

            return BaseResult(
                success=True,
                message=f"成功将宝可梦的昵称更新为：{nickname}",
                data={
                    "pokemon_id": pokemon_id,
                    "original_name": pokemon_info.name,
                    "new_nickname": nickname
                }
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"更新昵称失败: {str(e)}"
            )

    def get_user_pokemon_info_str_by_id(self, user_id: str, pokemon_id: int) -> BaseResult:
        """
        获取用户宝可梦信息字符串
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            BaseResult
        """
        # 1. 检查宝可梦是否存在
        pokemon_result = self.get_user_pokemon_by_id(user_id, pokemon_id)
        if not pokemon_result.success:
            return pokemon_result

        pokemon_info = pokemon_result.data
        nickname = pokemon_info.name
        species_name = self.pokemon_repo.get_pokemon_by_id(pokemon_info.species_id).name_zh
        can_learn_moves = self.move_repo.get_pokemon_moves_by_species_id(pokemon_info.species_id)
        can_learn_move_ids = []
        for move in can_learn_moves:
            logger.debug(f"检查招式 {move.get('name_zh')} (ID: {move.get('move_id')}) 是否可通过自然学习 (move_method_id: {move.get('move_method_id')})")
            if move.get('move_method_id') == 1:
                can_learn_move_ids.append(move.get('move_id'))
        can_learn_move_names = []
        for move_id in can_learn_move_ids:
            logger.debug(f"检查招式 {move_id} 是否可通过自然学习")
            move_data = self.move_repo.get_move_by_id(move_id)
            logger.debug(f"招式 {move_id} 详细信息: {move_data}")
            if move_data:
                can_learn_move_names.append(move_data.get('name_zh', '未知招式'))
            else:
                can_learn_move_names.append('未知招式')
        stats = pokemon_info.stats
        ivs = pokemon_info.ivs
        evs = pokemon_info.evs
        # 从PokemonMoves对象中提取实际的技能ID
        learned_move_ids = [
            pokemon_info.moves.move1_id,
            pokemon_info.moves.move2_id,
            pokemon_info.moves.move3_id,
            pokemon_info.moves.move4_id
        ]
        # 过滤掉无效的技能ID（0表示未学习）
        valid_move_ids = [move_id for move_id in learned_move_ids if move_id and move_id > 0]
        learned_move_names = [self.move_repo.get_move_by_id(move_id).get('name_zh', '未知招式') for move_id in valid_move_ids]

        # 获取可通过升级学习的招式 (获取详细信息，包括级别)
        all_learnable_moves = self.move_repo.get_pokemon_moves_by_species_id(pokemon_info.species_id)
        level_up_move_names = []
        for move_data in all_learnable_moves:
            # 检查是否为升级招式 (move_method_id == 1) 和是否超过当前等级
            if move_data.get('move_method_id') == 1 and move_data.get('level', 0) > pokemon_info.level:
                move_id = move_data.get('move_id')
                # 检查是否已经学会这个招式
                if move_id and move_id not in valid_move_ids:
                    move_info = self.move_repo.get_move_by_id(move_id)
                    if move_info:
                        level_up_move_names.append(f"{move_info['name_zh']} (等级 {move_data['level']})")

        # 获取持有物名称
        held_item_name = "无"
        if pokemon_info.held_item_id and pokemon_info.held_item_id > 0:
            item_info = self.item_repo.get_item_by_id(pokemon_info.held_item_id)
            if item_info:
                held_item_name = item_info.get('name', '未知道具')

        info_str = (
            f"宝可梦昵称: {nickname}\n 宝可梦物种名称: {species_name}\n 等级: {pokemon_info.level}\n 基础统计值: {stats}\n IV值: {ivs}\n EV值: {evs}\n"
            f"当前已学会招式: {learned_move_names}\n 可通过升级学习的招式: {level_up_move_names}\n"
            f"持有物: {held_item_name}\n"
        )

        return BaseResult(
            success=True,
            message="成功获取宝可梦信息",
            data={
                "info_str": info_str
            }
        )