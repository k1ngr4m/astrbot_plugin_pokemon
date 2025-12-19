from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING, List

from ...core.models.pokemon_models import UserPokemonInfo
from ...core.models.user_models import User
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class UserPokemonHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.user_service = container.user_service
        self.pokemon_service = container.pokemon_service
        self.user_pokemon_service = container.user_pokemon_service
        self.nature_service = container.nature_service
        self.ability_service = container.ability_service

    async def init_select(self, event: AstrMessageEvent):
        """初始化选择宝可梦"""
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return
        user:User = result.data

        # 检查用户是否已经初始化选择宝可梦
        if user.init_selected:
            yield event.plain_result(AnswerEnum.USER_ALREADY_INITIALIZED_POKEMON.value)
            return

        # 解析宝可梦ID
        args = event.message_str.split()
        # 检查参数数量是否正确
        if len(args) < 2:
            yield event.plain_result(AnswerEnum.POKEMON_INIT_SELECT_USAGE_ERROR.value)
            return
        try:
            pokemon_id = int(args[1])
            if pokemon_id not in (1, 4, 7):
                yield event.plain_result(AnswerEnum.POKEMON_INIT_SELECT_INVALID_POKEMON_ID.value)
                return
        except ValueError:
            yield event.plain_result(AnswerEnum.POKEMON_ID_INVALID.value)
            return

        # 检查宝可梦是否存在
        pokemon_info = self.pokemon_service.get_pokemon_by_id(pokemon_id)
        if not pokemon_info:
            yield event.plain_result(AnswerEnum.POKEMON_NOT_FOUND.value)
            return

        new_pokemon = self.pokemon_service.create_single_pokemon(pokemon_id, max_level=5, min_level=5)
        if not new_pokemon.success:
            yield event.plain_result(new_pokemon.message)
            return

        result = self.user_pokemon_service.init_select_pokemon(user_id, new_pokemon.data)
        if result.success:
            yield event.plain_result(
                AnswerEnum.POKEMON_INIT_SELECT_SUCCESS.value.format(
                    pokemon_name=result.data["pokemon_name"],
                    pokemon_id=result.data["pokemon_id"]
                )
            )
        else:
            yield event.plain_result(result.message)

    async def view_user_pokemon(self, event: AstrMessageEvent):
        """查看我的宝可梦，支持查看特定宝可梦详细信息"""
        user_id = userid_to_base32(event.get_sender_id())

        # 1. 权限/注册检查
        reg_check = self.user_service.check_user_registered(user_id)
        if not reg_check.success:
            yield event.plain_result(reg_check.message)
            return

        args = event.message_str.split()

        # 2. 分支逻辑处理
        if len(args) < 2:
            # 默认显示第一页
            yield await self._handle_list_view(event, user_id, page=1)
        else:
            arg = args[1].lower()
            # 处理分页指令: P2, p3...
            if arg.startswith('p') and arg[1:].isdigit():
                page = max(1, int(arg[1:]))
                yield await self._handle_list_view(event, user_id, page)
            # 处理详情指令: 数字ID
            elif arg.isdigit():
                yield await self._handle_detail_view(event, user_id, int(arg))
            else:
                yield event.plain_result(AnswerEnum.POKEMON_ID_INVALID.value)

    async def _handle_list_view(self, event, user_id, page):
        """处理列表分页逻辑"""
        page_size = 20
        res = self.user_pokemon_service.get_user_pokemon_paged(user_id, page=page, page_size=page_size)
        if not res.success:
            return event.plain_result(res.message)

        data = res.data
        pokemon_list = data.get("pokemon_list", [])
        if not pokemon_list:
            return event.plain_result(AnswerEnum.USER_POKEMONS_NOT_FOUND.value)

        msg = f"🌟 您拥有 {data['total_count']} 只宝可梦 (第 {data['page']}/{data['total_pages']} 页)：\n\n"
        start_idx = (data['page'] - 1) * page_size + 1

        for i, p in enumerate(pokemon_list, start_idx):
            # 提取公共格式化逻辑
            info = self._get_pokemon_basic_info(p)
            msg += f"{i}. {p.name} {info['gender']}\n"
            msg += f"---ID: {p.id}  |  等级: {p.level}  |  HP: {p.stats['hp']}\n\n"
            msg += f"---属性: {info['types']}  |  特性: {info['ability']}  |  性格: {info['nature']}\n\n"

        msg += f"\n使用 /我的宝可梦 P[页数] 查看其他页\n或使用 /我的宝可梦 <ID> 查看详情。"
        return event.plain_result(msg)

    async def _handle_detail_view(self, event, user_id, pokemon_id):
        """处理单只宝可梦详情逻辑"""
        res = self.user_pokemon_service.get_user_pokemon_by_id(user_id, pokemon_id)
        if not res.success:
            return event.plain_result(res.message)

        p: UserPokemonInfo = res.data
        info = self._get_pokemon_basic_info(p)

        # 组装基础信息
        msg = f"🔍 宝可梦详细信息：\n\n{p.name} {info['gender']}\n"
        msg += f"属性: {info['types']}  |  性格: {info['nature']}  |  特性: {info['ability']}\n"
        msg += f"等级: {p.level}  |  经验: {p.exp}\n\n"

        # 组装数值矩阵 (使用表格化排版对齐更美观)
        stats_map = [
            ("HP", "hp", "hp_iv", "hp_ev"),
            ("攻击", "attack", "attack_iv", "attack_ev"),
            ("防御", "defense", "defense_iv", "defense_ev"),
            ("特攻", "sp_attack", "sp_attack_iv", "sp_attack_ev"),
            ("特防", "sp_defense", "sp_defense_iv", "sp_defense_ev"),
            ("速度", "speed", "speed_iv", "speed_ev")
        ]

        msg += "💪 能力详情 (能力值 | IV | EV):\n\n"
        for label, s_key, iv_key, ev_key in stats_map:
            val = p.stats[s_key]
            iv = p.ivs[iv_key]
            ev = p.evs[ev_key]
            msg += f"  {label}: {val:<3} | {iv:>2}/31 | {ev:<3}\n\n"

        # 组装招式
        msg += "\n⚔️ 招式:\n"
        for i in range(1, 5):
            move_id = getattr(p.moves, f'move{i}_id', None)
            name = "(空)"
            if move_id:
                m_info = self.plugin.move_repo.get_move_by_id(move_id)
                name = m_info['name_zh'] if m_info else f"未知[{move_id}]"
            msg += f"  {i}. {name}\n"

        msg += f"\n📅 捕获时间: {p.caught_time}"
        return event.plain_result(msg)

    def _get_pokemon_basic_info(self, p):
        """辅助方法：统一获取宝可梦的基础显示文本"""
        # 性别图标
        gender_icon = {"M": "♂️", "F": "♀️", "N": "⚲"}.get(p.gender, "")

        # 类型/属性
        raw_types = self.pokemon_service.get_pokemon_types(p.species_id)
        types_str = '/'.join(dict.fromkeys(raw_types)) if raw_types else "未知"

        # 性格
        nature_name = self.nature_service.get_nature_name_by_id(p.nature_id)

        # 特性
        ability_name = "未知"
        if p.ability_id and p.ability_id > 0:
            a_info = self.ability_service.get_ability_by_id(p.ability_id)
            if a_info:
                ability_name = a_info.get('name_zh', a_info.get('name_en', '未知'))

        return {
            "gender": gender_icon,
            "types": types_str,
            "nature": nature_name,
            "ability": ability_name
        }