import random
from typing import List

from astrbot.api.event import AstrMessageEvent
from ...core.models.adventure_models import LocationInfo, AdventureResult, BattleResult
from ...core.models.common_models import BaseResult
from ...core.models.user_models import UserTeam
from ...interface.response.answer_enum import AnswerEnum
from ...core.models.pokemon_models import WildPokemonInfo, UserPokemonInfo, WildPokemonEncounterLog
from ...utils.utils import userid_to_base32


class AdventureHandlers:
    def __init__(self, plugin):
        self.plugin = plugin
        self.user_service = plugin.user_service
        self.adventure_service = plugin.adventure_service
        self.pokemon_service = plugin.pokemon_service
        self.user_pokemon_service = plugin.user_pokemon_service
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
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
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
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_COOLDOWN.value.format(cooldown=int(cooldown_remaining)))
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

        # 验证区域ID格式（确保是正整数）
        if not (location_id > 0):
            yield event.plain_result(AnswerEnum.ADVENTURE_LOCATION_INVALID.value.format(location_id=location_id))
            return

        result = self.adventure_service.adventure_in_location(user_id, location_id)
        if not result.success:
            yield event.plain_result(result.message)
            return
        d: AdventureResult = result.data
        wild_pokemon = d.wild_pokemon
        message = f"🌳 在 {d.location.name} 中冒险！\n\n"
        message += f"✨ 遇到了野生的 {wild_pokemon.name}！\n"
        message += f"等级: {wild_pokemon.level}\n"

        # 记录冒险时间到数据库，用于冷却时间控制
        import time
        current_time = time.time()
        self.plugin.user_repo.update_user_last_adventure_time(user_id, current_time)

        message += (AnswerEnum.ADVENTURE_LOCATION_POKEMON_ENCOUNTERED.value)
        yield event.plain_result(message)


    async def battle(self, event: AstrMessageEvent):
        """处理战斗指令"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
            return

        # 检查是否有缓存的野生宝可梦信息
        wild_pokemon_info: WildPokemonInfo = self.pokemon_service.get_user_encountered_wild_pokemon(user_id)

        if not wild_pokemon_info:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_NOT_ENCOUNTERED.value)
            return

        result = self.adventure_service.adventure_in_battle(user_id, wild_pokemon_info)
        if not result.success:
            yield event.plain_result(result.message)
        if result.success:
            d: BattleResult = result.data
            user_pokemon = d.user_pokemon
            wild_pokemon_data = d.wild_pokemon
            win_rates = d.win_rates
            battle_result = "胜利" if d.result == "success" else "失败"
            exp_details = d.exp_details
            battle_log = d.battle_log if d.battle_log else []  # 获取战斗日志

            message = "⚔️ 宝可梦战斗开始！\n\n"
            message += f"野生宝可梦: {wild_pokemon_data['name']} (Lv.{wild_pokemon_data['level']})\n\n"

            # 显示所有参与战斗的宝可梦
            if battle_log:
                message += "👥 参战宝可梦:\n"
                for i, battle_record in enumerate(battle_log, 1):
                    pokemon_result = "获胜" if battle_record['result'] == 'win' else "失败"
                    message += f"  {i}. {battle_record['pokemon_name']} [{battle_record['pokemon_id']}] (Lv.{battle_record['level']}) - {pokemon_result} (胜率: {battle_record['win_rate']}%)\n"
                message += "\n"

            # message += "📊 战斗胜率分析:\n"
            # message += f"最终我方胜率: {win_rates['user_win_rate']}%\n"
            # message += f"最终野生胜率: {win_rates['wild_win_rate']}%\n\n"

            message += f"🎯 战斗结果: {battle_result}\n"
            if d.log_id and d.log_id > 0:
                message += f"📜 战斗日志已生成，ID: {d.log_id}\n"
                message += f"💡 使用 /查看战斗 {d.log_id} 查看详细战斗过程\n"

            # 添加经验值信息
            if exp_details:
                team_pokemon_results = exp_details.get("team_pokemon_results", [])

                if team_pokemon_results:
                    message += f"\n📈 经验值获取:\n\n"
                    for i, pokemon_result in enumerate(team_pokemon_results):
                        if pokemon_result.get("success"):
                            exp_gained = pokemon_result.get("exp_gained", 0)
                            pokemon_name = pokemon_result.get("pokemon_name", f"宝可梦{i + 1}")
                            pokemon_id = pokemon_result.get("pokemon_id", 0)
                            message += f"  {pokemon_name}[{pokemon_id}] 获得了 {exp_gained} 点经验值\n\n"

                            level_up_info = pokemon_result.get("level_up_info", {})
                            if level_up_info.get("should_level_up"):
                                levels_gained = level_up_info.get("levels_gained", 0)
                                new_level = level_up_info.get("new_level", 0)
                                message += f"  🎉 恭喜 {pokemon_name}[{pokemon_id}] 升级了！等级提升 {levels_gained} 级，现在是 {new_level} 级！\n\n"

                                # 检查是否学习了新技能
                                move_learning_result = level_up_info.get("move_learning_result")
                                if move_learning_result:
                                    new_moves = move_learning_result.get("new_moves", [])
                                    if new_moves:
                                        if move_learning_result.get("requires_choice"):
                                            message += f"  ⚡ {pokemon_name} 可以学习新技能！但技能槽已满，请使用 /学习技能 指令选择替换技能。\n"
                                            for move in new_moves:
                                                message += f"    - {move.get('name', '未知技能')}\n"
                                        else:
                                            message += f"  ⚡ {pokemon_name} 学会了新技能！\n"
                                            for move in new_moves:
                                                message += f"    - {move.get('name', '未知技能')}\n"
                                    else:
                                        message += f"  📚 {pokemon_name} 没有新技能可以学习。\n"
                                message += "\n"
            yield event.plain_result(message)
            return

    async def view_battle_log(self, event: AstrMessageEvent):
        """查看战斗日志"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        args = event.message_str.split()
        if len(args) < 2:
            yield event.plain_result("❌ 请提供战斗日志ID，例如：/查看战斗 1")
            return

        try:
            log_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 无效的战斗日志ID")
            return

        if not self.plugin.battle_repo:
            yield event.plain_result("❌ 战斗日志系统未启用")
            return

        log = self.plugin.battle_repo.get_battle_log_by_id(log_id)
        if not log:
            yield event.plain_result("❌ 找不到该战斗日志")
            return

        # Check permission? Usually logs are public or user specific.
        # If user specific:
        if log['user_id'] != user_id:
            yield event.plain_result("❌ 你只能查看自己的战斗日志")
            return
        # For now, let's allow viewing any log if they have the ID.

        message = f"📜 战斗日志 #{log['id']}\n\n"
        message += f"时间: {log['created_at']}\n\n"
        message += f"对手: {log['target_name']}\n\n"
        message += f"结果: {'胜利' if log['result'] == 'success' else '失败'}\n\n"

        log_data = log['log_data']
        # log_data is a list of skirmishes
        for i, skirmish in enumerate(log_data, 1):
            message += f"=== 第 {i} 场对战 ===\n\n"
            message += f"我方: {skirmish['pokemon_name']} (Lv.{skirmish['level']})\n\n"
            message += f"胜率预测: {skirmish['win_rate']}%\n\n"
            message += "详细过程:\n\n"
            for line in skirmish['details']:
                message += f"  {line}\n\n"
            message += f"结果: {'胜利' if skirmish['result'] == 'win' else '失败'}\n\n"

        yield event.plain_result(message)

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

            # # 更新野生宝可梦遇到日志 - 捕捉失败（仍然标记为已交互）
            # try:
            #     # 获取最近的野生宝可梦遇到记录（未被捕捉的记录）
            #     recent_encounters: List[WildPokemonEncounterLog] = self.plugin.pokemon_repo.get_user_encounters(user_id, limit=5)
            #     encounter_log_id = None
            #     for encounter in recent_encounters:
            #         if (encounter.wild_pokemon_id == wild_pokemon.id and
            #             encounter.is_captured == 0):  # 未捕捉的记录
            #             encounter_log_id = encounter.id
            #             break
            #     if encounter_log_id:
            #         self.plugin.pokemon_repo.update_encounter_log(
            #             log_id=encounter_log_id,
            #             is_captured=0  # 捕捉失败
            #         )
            # except Exception as e:
            #     print(f"更新野生宝可梦遇到日志（捕捉失败）时出错: {e}")

        yield event.plain_result(message)

    async def run(self, event: AstrMessageEvent):
        """处理逃跑指令"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        result = self.user_service.check_user_registered(user_id)
        if not result.success:
            yield event.plain_result(result.message)
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


    async def learn_move(self, event: AstrMessageEvent):
        """处理学习新技能的指令 (主入口)"""
        user_id = userid_to_base32(self.plugin._get_effective_user_id(event))
        check_result = self.user_service.check_user_registered(user_id)
        if not check_result.success:
            yield event.plain_result(check_result.message)
            return

        args = event.message_str.split()

        # 路由分发
        if len(args) == 1:
            async for res in self._handle_show_learnable_moves(event, user_id):
                yield res
        elif len(args) >= 3:
            async for res in self._handle_learn_move_action(event, user_id, args):
                yield res
        # --- 修正点结束 ---
        else:
            yield event.plain_result("❌ 格式错误！正确格式: /学习技能 [宝可梦ID] [技能ID] [槽位编号(可选)]")

    # ----------------- 辅助方法 -----------------

    def _get_move_name_str(self, move_id: int) -> str:
        """辅助函数：安全获取技能名称"""
        if not move_id:
            return "未知技能"
        move_info = self.plugin.move_repo.get_move_by_id(move_id)
        return move_info['name_zh'] if move_info else f"技能{move_id}"

    async def _handle_show_learnable_moves(self, event, user_id):
        """子逻辑：显示队伍中可学习的技能"""
        user_team = self.plugin.team_repo.get_user_team(user_id)
        if not user_team:
            yield event.plain_result(AnswerEnum.USER_TEAM_NOT_SET.value)
            return

        message = ["🔍 检查队伍中是否有宝可梦可以学习新技能：\n"]
        has_new_move = False

        # 使用列表推导式获取非空的宝可梦ID
        pokemon_ids = [getattr(user_team, f"pokemon{i}_id") for i in range(1, 7)]
        valid_ids = [pid for pid in pokemon_ids if pid]

        for pid in valid_ids:
            p_data = self.plugin.user_repo.get_user_pokemon_by_id(user_id, pid)
            if not p_data: continue

            _, new_moves = self.plugin.exp_service._check_and_learn_new_moves(
                p_data.species_id, p_data.level, p_data.level, p_data.moves
            )

            if new_moves:
                has_new_move = True
                move_names = [self._get_move_name_str(mid) for mid in new_moves]
                message.append(f"  🌟 {p_data.name} (Lv.{p_data.level}) 可以学习: {', '.join(move_names)}")

        if not has_new_move:
            message.append("  ✅ 没有宝可梦有待学习的新技能！")

        yield event.plain_result("\n".join(message))

    async def _handle_learn_move_action(self, event, user_id, args):
        """子逻辑：执行学习技能操作"""
        try:
            pokemon_id = int(args[1])
            move_id = int(args[2])
        except ValueError:
            yield event.plain_result("❌ ID必须是数字")
            return

        p_data = self.plugin.user_repo.get_user_pokemon_by_id(user_id, pokemon_id)
        if not p_data:
            yield event.plain_result("❌ 找不到指定的宝可梦！")
            return

        # 1. 校验合法性
        _, new_moves = self.plugin.exp_service._check_and_learn_new_moves(
            p_data.species_id, p_data.level, p_data.level, p_data.moves
        )
        # 允许学习 "新解锁技能" 或者 "当前等级本来就该有的技能"
        if move_id not in new_moves:
            current_lvl_moves = self.plugin.move_repo.get_level_up_moves(p_data.species_id, p_data.level)
            if move_id not in current_lvl_moves:
                yield event.plain_result(f"❌ {p_data.name} 无法学习这个技能！")
                return

        target_move_name = self._get_move_name_str(move_id)

        # 2. 获取当前技能状态
        # current_moves_ids 示例: [10, 20, 0, 0] (0代表空槽位)
        current_moves_ids = [getattr(p_data.moves, f"move{i}_id") or 0 for i in range(1, 5)]

        if move_id in current_moves_ids:
            yield event.plain_result(f"❌ {p_data.name} 已经拥有技能 {target_move_name}，不能重复学习！")
            return

        # 3. 寻找空槽位
        try:
            empty_slot_index = current_moves_ids.index(0)  # 找到第一个为0的索引 (0-3)
            # 有空位，直接学习
            updated_moves = self.plugin.exp_service._add_move_to_pokemon(p_data.moves, move_id)[0]
            self.plugin.pokemon_repo.update_pokemon_moves(updated_moves, p_data.id, user_id)
            yield event.plain_result(f"🎉 {p_data.name} 学会了技能 {target_move_name}！")
            return
        except ValueError:
            # 没有空位 (ValueError: 0 is not in list)
            pass

        # 4. 技能槽已满的处理
        if len(args) < 4:
            # 显示替换菜单
            lines = [f"💥 {p_data.name} 的技能槽已满！请选择要替换的技能：\n"]
            for i, mid in enumerate(current_moves_ids, 1):
                lines.append(f"  技能{i}: {self._get_move_name_str(mid)}")

            lines.append(f"\n💡 替换指令: /学习技能 {pokemon_id} {move_id} <槽位1-4>")
            yield event.plain_result("\n".join(lines))
            return

        # 5. 执行替换逻辑
        try:
            slot_num = int(args[3])
            if not (1 <= slot_num <= 4): raise ValueError
        except ValueError:
            yield event.plain_result("❌ 槽位编号必须是1-4！")
            return

        old_move_id = getattr(p_data.moves, f"move{slot_num}_id")
        if old_move_id == move_id:
            yield event.plain_result(f"❌ 该槽位已经是 {target_move_name}！")
            return

        # 动态设置属性
        setattr(p_data.moves, f"move{slot_num}_id", move_id)

        self.plugin.pokemon_repo.update_pokemon_moves(p_data.moves, p_data.id, user_id)

        old_move_name = self._get_move_name_str(old_move_id)
        yield event.plain_result(
            f"✅ {p_data.name} 成功替换技能！\n"
            f"  - 遗忘: {old_move_name}\n"
            f"  - 学会: {target_move_name}"
        )