from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32
import io

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

import os

class PokemonHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.pokemon_service = container.pokemon_service
        self.user_pokemon_service = container.user_pokemon_service
        self.move_service = container.move_service
        self.ability_service = container.ability_service
        self.pokemon_repo = container.pokemon_repo
        self.tmp_dir = container.tmp_dir

        try:
            from .draw.pokedex_detail import draw_pokedex_detail
            self.draw_pokedex_detail_func = draw_pokedex_detail
        except ImportError:
            self.draw_pokedex_detail_func = None
            print("警告：无法导入图鉴详情生成模块，请确保PIL和numpy已安装。")

    def _show_pokedex_detail(self, user_id, query):
        """
        显示单只宝可梦的图鉴详情
        :param user_id: 用户ID
        :param query: 查询参数（宝可梦ID或名称）
        :return: 图鉴详情文本或错误消息
        """
        # 先尝试按ID查找
        if query.isdigit():
            species_info = self.pokemon_service.get_pokemon_by_id(int(query))
        else:
            # 按名称查找
            species_info = self.pokemon_service.get_pokemon_by_name(query)

        if not species_info:
            message = f"❌ 未找到宝可梦: {query}"
            return message

        # 检查用户是否已遇到或捕捉过该宝可梦
        user_progress = self.user_pokemon_service.get_user_pokedex_ids(user_id)
        if user_progress.success:
            d = user_progress.data
            caught_set = d['caught']
            seen_set = d['seen']
        else:
            return user_progress.message

        # 检查图片生成模块是否可用
        if not self.draw_pokedex_detail_func:
            # 如果图片模块不可用，返回文本
            if species_info.id not in seen_set:
                detail_text = f"🔍 图鉴信息: #{species_info.id:04d} ???\n\n"
                detail_text += f"该宝可梦的详细信息暂未解锁。\n\n"
                detail_text += f"请先在野外遇到该宝可梦以解锁图鉴信息。"
            else:
                detail_text = f"📖 图鉴信息: #{species_info.id:04d} {species_info.name_zh}\n\n"
                detail_text += f"类型: {'/'.join(self.pokemon_repo.get_pokemon_types(species_info.id))}\n\n"
                detail_text += f"身高: {species_info.height}m | 体重: {species_info.weight}kg\n\n"
                detail_text += f"种族值: \n\n"
                detail_text += f"HP:{species_info.base_stats.base_hp}\n"
                detail_text += f"攻击:{species_info.base_stats.base_attack}\n"
                detail_text += f"防御:{species_info.base_stats.base_defense}\n\n"
                detail_text += f"特攻:{species_info.base_stats.base_sp_attack}\n"
                detail_text += f"特防:{species_info.base_stats.base_sp_defense}\n"
                detail_text += f"速度:{species_info.base_stats.base_speed}\n\n"
                detail_text += f"描述: {species_info.description}\n\n"

                if species_info.id in caught_set:
                    detail_text += f"\n✅ 状态: 已捕捉"
                else:
                    detail_text += f"\n👁️ 状态: 已遇见"
            return detail_text

        # 用户未遇到过该宝可梦，返回文本提示
        if species_info.id not in seen_set:
            detail_text = f"🔍 图鉴信息: #{species_info.id:04d} ???\n\n"
            detail_text += f"该宝可梦的详细信息暂未解锁。\n\n"
            detail_text += f"请先在野外遇到该宝可梦以解锁图鉴信息。"
            return detail_text

        # 准备图片数据
        pokemon_data = {
            "id": species_info.id,
            "name_zh": species_info.name_zh,
            "types": self.pokemon_repo.get_pokemon_types(species_info.id),
            "height": species_info.height,
            "weight": species_info.weight,
            "base_stats": {
                "base_hp": species_info.base_stats.base_hp,
                "base_attack": species_info.base_stats.base_attack,
                "base_defense": species_info.base_stats.base_defense,
                "base_sp_attack": species_info.base_stats.base_sp_attack,
                "base_sp_defense": species_info.base_stats.base_sp_defense,
                "base_speed": species_info.base_stats.base_speed
            },
            "description": species_info.description,
            "caught": species_info.id in caught_set,
            "seen": species_info.id in seen_set
        }

        # 生成图片
        try:
            image = self.draw_pokedex_detail_func(pokemon_data)
            # 将图片转换为字节流
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr
        except Exception as e:
            print(f"生成图鉴详情图片失败: {e}")
            # 如果生成图片失败，返回文本
            if species_info.id not in seen_set:
                detail_text = f"🔍 图鉴信息: #{species_info.id:04d} ???\n\n"
                detail_text += f"该宝可梦的详细信息暂未解锁。\n\n"
                detail_text += f"请先在野外遇到该宝可梦以解锁图鉴信息。"
            else:
                detail_text = f"📖 图鉴信息: #{species_info.id:04d} {species_info.name_zh}\n\n"
                detail_text += f"类型: {'/'.join(self.pokemon_repo.get_pokemon_types(species_info.id))}\n\n"
                detail_text += f"身高: {species_info.height}m | 体重: {species_info.weight}kg\n\n"
                detail_text += f"种族值: \n\n"
                detail_text += f"HP:{species_info.base_stats.base_hp}\n"
                detail_text += f"攻击:{species_info.base_stats.base_attack}\n"
                detail_text += f"防御:{species_info.base_stats.base_defense}\n\n"
                detail_text += f"特攻:{species_info.base_stats.base_sp_attack}\n"
                detail_text += f"特防:{species_info.base_stats.base_sp_defense}\n"
                detail_text += f"速度:{species_info.base_stats.base_speed}\n\n"
                detail_text += f"描述: {species_info.description}\n\n"

                if species_info.id in caught_set:
                    detail_text += f"\n✅ 状态: 已捕捉"
                else:
                    detail_text += f"\n👁️ 状态: 已遇见"
            return detail_text

    async def pokedex(self, event: AstrMessageEvent):
        """
        查询图鉴
        指令1: /图鉴 ：查看第一页图鉴
        指令2: /图鉴 P+[页码] ：查看第P页图鉴
        指令3: /图鉴 M+[宝可梦ID/宝可梦名] ：查看宝可梦图鉴详情
        """
        user_id = userid_to_base32(event.get_sender_id())
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        # 获取查询参数
        args = event.message_str.split()
        if len(args) > 1:
            query = ' '.join(args[1:]).strip()
        else:
            query = ''

        # 情况 A: 检查是否为P页码格式
        if query.upper().startswith('P'):
            try:
                page_str = query[1:]  # 去掉"P"前缀
                page = int(page_str)
                if page <= 0:
                    yield event.plain_result("页码必须是正整数！")
                    return
                # 调用 Service 获取列表视图
                result_text = self.pokemon_service.get_pokedex_view(user_id, page)
                yield event.plain_result(result_text)
                return
            except ValueError:
                yield event.plain_result("页码格式错误！请使用 /图鉴 P+页码 格式。")
                return

        # 情况 B: 检查是否为M+查询格式
        elif query.upper().startswith('M'):
            query_param = query[1:]  # 去掉"M"前缀
            if not query_param:
                yield event.plain_result("查询参数不能为空！请使用 /图鉴 M+宝可梦ID或名称 格式。")
                return
            result = self._show_pokedex_detail(user_id, query_param)
            if isinstance(result, io.BytesIO):
                # 保存图片到临时文件并返回
                import uuid
                filename = f"pokedex_detail_{uuid.uuid4().hex}.png"
                output_path = os.path.join(self.tmp_dir, filename)
                # 将字节流保存到临时文件
                with open(output_path, 'wb') as f:
                    f.write(result.getvalue())
                yield event.image_result(output_path)
            elif isinstance(result, str):
                yield event.plain_result(result)
            else:
                yield event.plain_result(result.message)
            return

        # 情况 C: 如果是纯数字，视为页码
        elif query.isdigit():
            page = int(query)
            if page <= 0:
                yield event.plain_result("页码必须是正整数！")
                return
            # 调用 Service 获取列表视图
            result_text = self.pokemon_service.get_pokedex_view(user_id, page)
            yield event.plain_result(result_text)
            return

        # 情况 D: 其他非空参数视为宝可梦名称或ID查询
        elif query:
            result = self._show_pokedex_detail(user_id, query)
            if isinstance(result, io.BytesIO):
                # 保存图片到临时文件并返回
                import uuid
                filename = f"pokedex_detail_{uuid.uuid4().hex}.png"
                output_path = os.path.join(self.tmp_dir, filename)
                # 将字节流保存到临时文件
                with open(output_path, 'wb') as f:
                    f.write(result.getvalue())
                yield event.image_result(output_path)
            elif isinstance(result, str):
                yield event.plain_result(result)
            else:
                yield event.plain_result(result.message)
            return

        # 情况 E: 默认显示第一页
        result_text = self.pokemon_service.get_pokedex_view(user_id, 1)
        yield event.plain_result(result_text)

    async def view_move_info(self, event: AstrMessageEvent):
        """查询招式详细信息。用法：/查询招式 [招式ID或招式名称]"""
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = self.user_service.check_user_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        # 解析招式参数
        args = event.message_str.split()
        if len(args) < 2:
            yield event.plain_result("❌ 请提供招式ID或招式名称，例如：/查询招式 1 或 /查询招式 冲浪")
            return

        query = args[1].strip()

        # 先尝试按ID查询
        move_info = None
        try:
            move_id = int(query)
            if move_id > 0:
                move_info = self.move_service.get_move_by_id(move_id)
                if move_info:
                    move_id_for_stats = move_id  # 用于后续获取能力变化信息
        except ValueError:
            # 如果不是数字，尝试按名称查询
            move_info = self.move_service.get_move_by_name(query)
            if move_info:
                move_id_for_stats = move_info['id']  # 用于后续获取能力变化信息

        if not move_info:
            yield event.plain_result(f"❌ 找不到ID或名称为 {query} 的招式！")
            return

        # 构建详细信息
        type_name = move_info.get('type_name', 'unknown')
        power = move_info.get('power', '—')
        pp = move_info.get('pp', 1)
        accuracy = move_info.get('accuracy', '—')
        description = move_info.get('description', '暂无描述')

        # 根据招式类型确定伤害类别
        damage_class_map = {1: '变化', 2: '物理', 3: '特殊'}
        damage_class = damage_class_map.get(move_info.get('damage_class_id', 1), '未知')

        message = [
            f"📖 招式信息: {move_info['name_zh']} (ID: {move_info['id']})\n\n",
            f"类型: {type_name} | 类别: {damage_class}\n\n",
            f"威力: {power} | PP: {pp} | 命中: {accuracy}%\n\n",
            f"描述: {description}\n\n",
            ""
        ]

        # 添加能力变化信息
        stat_changes = self.move_service.get_move_stat_changes_by_move_id(move_id_for_stats)
        if stat_changes:
            message.append("能力变化:\n\n")
            stat_map = {1: 'HP', 2: '攻击', 3: '防御', 4: '特攻', 5: '特防', 6: '速度'}
            for stat_change in stat_changes:
                stat_id = stat_change['stat_id']
                change = stat_change['change']
                stat_name = stat_map.get(stat_id, '未知')
                message.append(f"  {stat_name}: {'+' if change > 0 else ''}{change}\n\n")
            message.append("")

        # 添加连击/回合信息
        # min_hits = move_info.get('min_hits')
        # max_hits = move_info.get('max_hits')
        # if min_hits and max_hits and min_hits != max_hits:
        #     message.append(f"连击次数: {min_hits}-{max_hits}次\n\n")
        # elif min_hits and max_hits and min_hits == max_hits and min_hits > 1:
        #     message.append(f"连击次数: {min_hits}次\n\n")
        #
        # min_turns = move_info.get('min_turns')
        # max_turns = move_info.get('max_turns')
        # if min_turns and max_turns and min_turns != max_turns:
        #     message.append(f"持续回合: {min_turns}-{max_turns}回合\n\n")
        # elif min_turns and max_turns and min_turns == max_turns and min_turns > 1:
        #     message.append(f"持续回合: {max_turns}回合\n\n")

        # 添加吸血/回复信息
        drain = move_info.get('drain', 0)
        healing = move_info.get('healing', 0)
        if drain != 0:
            message.append(f"吸血率: {drain}%\n\n")
        if healing != 0:
            message.append(f"回复率: {healing}%\n\n")

        yield event.plain_result("\n".join(message))

    async def view_ability_info(self, event: AstrMessageEvent):
        """查看特性详细信息。用法：/查询特性 [特性名称]"""
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = self.user_service.check_user_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        # 解析参数
        args = event.message_str.split()
        if len(args) < 2:
            yield event.plain_result("❌ 请提供特性名称，例如：/查询特性 猛火")
            return

        query = args[1].strip()

        # 先尝试按ID查询 (虽然指令说是名称，但支持ID也不错)
        ability_info = None
        if query.isdigit():
            ability_info = self.ability_service.get_ability_by_id(int(query))
        
        # 尝试按名称查询
        if not ability_info:
            ability_info = self.ability_service.get_ability_by_name(query)

        if not ability_info:
            yield event.plain_result(f"❌ 找不到名称为 {query} 的特性！")
            return

        # 构建详细信息
        name_zh = ability_info.get('name_zh', '未知')
        name_en = ability_info.get('name_en', 'Unknown')
        desc = ability_info.get('description', '暂无描述')
        gen = ability_info.get('generation_id', '?')

        message = [
            f"✨ 特性信息: {name_zh} ({name_en})\n",
            f"ID: {ability_info['id']} | 世代: Gen {gen}\n",
            f"描述: {desc}\n"
        ]

        yield event.plain_result("\n".join(message))
