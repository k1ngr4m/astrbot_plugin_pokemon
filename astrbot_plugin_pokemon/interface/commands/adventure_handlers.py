import random
from typing import List

from astrbot.api.event import AstrMessageEvent
from ...core.models.adventure_models import LocationInfo
from ...interface.response.answer_enum import AnswerEnum
from ...core.models.pokemon_models import WildPokemonInfo, UserPokemonInfo, WildPokemonEncounterLog
from ...utils.utils import userid_to_base32


class AdventureHandlers:
    def __init__(self, plugin):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.adventure_service = plugin.adventure_service
        self.battle_service = plugin.battle_service
        self.pokemon_service = plugin.pokemon_service
        self.team_service = plugin.team_service

    async def view_locations(self, event: AstrMessageEvent):
        """查看所有可冒险的区域"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        result = self.adventure_service.get_all_locations()

        if not result.success:
            yield event.plain_result(result.message)
            return

        locations: List[LocationInfo] = result.data

        # 组织显示信息
        message = f"🗺️ {AnswerEnum.ADVENTURE_LOCATIONS_FOUND.value.format(count=len(locations))}：\n\n"
        for i, location in enumerate(locations, 1):
            message += f"{i}. {location.name}\n"
            message += f"   ID: {location.id} | 等级: {location.min_level}-{location.max_level}\n"
            if location.description != "暂无描述":
                message += f"   描述: {location.description}\n"
            message += "\n"

        message += "💡 使用 冒险 <区域ID> 指令进入冒险！"

        yield event.plain_result(message.strip())

    async def adventure(self, event: AstrMessageEvent):
        """进入指定区域冒险"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        # 检查用户是否已经遇到了野生宝可梦
        wild_pokemon = self.pokemon_service.get_user_encountered_wild_pokemon(user_id)
        if wild_pokemon:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_ALREADY_ENCOUNTERED.value)
            return

        # 检查冒险冷却时间
        import time
        current_time = time.time()
        user = self.plugin.user_repo.get_user_by_id(user_id)
        last_adventure_time = user.last_adventure_time if user and user.last_adventure_time else 0
        cooldown_remaining = (last_adventure_time + self.plugin.adventure_cooldown) - current_time

        if cooldown_remaining > 0:
            yield event.plain_result(f"❌ 冒险冷却中，请等待 {int(cooldown_remaining)} 秒后再试。")
            return

        # 检查用户是否有设置队伍
        user_team_data = self.plugin.team_repo.get_user_team(user_id)
        if not user_team_data:
            yield event.plain_result(AnswerEnum.USER_TEAM_NOT_SET.value)
            return

        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_LOCATION_NOT_SPECIFIED.value)
            return

        location_id = int(args[1])  # 转换为整数

        # 验证区域代码格式（A开头的四位数）
        if not (location_id > 0):
            yield event.plain_result(f"❌ 区域ID {location_id} 格式不正确（应为正整数）。")
            return

        result = self.adventure_service.adventure_in_location(user_id, location_id)

        if result.success:
            wild_pokemon = result.wild_pokemon
            message = f"🌳 在 {result.location.location_name} 中冒险！\n\n"
            message += f"✨ 遇到了野生的 {wild_pokemon.name}！\n"
            message += f"等级: {wild_pokemon.level}\n"

            # 记录冒险时间到数据库，用于冷却时间控制
            import time
            current_time = time.time()
            self.plugin.user_repo.update_user_last_adventure_time(user_id, current_time)

            message += ("接下来你可以选择战斗、捕捉或逃跑...\n\n"
                        "使用 /战斗 指令进行对战！\n\n"
                        "使用 /捕捉 指令尝试捕捉它！\n\n"
                        "使用 /逃跑 指令安全离开！")
            yield event.plain_result(message)
        else:
            yield event.plain_result(result.message)

    async def battle(self, event: AstrMessageEvent):
        """处理战斗指令"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        # 检查是否有缓存的野生宝可梦信息
        wild_pokemon_info: WildPokemonInfo = self.pokemon_service.get_user_encountered_wild_pokemon(user_id)

        if not wild_pokemon_info:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_NOT_ENCOUNTERED.value)
            return

        result = self.adventure_service.adventure_in_battle(user_id, wild_pokemon_info)
        if result['success']:
            yield event.plain_result(result['message'])
        else:
            yield event.plain_result(result['message'])

    async def catch_pokemon(self, event: AstrMessageEvent):
        """处理捕捉野生宝可梦的指令"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        # 检查是否有遇到的野生宝可梦信息（使用PokemonService方法）
        wild_pokemon: WildPokemonInfo = self.pokemon_service.get_user_encountered_wild_pokemon(user_id)
        if not wild_pokemon:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_NOT_ENCOUNTERED.value)
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

        # 计算捕捉成功率
        catch_success_rate = self.adventure_service.calculate_catch_success_rate(user_id, wild_pokemon, item_id)
        if not catch_success_rate['success']:
            yield event.plain_result(catch_success_rate['message'])
            return
        message = f"您尝试捕捉野生的 {wild_pokemon.name} (Lv.{wild_pokemon.level})，捕捉成功率为 {catch_success_rate['data']['success_rate']*100:.2f}%。\n\n"
        # 随机决定捕捉结果
        is_successful = random.random() < catch_success_rate['data']['success_rate']
        pokeball_item = catch_success_rate['data']['pokeball_item']
        # 扣除一个精灵球
        self.plugin.user_repo.add_user_item(user_id, pokeball_item.item_id, -1)

        if is_successful:
            # 成功捕捉 - 将野生宝可梦添加到用户宝可梦列表中
            # 首先创建一个基础的宝可梦记录
            user_pokemon_info: UserPokemonInfo = UserPokemonInfo(
                id=0,
                species_id=wild_pokemon.species_id,
                name=wild_pokemon.name,
                level=wild_pokemon.level,
                exp=wild_pokemon.exp,
                gender=wild_pokemon.gender,
                stats=wild_pokemon.stats,
                ivs=wild_pokemon.ivs,
                evs=wild_pokemon.evs,
                moves=wild_pokemon.moves,
            )
            pokemon_id = self.plugin.user_repo.create_user_pokemon(user_id, user_pokemon_info)

            # 获取新捕捉的宝可梦信息
            new_pokemon:UserPokemonInfo = self.plugin.user_repo.get_user_pokemon_by_id(user_id, pokemon_id)

            message += f"🎉 捕捉成功！\n\n"
            message += f"您成功捕捉到了 {wild_pokemon.name} (Lv.{wild_pokemon.level})！\n\n"
            message += f"已添加到您的宝可梦收藏中。\n\n"
            message += f"宝可梦ID: {new_pokemon.id}\n\n"
            message += f"使用的精灵球: [{pokeball_item.item_id}] {pokeball_item.name_zh}\n\n"
            message += f"剩余精灵球: {pokeball_item.quantity - 1}"

            # 更新野生宝可梦遇到日志 - 标记为已捕捉
            try:
                # 获取最近的野生宝可梦遇到记录（未被捕捉的记录）
                recent_encounters: List[WildPokemonEncounterLog] = self.plugin.pokemon_repo.get_user_encounters(user_id, limit=5)
                encounter_log_id = None
                for encounter in recent_encounters:
                    if (encounter.wild_pokemon_id == wild_pokemon.id and
                        encounter.is_captured == 0):  # 未捕捉的记录
                        encounter_log_id = encounter.id
                        break
                if encounter_log_id:
                    self.plugin.pokemon_repo.update_encounter_log(
                        log_id=encounter_log_id,
                        is_captured=1
                    )
            except Exception as e:
                print(f"更新野生宝可梦遇到日志（捕捉）时出错: {e}")

        else:
            message += f"❌ 捕捉失败！\n\n"
            message += f"{wild_pokemon.name} 逃脱了！\n\n"
            message += f"使用的精灵球: [{pokeball_item.item_id}] {pokeball_item.name_zh}\n\n"
            message += f"剩余精灵球: {pokeball_item.quantity - 1}\n\n"
            message += "你也可以使用 /逃跑 指令离开这只野生宝可梦。"

            # 更新野生宝可梦遇到日志 - 捕捉失败（仍然标记为已交互）
            try:
                # 获取最近的野生宝可梦遇到记录（未被捕捉的记录）
                recent_encounters: List[WildPokemonEncounterLog] = self.plugin.pokemon_repo.get_user_encounters(user_id, limit=5)
                encounter_log_id = None
                for encounter in recent_encounters:
                    if (encounter.wild_pokemon_id == wild_pokemon.id and
                        encounter.is_captured == 0):  # 未捕捉的记录
                        encounter_log_id = encounter.id
                        break
                if encounter_log_id:
                    self.plugin.pokemon_repo.update_encounter_log(
                        log_id=encounter_log_id,
                        is_captured=0  # 捕捉失败
                    )
            except Exception as e:
                print(f"更新野生宝可梦遇到日志（捕捉失败）时出错: {e}")

        yield event.plain_result(message)

    async def run(self, event: AstrMessageEvent):
        """处理逃跑指令"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        user = self.plugin.user_repo.get_user_by_id(user_id)

        if not user:
            yield event.plain_result(AnswerEnum.USER_NOT_REGISTERED.value)
            return

        # 检查是否有遇到的野生宝可梦信息（使用PokemonService方法）
        wild_pokemon = self.pokemon_service.get_user_encountered_wild_pokemon(user_id)

        if not wild_pokemon:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_NOT_ENCOUNTERED.value)
            return

        escape_success_rate = 80

        # 计算逃跑结果（默认80%成功率）
        escape_success = random.random() * 100 < escape_success_rate

        if escape_success:
            message = "🏃 您成功逃跑了！\n\n"
            message += f"野生的 {wild_pokemon.name} 没有追上来。\n"

            # 更新野生宝可梦遇到日志 - 标记为已逃跑
            try:
                # 获取最近的野生宝可梦遇到记录（未被捕捉的记录）
                recent_encounters: List[WildPokemonEncounterLog] = self.plugin.pokemon_repo.get_user_encounters(user_id, limit=5)
                encounter_log_id = None
                for encounter in recent_encounters:
                    if (encounter.wild_pokemon_id == wild_pokemon.id and
                        encounter.is_captured == 0):  # 未捕捉的记录
                        encounter_log_id = encounter.id
                        break
                if encounter_log_id:
                    self.plugin.pokemon_repo.update_encounter_log(
                        log_id=encounter_log_id,
                        isdel=1  # 标记为已删除
                    )
            except Exception as e:
                print(f"更新野生宝可梦遇到日志（逃跑）时出错: {e}")

        else:
            message = "😅 逃跑失败了！\n\n"
            message += f"野生的 {wild_pokemon.name} 还在盯着你...\n"
            message += "你可以再次尝试逃跑，或者选择战斗或捕捉！"

        yield event.plain_result(message)