import random
from typing import Dict, Any

from .pokemon_service import PokemonService
from ..repositories.abstract_repository import (
    AbstractUserRepository, AbstractPokemonRepository,
)

from ..utils import get_now, get_today, userid_to_base32
from ..domain.user_models import User
from ..domain.pokemon_models import UserPokemonInfo, PokemonDetail
from ..answer.answer_enum import AnswerEnum

class UserService:
    """封装与用户相关的业务逻辑"""
    def __init__(
            self,
            user_repo: AbstractUserRepository,
            pokemon_repo: AbstractPokemonRepository,
            pokemon_service: PokemonService,
            config: Dict[str, Any]
    ):
        self.user_repo = user_repo
        self.pokemon_repo = pokemon_repo
        self.pokemon_service = pokemon_service
        self.config = config

    def register(self, user_id: str, nickname: str) -> Dict[str, Any]:
        """
        注册新用户。
        Args:
            user_id: 用户ID
            nickname: 用户昵称
        Returns:
            一个包含成功状态和消息的字典。
        """
        origin_id = user_id
        user_id = userid_to_base32(user_id)
        if self.user_repo.check_exists(user_id):
            return {"success": False, "message": AnswerEnum.USER_ALREADY_REGISTERED.value}

        initial_coins = self.config.get("user", {}).get("initial_coins", 200)
        new_user = User(
            user_id = user_id,
            nickname = nickname,
            coins = initial_coins,
            origin_id = origin_id
        )
        self.user_repo.create_user(new_user)

        return {
            "success": True,
            "message": f"注册成功！欢迎 {nickname} 🎉 你获得了 {initial_coins} 金币作为起始资金。\n\n请从妙蛙种子1、小火龙4、杰尼龟7中选择作为初始宝可梦。\n\n输入 /初始选择 <宝可梦ID> 来选择。"
        }

    def checkin(self, user_id: str) -> Dict[str, Any]:
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
            return {
                "success": False,
                "message": AnswerEnum.USER_ALREADY_CHECKED_IN.value,
            }

        # 检查用户是否存在
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "message": AnswerEnum.USER_NOT_REGISTERED.value,
            }

        # 生成随机金币奖励（100-300之间）
        gold_reward = random.randint(100, 300)

        # 道具奖励：普通精灵球（ID=1），数量=1
        item_reward_id = 4
        item_quantity = 1

        # 更新用户金币
        new_coins = user.coins + gold_reward
        self.user_repo.update_user_coins(user_id, new_coins)

        # 为用户添加道具
        self.user_repo.add_user_item(user_id, item_reward_id, item_quantity)

        # 记录签到信息
        self.user_repo.add_user_checkin(user_id, today, gold_reward, item_reward_id, item_quantity)

        return {
            "success": True,
            "message": f"✅ 签到成功！\n获得了 {gold_reward} 金币 💰\n获得了 普通精灵球 x{item_quantity} 🎒\n当前金币总数：{new_coins}",
            "gold_reward": gold_reward,
            "item_reward": {
                "id": item_reward_id,
                "quantity": item_quantity
            }
        }

    def init_select_pokemon(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        初始化选择宝可梦。
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID
        Returns:
            一个包含成功状态和消息的字典。
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return {"success": False, "message": AnswerEnum.USER_NOT_REGISTERED.value}
        if user.init_selected:
            return {"success": False, "message": AnswerEnum.USER_ALREADY_INITIALIZED_POKEMON.value}

        # 检查宝可梦是否存在
        pokemon_template = self.pokemon_repo.get_pokemon_by_id(pokemon_id)
        if not pokemon_template:
            return {"success": False, "message": AnswerEnum.POKEMON_NOT_FOUND.value}

        new_pokemon = self.pokemon_service.create_single_pokemon(pokemon_id, 1, 1)

        if not new_pokemon["success"]:
            return {
                "success": False,
                "message": new_pokemon["message"],
            }
        new_pokemon_data: PokemonDetail = new_pokemon["data"]
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

        return {
            "success": True,
            "message": f"成功将 {pokemon_template.name_zh} 初始选择为宝可梦！\n\n它已根据种族模板完善了个体值、努力值等特性。\n\n您可以使用 /我的宝可梦 来查看您的宝可梦详情。"
        }

    def create_init_pokemon(self, species_id: int) -> Dict[str, Any]:
        """
        创建一个新的宝可梦实例，使用指定的宝可梦ID
        Args:
            species_id (int): 宝可梦的ID

        Returns:
            Pokemon: 新创建的宝可梦实例
        """
        # 局部函数：生成0-31的随机IV
        def generate_iv() -> int:
            return random.randint(0, 31)

        # 获取宝可梦完整基础数据
        base_pokemon = self.pokemon_repo.get_pokemon_by_id(species_id).to_dict()

        # 性别从 M/F/N 随机选择
        gender = random.choice(['M', 'F', 'N'])

        # 为初始宝可梦生成随机个体值(IV)，范围0-31
        hp_iv = generate_iv()
        attack_iv = generate_iv()
        defense_iv = generate_iv()
        sp_attack_iv = generate_iv()
        sp_defense_iv = generate_iv()
        speed_iv = generate_iv()

        # 初始努力值为0
        hp_ev = 0
        attack_ev = 0
        defense_ev = 0
        sp_attack_ev = 0
        sp_defense_ev = 0
        speed_ev = 0

        # 初始等级为1
        level = 1
        exp = 0

        # 初始技能为空数组
        moves = '[]'


        pokemon = {
            'base_pokemon': base_pokemon,
            'gender': gender,
            'hp_iv': hp_iv,
            'attack_iv': attack_iv,
            'defense_iv': defense_iv,
            'sp_attack_iv': sp_attack_iv,
            'sp_defense_iv': sp_defense_iv,
            'speed_iv': speed_iv,
            'hp_ev': hp_ev,
            'attack_ev': attack_ev,
            'defense_ev': defense_ev,
            'sp_attack_ev': sp_attack_ev,
            'sp_defense_ev': sp_defense_ev,
            'speed_ev': speed_ev,
            'level': level,
            'exp': exp,
            'moves': moves,
        }

        return pokemon

    def get_user_specific_pokemon(self, user_id: str, pokemon_id: int) -> Dict[str, Any]:
        """
        获取用户特定宝可梦的详细信息
        Args:
            user_id: 用户ID
            pokemon_id: 宝可梦ID（数字ID）
        Returns:
            包含宝可梦详细信息的字典
        """
        # 获取特定宝可梦的信息
        pokemon_data = self.user_repo.get_user_pokemon_by_id(user_id, int(pokemon_id))
        if not pokemon_data:
            return {
                "success": False,
                "message": "❌ 您没有这只宝可梦，或宝可梦不存在。"
            }

        # 显示详细信息
        gender_str = {
            "M": "♂️",
            "F": "♀️",
            "N": "⚲"
        }.get(pokemon_data["gender"], "")

        message = f"🔍 宝可梦详细信息：\n\n"
        message += f"{pokemon_data['name']} {gender_str}\n\n"
        message += f"等级: {pokemon_data['level']}\n"
        message += f"经验: {pokemon_data['exp']}\n\n"

        # 实际属性值
        message += "💪 属性值:\n\n"
        message += f"  HP: {pokemon_data['stats']['hp']}\t\n"
        message += f"  攻击: {pokemon_data['stats']['attack']}\t\n"
        message += f"  防御: {pokemon_data['stats']['defense']}\n\n"
        message += f"  特攻: {pokemon_data['stats']['sp_attack']}\t\n"
        message += f"  特防: {pokemon_data['stats']['sp_defense']}\t\n"
        message += f"  速度: {pokemon_data['stats']['speed']}\n\n"

        # 个体值 (IV)
        message += "📊 个体值 (IV):\n\n"
        message += f"  HP: {pokemon_data['ivs']['hp_iv']}/31\t\n"
        message += f"  攻击: {pokemon_data['ivs']['attack_iv']}/31\t\n"
        message += f"  防御: {pokemon_data['ivs']['defense_iv']}/31\n\n"
        message += f"  特攻: {pokemon_data['ivs']['sp_attack_iv']}/31\t\n"
        message += f"  特防: {pokemon_data['ivs']['sp_defense_iv']}/31\t\n"
        message += f"  速度: {pokemon_data['ivs']['speed_iv']}/31\n\n"

        # 努力值 (EV)
        message += "📈 努力值 (EV):\n\n"
        message += f"  HP: {pokemon_data['evs']['hp_ev']}\t\n"
        message += f"  攻击: {pokemon_data['evs']['attack_ev']}\t\n"
        message += f"  防御: {pokemon_data['evs']['defense_ev']}\n\n"
        message += f"  特攻: {pokemon_data['evs']['sp_attack_ev']}\t\n"
        message += f"  特防: {pokemon_data['evs']['sp_defense_ev']}\t\n"
        message += f"  速度: {pokemon_data['evs']['speed_ev']}\n\n"

        message += f"捕获时间: {pokemon_data['caught_time']}"

        return {
            "success": True,
            "message": message
        }

    def get_user_all_pokemon(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的所有宝可梦信息
        Args:
            user_id: 用户ID
        Returns:
            包含用户宝可梦信息的字典
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        user_pokemon_list = self.user_repo.get_user_pokemon(user_id)

        if not user_pokemon_list:
            return {"success": True, "message": "您还没有获得任何宝可梦", "pokemon_list": []}

        # 格式化返回数据
        formatted_pokemon = []
        for pokemon in user_pokemon_list:
            formatted_pokemon.append({
                "id": pokemon["id"],
                "species_id": pokemon["species_id"],
                "name": pokemon["name"],
                "level": pokemon["level"],
                "exp": pokemon["exp"],
                "gender": pokemon["gender"],
                "hp": pokemon["stats"]["hp"],
                "attack": pokemon["stats"]["attack"],
                "defense": pokemon["stats"]["defense"],
                "sp_attack": pokemon["stats"]["sp_attack"],
                "sp_defense": pokemon["stats"]["sp_defense"],
                "speed": pokemon["stats"]["speed"],
            })

        # 组织显示信息
        message = f"🌟 您拥有 {len(formatted_pokemon)} 只宝可梦：\n\n"
        for i, pokemon in enumerate(formatted_pokemon, 1):
            gender_str = {
                "M": "♂️",
                "F": "♀️",
                "N": "⚲"
            }.get(pokemon["gender"], "")

            message += f"{i}. {pokemon['name']} {gender_str}\n"
            message += f"   ID：{pokemon['id']} | 等级: {pokemon['level']} | HP: {pokemon['hp']}\n"

        message += f"\n您可以使用 /我的宝可梦 <宝可梦ID> 来查看特定宝可梦的详细信息。"

        return {
            "success": True,
            "message": message
        }
