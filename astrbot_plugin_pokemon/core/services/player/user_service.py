import random
from typing import Dict, Any, List

from astrbot.api import logger
from ...models.common_models import BaseResult
from ....infrastructure.repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository, AbstractItemRepository, AbstractUserItemRepository,
    AbstractUserPokemonRepository, AbstractTeamRepository, AbstractBattleRepository,
)

from ....utils.utils import get_today, userid_to_base32
from ....core.models.user_models import User
from ....core.models.pokemon_models import UserPokemonInfo, PokemonDetail, WildPokemonEncounterLog
from ....interface.response.answer_enum import AnswerEnum

class UserService:
    """封装与用户相关的业务逻辑"""
    def __init__(
            self,
            user_repo: AbstractUserRepository,
            pokemon_repo: AbstractPokemonRepository,
            item_repo: AbstractItemRepository,
            user_item_repo: AbstractUserItemRepository,
            user_pokemon_repo: AbstractUserPokemonRepository,
            team_repo: AbstractTeamRepository,
            battle_repo: AbstractBattleRepository,
            exp_service,
            config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.item_repo = item_repo
        self.user_item_repo = user_item_repo
        self.user_pokemon_repo = user_pokemon_repo
        self.team_repo = team_repo
        self.battle_repo = battle_repo
        self.exp_service = exp_service
        self.config = config

    def register(self, user_id: str, nickname: str) -> BaseResult:
        """
        注册新用户。
        Args:
            user_id: 用户ID
            nickname: 用户昵称
        Returns:
            一个包含成功状态、消息和用户数据的BaseResult对象。
        """
        origin_id = user_id
        user_id = userid_to_base32(user_id)
        if self.user_repo.get_user_by_id(user_id):
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_ALREADY_REGISTERED.value
            )

        initial_coins = self.config.get("user", {}).get("initial_coins", 200)
        new_user = User(
            user_id = user_id,
            nickname = nickname,
            coins = initial_coins,
            origin_id = origin_id
        )
        self.user_repo.add_pokemon_user(new_user)

        return BaseResult(
            success=True,
            message=f"注册成功！欢迎 {nickname} 🎉 你获得了 {initial_coins} 金币作为起始资金。\n\n请从妙蛙种子1、小火龙4、杰尼龟7中选择作为初始宝可梦。\n\n输入 /初始选择 <宝可梦ID> 来选择。",
            data={
                "user_id": user_id,
                "nickname": nickname,
                "coins": initial_coins,
                "origin_id": origin_id
            }
        )

    def checkin(self, user_id: str) -> BaseResult:
        """
        用户签到
        Args:
            user_id: 用户ID
        Returns:
            包含签到结果的字典
        """
        # 获取今天的日期
        today = get_today().strftime("%Y-%m-%d")

        # 检查用户今天是否已经签到
        if self.user_repo.has_user_checked_in_today(user_id, today):
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_ALREADY_CHECKED_IN.value,
            )

        # 检查用户是否存在
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_NOT_REGISTERED.value,
            )

        # 生成随机金币奖励（100-300之间）
        gold_reward = random.randint(100, 300)

        # 道具奖励：普通精灵球（ID=1），数量=1
        item_reward_id = 4
        item_quantity = 1

        # 更新用户金币
        new_coins = user.coins + gold_reward
        self.user_repo.update_user_coins(user_id, new_coins)

        # 为用户添加道具
        self.user_item_repo.add_user_item(user_id, item_reward_id, item_quantity)

        # 记录签到信息
        self.user_repo.add_user_checkin(user_id, today, gold_reward, item_reward_id, item_quantity)

        # 获取道具名称
        item_name = self.item_repo.get_item_name(item_reward_id)

        return BaseResult(
            success=True,
            message=AnswerEnum.USER_CHECKIN_SUCCESS.value,
            data={
                "gold_reward": gold_reward,
                "item_reward": item_name,
                "quantity": item_quantity,
                "new_coins": new_coins,
            }
        )

    def check_user_registered(self, user_id: str) -> BaseResult[User]:
        """
        检查用户是否已注册。
        Args:
            user_id: 用户ID
        Returns:
            如果用户已注册则返回{"success": True, "message": AnswerEnum.USER_ALREADY_REGISTERED.value, "data": user}，
            否则返回{"success": False, "message": AnswerEnum.USER_NOT_REGISTERED.value}。
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_NOT_REGISTERED.value
            )
        return BaseResult(
            success=True,
            message=AnswerEnum.USER_ALREADY_REGISTERED.value,
            data=user
        )

    def get_user_by_id(self, user_id: str) -> BaseResult[User]:
        """
        根据用户ID获取用户信息。
        Args:
            user_id: 用户ID
        Returns:
            如果用户存在则返回{"success": True, "message": AnswerEnum.USER_ALREADY_REGISTERED.value, "data": user}，
            否则返回{"success": False, "message": AnswerEnum.USER_NOT_REGISTERED.value}。
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_NOT_REGISTERED.value
            )
        return BaseResult(
            success=True,
            message=AnswerEnum.USER_ALREADY_REGISTERED.value,
            data=user
        )

    def update_user_last_adventure_time(self, user_id: str, last_adventure_time: float) -> BaseResult:
        """
        更新用户上次冒险时间。
        Args:
            user_id: 用户ID
            last_adventure_time: 上次冒险时间
        Returns:
            如果更新成功则返回{"success": True, "message": AnswerEnum.USER_ADVENTURE_TIME_UPDATED.value}，
            否则返回{"success": False, "message": AnswerEnum.USER_NOT_REGISTERED.value}。
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_NOT_REGISTERED.value
            )
        self.user_repo.update_user_last_adventure_time(user_id, last_adventure_time)
        return BaseResult(
            success=True,
            message=AnswerEnum.USER_ADVENTURE_TIME_UPDATED.value
        )

    def add_user_item(self, user_id: str, item_id: int, quantity: int) -> BaseResult:
        """
        为用户添加道具。
        Args:
            user_id: 用户ID
            item_id: 道具ID
            quantity: 道具数量
        Returns:
            如果添加成功则返回{"success": True, "message": AnswerEnum.USER_ITEM_ADDED.value}，
            否则返回{"success": False, "message": AnswerEnum.USER_NOT_REGISTERED.value}。
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return BaseResult(
                success=False,
                message=AnswerEnum.USER_NOT_REGISTERED.value
            )
        self.user_item_repo.add_user_item(user_id, item_id, quantity)
        return BaseResult(
            success=True,
            message=AnswerEnum.USER_ITEM_ADDED.value
        )

    def _update_encounter_log(self, user_id: str, wild_id: int, captured: bool = False, deleted: bool = False):
        """更新遭遇日志 (封装Repo操作)"""
        try:
            logs = self.user_pokemon_repo.get_user_encounters(user_id, limit=5)
            # 找到最近一条匹配且未处理的记录
            target_log = next((l for l in logs if l.wild_pokemon_id == wild_id and l.is_captured == 0), None)

            if target_log:
                self.user_pokemon_repo.update_encounter_log(
                    log_id=target_log.id,
                    is_captured=1 if captured else 0,
                    isdel=1 if deleted else 0
                )
        except Exception as e:
            # 日志更新失败不应阻断主流程，打印错误即可
            logger.error(f"Error updating encounter log: {e}")

    def update_encounter_log(self, log_id: int, is_captured: int, isdel: int) -> BaseResult:
        """
        更新遭遇记录。
        Args:
            log_id: 遭遇记录ID
            is_captured: 是否被捕获
            isdel: 是否删除
        Returns:
            如果更新成功则返回{"success": True, "message": AnswerEnum.USER_ENCOUNTERS_UPDATED.value}，
            否则返回{"success": False, "message": AnswerEnum.USER_NOT_REGISTERED.value}。
        """
        self.user_pokemon_repo.update_encounter_log(log_id, is_captured, isdel)
        return BaseResult(
            success=True,
            message=AnswerEnum.USER_ENCOUNTERS_UPDATED.value
        )

    def get_user_profile(self, user_id: str) -> BaseResult[Dict[str, Any]]:
        """获取用户个人资料，包括等级、经验、金币等信息"""
        user_result = self.check_user_registered(user_id)
        if not user_result.success:
            return user_result

        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return BaseResult(success=False, message=AnswerEnum.USER_NOT_EXISTS.value)

        # 计算下一级所需经验
        if self.exp_service:
            required_exp_for_next = self.exp_service.get_required_exp_for_level(user.level + 1)
            exp_needed_for_next = required_exp_for_next - user.exp if user.level < 100 else 0
        else:
            exp_needed_for_next = 0

        profile_data = {
            "user_id": user.user_id,
            "nickname": user.nickname,
            "level": user.level,
            "exp": user.exp,
            "exp_needed_for_next": exp_needed_for_next,
            "coins": user.coins,
            "created_at": user.created_at
        }

        return BaseResult(
            success=True,
            message="用户资料获取成功",
            data=profile_data
        )

    def get_all_users(self) -> BaseResult:
        """获取所有用户信息"""
        try:
            users = self.user_repo.get_all_users()
            return BaseResult(
                success=True,
                message="获取所有用户成功",
                data=users
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"获取用户列表失败: {str(e)}",
                data=[]
            )

    def get_user_detailed_info(self, user_id: str) -> BaseResult:
        """获取用户的详细信息，包括基本信息、宝可梦、道具、队伍和战斗记录"""
        try:
            # 获取用户基本信息
            user_basic_info = self.get_user_profile(user_id)
            if not user_basic_info.success:
                return user_basic_info

            # 获取用户宝可梦 - 安全处理避免函数调用错误
            try:
                user_pokemon_result = self.user_pokemon_repo.get_user_pokemon(user_id)
                # 确保user_pokemon_result是列表而不是函数
                if user_pokemon_result and callable(user_pokemon_result):
                    user_pokemon = []
                else:
                    # 如果结果是列表，确保每个元素都是原始数据
                    if isinstance(user_pokemon_result, list):
                        user_pokemon = user_pokemon_result
                    else:
                        user_pokemon = user_pokemon_result if user_pokemon_result is not None else []
            except Exception as pokemon_error:
                logger.error(f"获取用户宝可梦时出错: {pokemon_error}")
                user_pokemon = []

            # 获取用户道具 - 最安全的处理方式，确保只返回纯净的列表数据
            try:
                def convert_items_to_dict(items_list):
                    """将items列表转换为字典列表，确保数据纯净"""
                    result = []
                    if items_list:
                        for item in items_list:
                            item_info = {
                                "item_id": getattr(item, 'item_id', None),
                                "quantity": getattr(item, 'quantity', 0),
                                "name_zh": getattr(item, 'name_zh', ''),
                                "category_id": getattr(item, 'category_id', 0),
                                "description": getattr(item, 'description', ''),
                            }
                            result.append(item_info)
                    return result

                user_items_result = self.user_item_repo.get_user_items(user_id)
                if user_items_result:
                    # 检查是否是UserItems对象，它应该有items属性
                    if hasattr(user_items_result, 'items'):
                        original_items = getattr(user_items_result, 'items', [])
                        # 确保original_items不是方法
                        if original_items and callable(original_items):
                            user_items = []
                        else:
                            user_items = convert_items_to_dict(original_items)
                    else:
                        # user_items_result本身可能已经是items列表
                        if isinstance(user_items_result, list):
                            user_items = convert_items_to_dict(user_items_result)
                        else:
                            user_items = []
                else:
                    user_items = []
            except Exception as item_error:
                logger.error(f"获取用户道具时出错: {item_error}")
                user_items = []

            # 获取用户队伍 - 安全处理避免函数调用错误
            try:
                user_team_result = self.team_repo.get_user_team(user_id)
                if user_team_result:
                    # 检查是否是UserTeam对象，它应该有team_pokemon_ids属性
                    if hasattr(user_team_result, 'team_pokemon_ids'):
                        team_attr = getattr(user_team_result, 'team_pokemon_ids', [])
                        # 确保team_attr不是函数
                        if team_attr and callable(team_attr):
                            user_team = []
                        else:
                            user_team = team_attr if team_attr is not None else []
                    else:
                        # user_team_result本身可能已经是队伍列表
                        if isinstance(user_team_result, list):
                            user_team = user_team_result
                        else:
                            user_team = []
                else:
                    user_team = []
            except Exception as team_error:
                logger.error(f"获取用户队伍时出错: {team_error}")
                user_team = []

            # 获取战斗记录 - 安全处理避免函数调用错误
            try:
                battle_logs_result = self.battle_repo.get_user_battle_logs(user_id, limit=10)
                # 确保battle_logs_result是列表而不是函数
                if battle_logs_result and callable(battle_logs_result):
                    battle_logs = []
                else:
                    # 如果结果是列表，确保它被正确赋值
                    if isinstance(battle_logs_result, list):
                        battle_logs = battle_logs_result
                    else:
                        battle_logs = battle_logs_result if battle_logs_result is not None else []
            except Exception as battle_error:
                logger.error(f"获取战斗记录时出错: {battle_error}")
                battle_logs = []

            # 获取用户遭遇记录（可选，作为补充信息）- 安全处理避免函数调用错误
            try:
                encounter_logs_result = self.user_pokemon_repo.get_user_encounters(user_id, limit=10)
                # 确保encounter_logs_result是列表而不是函数
                if encounter_logs_result and callable(encounter_logs_result):
                    encounter_logs = []
                else:
                    # 如果结果是列表，确保它被正确赋值
                    if isinstance(encounter_logs_result, list):
                        encounter_logs = encounter_logs_result
                    else:
                        encounter_logs = encounter_logs_result if encounter_logs_result is not None else []
            except Exception as encounter_error:
                logger.error(f"获取用户遭遇记录时出错: {encounter_error}")
                encounter_logs = []

            # 构建详细信息字典，确保所有值都是原始数据类型，而不是可能包含方法的对象
            detailed_info = {
                "basic_info": user_basic_info.data,
                "pokemon": user_pokemon if user_pokemon is not None else [],
                "user_items": user_items if user_items is not None else [],
                "team": user_team if user_team is not None else [],
                "battle_logs": battle_logs if battle_logs is not None else [],
                "encounters": encounter_logs if encounter_logs is not None else []  # 遭遇记录作为补充信息
            }

            return BaseResult(
                success=True,
                message="获取用户详细信息成功",
                data=detailed_info
            )
        except Exception as e:
            return BaseResult(
                success=False,
                message=f"获取用户详细信息失败: {str(e)}",
                data=None
            )
