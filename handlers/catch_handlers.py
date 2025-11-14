from astrbot.api.event import AstrMessageEvent
from typing import TYPE_CHECKING
import random

from ..core.answer.answer_enum import AnswerEnum

if TYPE_CHECKING:
    from ..main import PokemonPlugin

class CatchHandlers:
    def __init__(self, plugin: "PokemonPlugin"):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.pokemon_service = plugin.pokemon_service
        self.item_service = plugin.item_service

    async def catch_pokemon(self, event: AstrMessageEvent):
        """处理捕捉野生宝可梦的指令"""
        user_id = self.plugin._get_effective_user_id(event)
        user = self.plugin.user_repo.get_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        # 检查是否有缓存的野生宝可梦信息
        wild_pokemon = getattr(self.plugin, '_cached_wild_pokemon', {}).get(user_id)
        if not wild_pokemon:
            yield event.plain_result("❌ 您当前没有遇到野生宝可梦。请先使用 /冒险 <区域代码> 指令去冒险遇到野生宝可梦。")
            return

        # 解析用户可能传递的道具ID参数
        message_content = event.message_str
        command_parts = message_content.split()
        item_id = None

        if len(command_parts) > 1:
            # 尝试解析第二个参数作为道具ID
            try:
                item_id = int(command_parts[1])
            except ValueError:
                # 如果不是数字，提示用户使用道具ID
                yield event.plain_result("❌ 无效的道具ID格式。请使用命令格式: /捕捉 [道具ID] 或 /捕捉")
                return

        # 检查用户背包中的道具
        user_items = self.plugin.user_repo.get_user_items(user_id)
        pokeball_item = None

        if item_id is not None:
            # 用户指定了特定的道具ID
            for item in user_items:
                if item['item_id'] == item_id and item['type'] == 'Pokeball' and item['quantity'] > 0:
                    pokeball_item = item
                    break
        else:
            # 用户未指定道具ID，自动寻找第一个可用的精灵球
            for item in user_items:
                if item['type'] == 'Pokeball' and item['quantity'] > 0:
                    pokeball_item = item
                    break

        if not pokeball_item:
            if item_id is not None:
                yield event.plain_result(f"❌ 找不到ID为 {item_id} 的精灵球或该道具不存在，无法进行捕捉！请检查道具ID或先通过签到或其他方式获得精灵球。")
            else:
                yield event.plain_result("❌ 您的背包中没有精灵球，无法进行捕捉！请先通过签到或其他方式获得精灵球。")
            return

        # 计算捕捉成功率

        # 根据精灵球类型调整基础捕捉率
        ball_multiplier = 1.0  # 普通精灵球
        if pokeball_item['name'] == '超级球':
            ball_multiplier = 1.5
        elif pokeball_item['name'] == '高级球':
            ball_multiplier = 2.0

        # 基础捕捉率，考虑精灵球类型
        base_catch_rate = 0.2 * ball_multiplier

        # 根据野生宝可梦的等级调整成功率（等级越高越难捕捉）
        level_factor = max(0.1, 1.0 - (wild_pokemon['level'] / 100.0))

        # 如果用户有战斗胜率信息，可以将其作为额外因素
        # 计算一个简化版本的胜率
        user_win_rate, wild_win_rate = self.plugin.battle_service.calculate_battle_win_rate(
            {"species_id": wild_pokemon['species_id'], "level": 5, "speed": 50,  # 假设用户派出一只低等级宝可梦
             "attack": 50, "defense": 50, "sp_attack": 50, "sp_defense": 50},
            wild_pokemon
        )

        # 将战斗胜率作为捕捉成功率的修正因子（胜利可能性高则捕捉成功率增加）
        battle_factor = user_win_rate / 100.0  # 转换为0-1之间的值
        # 捕捉成功率 = 基础捕捉率 * 等级因素 * 战斗胜率修正
        catch_success_rate = base_catch_rate * level_factor * (0.5 + 0.5 * battle_factor)

        # 确保成功率在合理范围内
        # catch_success_rate = max(0.05, min(0.95, catch_success_rate))
        # 先100%捕捉，后面再改概率
        catch_success_rate = 1

        # 随机决定捕捉结果
        is_successful = random.random() < catch_success_rate

        # 扣除一个精灵球
        self.plugin.user_repo.add_user_item(user_id, pokeball_item['item_id'], -1)

        if is_successful:
            # 成功捕捉 - 将野生宝可梦添加到用户宝可梦列表中
            # 首先创建一个基础的宝可梦记录
            pokemon_id = self.plugin.user_repo.create_user_pokemon(user_id, wild_pokemon['species_id'])

            # 然后更新宝可梦的等级和属性值为野生宝可梦的当前值
            # 获取野生宝可梦的属性值
            nickname = wild_pokemon['name']
            level = wild_pokemon['level']
            current_hp = wild_pokemon.get('current_hp', wild_pokemon.get('hp', 0))
            attack = wild_pokemon.get('attack', 0)
            defense = wild_pokemon.get('defense', 0)
            sp_attack = wild_pokemon.get('sp_attack', 0)
            sp_defense = wild_pokemon.get('sp_defense', 0)
            speed = wild_pokemon.get('speed', 0)
            name = wild_pokemon['name']
            # 更新宝可梦的属性值
            with self.plugin.user_repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_pokemon
                    SET nickname = ?, level = ?, current_hp = ?, attack = ?, defense = ?,
                        sp_attack = ?, sp_defense = ?, speed = ?
                    WHERE id = ?
                """, (name, level, current_hp, attack, defense, sp_attack, sp_defense, speed, pokemon_id))
                conn.commit()

            # 获取新捕捉的宝可梦信息
            new_pokemon = self.plugin.user_repo.get_user_pokemon_by_numeric_id(pokemon_id)

            message = f"🎉 捕捉成功！\n\n"
            message += f"您成功捕捉到了 {wild_pokemon['name']} (Lv.{wild_pokemon['level']})！\n\n"
            message += f"已添加到您的宝可梦收藏中。\n\n"
            message += f"宝可梦ID: {new_pokemon['shortcode']}\n\n"
            message += f"使用的精灵球: [{pokeball_item['item_id']}] {pokeball_item['name']}\n\n"
            message += f"剩余精灵球: {pokeball_item['quantity'] - 1}"

            # 清除缓存的野生宝可梦信息
            if hasattr(self.plugin, '_cached_wild_pokemon'):
                self.plugin._cached_wild_pokemon.pop(user_id, None)
        else:
            message = f"❌ 捕捉失败！\n\n"
            message += f"{wild_pokemon['name']} 逃脱了！\n\n"
            message += f"使用的精灵球: [{pokeball_item['item_id']}] {pokeball_item['name']}\n\n"
            message += f"捕捉成功率: {catch_success_rate * 100:.1f}%\n\n"
            message += f"剩余精灵球: {pokeball_item['quantity'] - 1}\n\n"
            message += "你也可以使用 /逃跑 指令离开这只野生宝可梦。"

        yield event.plain_result(message)