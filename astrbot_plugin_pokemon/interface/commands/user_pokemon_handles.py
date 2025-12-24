from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING, List

from ...core.models.pokemon_models import UserPokemonInfo
from ...core.models.user_models import User
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32
from .draw.user_pokemon_drawer import draw_user_pokemon_list, draw_user_pokemon_detail
import os

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
        self.tmp_dir = container.tmp_dir

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
        """查看我的宝可梦，支持查看特定宝可梦详细信息和按属性类型搜索"""
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
            # 处理按属性类型搜索
            elif self._is_valid_pokemon_type(arg):  # 检查是否为有效宝可梦属性类型
                pokemon_type = arg
                page = 1  # 默认显示第一页
                if len(args) >= 3 and args[2].lower().startswith('p') and args[2].lower()[1:].isdigit():
                    page = max(1, int(args[2].lower()[1:]))
                yield await self._handle_type_filter_view(event, user_id, pokemon_type, page)
            else:
                yield event.plain_result(AnswerEnum.POKEMON_ID_INVALID.value)

    async def _handle_list_view(self, event, user_id, page):
        """处理列表分页逻辑"""
        page_size = 10  # 图片模式改为每页10个更合适
        res = self.user_pokemon_service.get_user_pokemon_paged(user_id, page=page, page_size=page_size)
        if not res.success:
            return event.plain_result(res.message)

        data = res.data
        pokemon_list = data.get("pokemon_list", [])
        if not pokemon_list:
            return event.plain_result(AnswerEnum.USER_POKEMONS_NOT_FOUND.value)
            
        # 构建绘图数据
        draw_data = {
            "total_count": data['total_count'],
            "page": data['page'],
            "total_pages": data['total_pages'],
            "list": []
        }
        
        for p in pokemon_list:
            info = self._get_pokemon_basic_info(p)
            draw_data["list"].append({
                "id": p.id,
                "sprite_id": p.species_id,
                "name": p.name,
                "level": p.level,
                "gender": info['gender'], # 传递图标或文字
                "nature": info['nature'],
                "ability": info['ability'],
                "current_hp": p.current_hp,
                "max_hp": p.stats.hp,
                "types": info['types'].split('/') if info['types'] != "未知" else []
            })
        # 生成图片
        img = draw_user_pokemon_list(draw_data)
        save_path = os.path.join(self.tmp_dir, f"user_pokemon_list_{user_id}_{page}.png")
        img.save(save_path)
        return event.image_result(save_path)

    async def _handle_detail_view(self, event, user_id, pokemon_id):
        """处理单只宝可梦详情逻辑"""
        res = self.user_pokemon_service.get_user_pokemon_by_id(user_id, pokemon_id)
        if not res.success:
            return event.plain_result(res.message)

        p: UserPokemonInfo = res.data
        info = self._get_pokemon_basic_info(p)

        # 招式数据
        moves_data = []
        for i in range(1, 5):
             mid = getattr(p.moves, f"move{i}_id", None)
             if mid:
                 m = self.plugin.move_repo.get_move_by_id(mid)
                 moves_data.append({
                     "name": m['name_zh'] if m else f"未知[{mid}]",
                     "type": m['type_name'] if m else "一般",
                     "pp": getattr(p, f"current_pp{i}", getattr(p.moves, f"move{i}_pp", 0)), 
                     # 注意：UserPokemonInfo 有 current_ppX 字段，如果没数据可能需要 fallback
                     # 模型里 UserPokemonInfo 定义了 current_ppX。
                     # PokemonMoves 里只有 id? 检查了模型，UserPokemonInfo 才有 current_pp。
                     # 不过 UserPokemonInfo.moves 是 PokemonMoves 对象，PokemonMoves 对象没有 pp 字段（只有ID）。
                     # Move Repo m['pp'] 是 max_pp.
                     "max_pp": m['pp'] if m else 0
                 })

        # 能力值数据
        stats_map = [
            ("HP", "hp", "hp_iv", "hp_ev"),
            ("攻击", "attack", "attack_iv", "attack_ev"),
            ("防御", "defense", "defense_iv", "defense_ev"),
            ("特攻", "sp_attack", "sp_attack_iv", "sp_attack_ev"),
            ("特防", "sp_defense", "sp_defense_iv", "sp_defense_ev"),
            ("速度", "speed", "speed_iv", "speed_ev")
        ]
        
        stats_detail = []
        for label, s_key, iv_key, ev_key in stats_map:
            stats_detail.append({
                "label": label,
                "val": p.stats[s_key],
                "iv": p.ivs[iv_key],
                "ev": p.evs[ev_key]
            })

        detail_data = {
             "id": p.id,
             "sprite_id": p.species_id,
             "name": p.name,
             "level": p.level,
             "gender": info['gender'],
             "nature": info['nature'],
             "ability": info['ability'],
             "exp": p.exp,
             "caught_time": p.caught_time, # str
             "types": info['types'].split('/') if info['types'] != "未知" else [],
             "stats_detail": stats_detail,
             "moves": moves_data
        }
        
        img = draw_user_pokemon_detail(detail_data)
        save_path = os.path.join(self.tmp_dir, f"user_pokemon_detail_{user_id}_{pokemon_id}.png")
        img.save(save_path)
        return event.image_result(save_path)

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

    def _is_valid_pokemon_type(self, type_name: str) -> bool:
        """检查是否为有效的宝可梦属性类型"""
        # 宝可梦的标准属性类型列表（中文名）
        valid_types = {
            'normal', 'fighting', 'flying', 'poison', 'ground',
            'rock', 'bug', 'ghost', 'steel', 'fire', 'water',
            'grass', 'electric', 'psychic', 'ice', 'dragon',
            'dark', 'fairy',
            # 中文属性名称
            '一般', '格斗', '飞行', '毒', '地面', '岩石', '虫',
            '幽灵', '钢', '火', '水', '草', '电', '超能力',
            '冰', '龙', '恶', '妖精'
        }
        return type_name.lower() in valid_types

    async def _handle_type_filter_view(self, event, user_id, pokemon_type, page):
        """处理按属性类型过滤的宝可梦列表显示"""
        page_size = 10
        # 获取用户所有宝可梦
        all_res = self.user_pokemon_service.get_user_all_pokemon(user_id)
        if not all_res.success:
            return event.plain_result(all_res.message)

        all_pokemon = all_res.data
        if not all_pokemon:
            return event.plain_result(AnswerEnum.USER_POKEMONS_NOT_FOUND.value)

        # 按属性类型过滤
        filtered_pokemon = []
        for p in all_pokemon:
            pokemon_info = self._get_pokemon_basic_info(p)
            types_list = pokemon_info['types'].split('/')
            if pokemon_type in types_list or pokemon_type in [t.lower() for t in types_list]:
                filtered_pokemon.append(p)

        # 计算总页数
        total_count = len(filtered_pokemon)
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        # 检查页码是否有效
        if page > total_pages:
            return event.plain_result(f"❌ 页码超出范围，最大页数为 {total_pages}")

        # 获取当前页的数据
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        pokemon_page = filtered_pokemon[start_idx:end_idx]

        if not pokemon_page:
            return event.plain_result(f"❌ 您没有持有属性为 '{pokemon_type}' 的宝可梦")

        # 构建绘图数据
        draw_data = {
            "total_count": total_count,
            "page": page,
            "total_pages": total_pages,
            "list": []
        }

        for p in pokemon_page:
            info = self._get_pokemon_basic_info(p)
            draw_data["list"].append({
                "id": p.id,
                "sprite_id": p.species_id,
                "name": p.name,
                "level": p.level,
                "gender": info['gender'],  # 传递图标或文字
                "nature": info['nature'],
                "ability": info['ability'],
                "current_hp": p.current_hp,
                "max_hp": p.stats.hp,
                "types": info['types'].split('/') if info['types'] != "未知" else []
            })

        # 生成图片
        img = draw_user_pokemon_list(draw_data)
        save_path = os.path.join(self.tmp_dir, f"user_pokemon_{pokemon_type}_list_{user_id}_{page}.png")
        img.save(save_path)
        return event.image_result(save_path)

    async def favorite_pokemon(self, event: AstrMessageEvent):
        """收藏宝可梦命令处理器"""
        user_id = userid_to_base32(event.get_sender_id())

        # 1. 权限/注册检查
        reg_check = self.user_service.check_user_registered(user_id)
        if not reg_check.success:
            yield event.plain_result(reg_check.message)
            return

        args = event.message_str.split()

        # 检查参数
        if len(args) < 2:
            yield event.plain_result("❌ 请指定要收藏的宝可梦ID，格式：/收藏宝可梦 [宝可梦ID]")
            return

        try:
            pokemon_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 宝可梦ID必须是数字")
            return

        # 调用服务层设置收藏状态
        result = self.user_pokemon_service.set_pokemon_favorite(user_id, pokemon_id, True)
        yield event.plain_result(result.message)

    async def unfavorite_pokemon(self, event: AstrMessageEvent):
        """取消收藏宝可梦命令处理器"""
        user_id = userid_to_base32(event.get_sender_id())

        # 1. 权限/注册检查
        reg_check = self.user_service.check_user_registered(user_id)
        if not reg_check.success:
            yield event.plain_result(reg_check.message)
            return

        args = event.message_str.split()

        # 检查参数
        if len(args) < 2:
            yield event.plain_result("❌ 请指定要取消收藏的宝可梦ID，格式：/取消收藏宝可梦 [宝可梦ID]")
            return

        try:
            pokemon_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 宝可梦ID必须是数字")
            return

        # 调用服务层取消收藏状态
        result = self.user_pokemon_service.set_pokemon_favorite(user_id, pokemon_id, False)
        yield event.plain_result(result.message)

    async def view_favorite_pokemon(self, event: AstrMessageEvent):
        """查看收藏宝可梦命令处理器，支持分页"""
        user_id = userid_to_base32(event.get_sender_id())

        # 1. 权限/注册检查
        reg_check = self.user_service.check_user_registered(user_id)
        if not reg_check.success:
            yield event.plain_result(reg_check.message)
            return

        args = event.message_str.split()
        page = 1

        # 解析页码参数
        if len(args) > 1:
            page_arg = args[1].lower()
            if page_arg.startswith('p'):
                try:
                    page = int(page_arg[1:])
                except ValueError:
                    yield event.plain_result("❌ 页码格式错误，请使用 P<数字> 格式，例如：/查看收藏宝可梦 P2")
                    return
            elif page_arg.isdigit():
                try:
                    page = int(page_arg)
                except ValueError:
                    yield event.plain_result("❌ 页码格式错误")
                    return

        # 调用服务层获取收藏的宝可梦列表
        res = self.user_pokemon_service.get_user_favorite_pokemon_paged(user_id, page=page, page_size=10)
        if not res.success:
            yield event.plain_result(res.message)
            return

        data = res.data
        pokemon_list = data.get("pokemon_list", [])
        if not pokemon_list:
            yield event.plain_result("❌ 您还没有收藏任何宝可梦")
            return

        # 构建绘图数据
        draw_data = {
            "total_count": data['total_count'],
            "page": data['page'],
            "total_pages": data['total_pages'],
            "list": []
        }

        for p in pokemon_list:
            info = self._get_pokemon_basic_info(p)
            draw_data["list"].append({
                "id": p.id,
                "sprite_id": p.species_id,
                "name": p.name,
                "level": p.level,
                "gender": info['gender'],  # 传递图标或文字
                "nature": info['nature'],
                "ability": info['ability'],
                "current_hp": p.current_hp,
                "max_hp": p.stats.hp,
                "types": info['types'].split('/') if info['types'] != "未知" else []
            })

        # 生成图片
        try:
            img = draw_user_pokemon_list(draw_data)
            save_path = os.path.join(self.tmp_dir, f"user_favorite_pokemon_list_{user_id}_{page}.png")
            img.save(save_path)

            # 返回图片
            yield event.image_result(save_path)
        except Exception as e:
            # 如果绘图失败，返回文本格式
            pokemon_names = [f"{p.name}(ID:{p.id}, Lv.{p.level})" for p in pokemon_list]
            formatted_message = f"🌟 您收藏的宝可梦列表（第{data['page']}页/{data['total_pages']}页）:\n" + "\n".join(pokemon_names)
            yield event.plain_result(formatted_message)

    async def equip_held_item(self, event: AstrMessageEvent):
        """装备持有物命令处理器"""
        user_id = userid_to_base32(event.get_sender_id())

        # 1. 权限/注册检查
        reg_check = self.user_service.check_user_registered(user_id)
        if not reg_check.success:
            yield event.plain_result(reg_check.message)
            return

        # 解析参数
        args = event.message_str.split()
        if len(args) < 3:
            yield event.plain_result("❌ 请指定宝可梦ID和道具ID，格式：/装备持有物 [宝可梦ID] [道具ID]")
            return

        try:
            pokemon_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 宝可梦ID必须是数字")
            return

        try:
            item_id = int(args[2])
        except ValueError:
            yield event.plain_result("❌ 道具ID必须是数字")
            return

        # 调用服务层装备持有物
        result = self.user_pokemon_service.set_pokemon_held_item(user_id, pokemon_id, item_id)

        yield event.plain_result(result.message)