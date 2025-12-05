import time
import random
from typing import List, Optional, TYPE_CHECKING, Any

from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from data.plugins.astrbot_plugin_pokemon.astrbot_plugin_pokemon.core.models.pokemon_models import UserPokemonInfo
from ...core.models.adventure_models import LocationInfo, AdventureResult, BattleResult
from ...core.models.common_models import BaseResult
from ...core.models.pokemon_models import WildPokemonInfo, UserPokemonInfo, WildPokemonEncounterLog, PokemonStats, PokemonIVs, PokemonEVs, PokemonMoves
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class AdventureHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        # 提取常用 Service，减少 self.plugin.xxx 的调用链长度
        self.user_service = container.user_service
        self.adventure_service = container.adventure_service
        self.pokemon_service = container.pokemon_service
        self.user_pokemon_service = container.user_pokemon_service
        self.team_service = container.team_service
        self.exp_service = container.exp_service
        self.move_service = container.move_service

        self.adventure_cooldown = self.plugin.game_config["adventure"]["cooldown"]

    async def view_locations(self, event: AstrMessageEvent):
        """查看所有可冒险的区域"""
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = await self._check_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        result = self.adventure_service.get_all_locations()
        if not result.success:
            yield event.plain_result(result.message)
            return

        locations: List[LocationInfo] = result.data

        # 优化：使用 join 拼接字符串，比循环 += 更高效且清晰
        lines = [f"🗺️ {AnswerEnum.ADVENTURE_LOCATIONS_FOUND.value.format(count=len(locations))}：\n"]
        for i, loc in enumerate(locations, 1):
            desc = f"   描述: {loc.description}\n" if loc.description != "暂无描述" else ""
            lines.append(
                f"{i}. {loc.name}\n"
                f"   ID: {loc.id} | 等级: {loc.min_level}-{loc.max_level}\n"
                f"{desc}"
            )
        lines.append("💡 使用 冒险 <区域ID> 指令进入冒险！")

        yield event.plain_result("\n".join(lines).strip())

    async def adventure(self, event: AstrMessageEvent):
        """进入指定区域冒险"""
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = await self._check_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        # 1. 检查状态 (是否已遭遇、冷却时间、队伍设置)
        if self.user_pokemon_service.get_user_encountered_wild_pokemon(user_id):
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_ALREADY_ENCOUNTERED.value)
            return

        # 检查是否有当前遭遇的训练家
        if self.user_pokemon_service.get_user_current_trainer_encounter(user_id):
            yield event.plain_result("您当前正在与训练家遭遇中，请先完成当前遭遇（使用 /战斗 或 /逃跑）。")
            return

        user = self.user_service.get_user_by_id(user_id)
        if not user.success:
            yield event.plain_result(user.message)
            return
        user = user.data
        current_time = time.time()
        last_time = user.last_adventure_time if user and user.last_adventure_time else 0
        cooldown_remaining = (last_time + self.adventure_cooldown) - current_time

        if cooldown_remaining > 0:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_COOLDOWN.value.format(cooldown=int(cooldown_remaining)))
            return

        if not self.team_service.get_user_team(user_id).success:
            yield event.plain_result(AnswerEnum.USER_TEAM_NOT_SET.value)
            return

        # 2. 解析参数
        args = event.message_str.split()
        if len(args) < 2:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_LOCATION_NOT_SPECIFIED.value)
            return

        try:
            location_id = int(args[1])
            if location_id <= 0: raise ValueError
        except ValueError:
            yield event.plain_result(AnswerEnum.ADVENTURE_LOCATION_INVALID.value.format(location_id=args[1]))
            return

        # 3. 执行冒险 - 按7:3比例遭遇野生宝可梦和训练家
        result = self.adventure_service.adventure_in_location(user_id, location_id, encounter_npc_only=False)
        if not result.success:
            yield event.plain_result(result.message)
            return

        d: AdventureResult = result.data

        # 4. 成功后处理
        self.user_service.update_user_last_adventure_time(user_id, time.time())  # 更新冷却

        # 检查是否遭遇了训练家
        if d.trainer:
            # 遭遇了训练家
            pokemon_names = [f"{pokemon.name}(Lv.{pokemon.level})" for pokemon in d.trainer.pokemon_list]
            pokemon_list_str = ", ".join(pokemon_names)

            message = (
                f"🌳 在 {d.location.name} 中冒险！\n\n"
                f"⚔️ 遇到了训练家 {d.trainer.trainer.name}！\n\n"
                f"职业: {d.trainer.trainer.trainer_class}\n\n"
                f"宝可梦: {pokemon_list_str}\n\n"
                f"基础赏金: {d.trainer.trainer.base_payout}金币\n\n"
                f"您可以选择：\n\n"
                f"💡 /战斗 - 与训练家战斗\n\n"
                f"🏃 /逃跑 - 逃离战斗"
            )
        else:
            # 遭遇了野生宝可梦
            message = (
                f"🌳 在 {d.location.name} 中冒险！\n\n"
                f"✨ 遇到了野生的 {d.wild_pokemon.name}！\n"
                f"等级: {d.wild_pokemon.level}\n"
                f"{AnswerEnum.ADVENTURE_LOCATION_POKEMON_ENCOUNTERED.value}"
            )

        yield event.plain_result(message)

    async def battle(self, event: AstrMessageEvent):
        """处理战斗指令"""
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = await self._check_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        # 检查是否遭遇了训练家
        trainer_id = self.user_pokemon_service.get_user_current_trainer_encounter(user_id)
        if trainer_id:
            # 与训练家战斗
            # 获取完整的训练家信息
            battle_trainer = self.adventure_service.trainer_service.get_trainer_with_pokemon(trainer_id)
            if not battle_trainer:
                yield event.plain_result("获取训练家信息失败")
                return

            # 获取用户队伍
            user_team_result = self.team_service.get_user_team(user_id)
            if not user_team_result.success or not user_team_result.data or len(user_team_result.data) == 0:
                yield event.plain_result(AnswerEnum.USER_TEAM_NOT_SET.value)
                return

            user_team_data = user_team_result.data
            # 获取队伍宝可梦ID列表
            user_team_list = [pokemon.id for pokemon in user_team_data]
            # 开始训练家战斗
            result = self.adventure_service.start_trainer_battle(user_id, battle_trainer, user_team_list)
            if not result.success:
                yield event.plain_result(result.message)
                return

            # 格式化输出 (逻辑抽取到私有方法)
            message = self._format_battle_result_message(result.data)
            yield event.plain_result(message)

            # 清除当前训练家遭遇
            self.user_pokemon_service.clear_user_current_trainer_encounter(user_id)
        else:
            # 与野生宝可梦战斗
            wild_pokemon_info = self.user_pokemon_service.get_user_encountered_wild_pokemon(user_id)
            if not wild_pokemon_info:
                yield event.plain_result(AnswerEnum.USER_ADVENTURE_NOT_ENCOUNTERED.value)
                return

            # 执行战斗逻辑
            result = self.adventure_service.adventure_in_battle(user_id, wild_pokemon_info)
            if not result.success:
                yield event.plain_result(result.message)
                return

            # 格式化输出 (逻辑抽取到私有方法)
            message = self._format_battle_result_message(result.data)
            yield event.plain_result(message)

    async def view_battle_log(self, event: AstrMessageEvent):
        """查看战斗日志"""
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = await self._check_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        args = event.message_str.split()

        if len(args) < 2 or not args[1].isdigit():
            yield event.plain_result("❌ 请提供有效的战斗日志ID，例如：/查看战斗 1")
            return

        log_id = int(args[1])

        log = self.adventure_service.get_battle_log_by_id(log_id)
        if not log:
            yield event.plain_result("❌ 找不到该战斗日志")
            return

        # 格式化日志详情
        message = [
            f"📜 战斗日志 #{log['id']}\n\n",
            f"时间: {log['created_at']}\n\n",
            f"对手: {log['target_name']}\n\n",
            f"结果: {'胜利' if log['result'] == 'success' else '失败'}\n\n",
        ]

        for i, skirmish in enumerate(log['log_data'], 1):
            message.append(f"=== 第 {i} 场对战 ===\n\n")
            message.append(f"我方: {skirmish['pokemon_name']} (Lv.{skirmish['level']})")
            message.append(f"预测胜率: {skirmish['win_rate']}%\n\n")
            message.append("详细过程:")
            message.extend([f"  {line}" for line in skirmish['details']])
            message.append(f"本场结果: {'胜利' if skirmish['result'] == 'win' else '失败'}\n")

        yield event.plain_result("\n".join(message))

    async def catch_pokemon(self, event: AstrMessageEvent):
        """处理捕捉野生宝可梦的指令"""
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = await self._check_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        wild_pokemon = self.user_pokemon_service.get_user_encountered_wild_pokemon(user_id)
        if not wild_pokemon:
            yield event.plain_result(AnswerEnum.USER_ADVENTURE_NOT_ENCOUNTERED.value)
            return

        # 解析道具ID
        args = event.message_str.split()
        item_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        if len(args) > 1 and not args[1].isdigit():
            yield event.plain_result("❌ 无效的道具ID格式。")
            return

        # 计算概率
        rate_result = self.adventure_service.calculate_catch_success_rate(user_id, wild_pokemon, item_id)
        if not rate_result['success']:
            yield event.plain_result(rate_result['message'])
            return

        data = rate_result['data']
        success_rate = data['success_rate']
        pokeball = data['pokeball_item']

        # 消耗道具
        self.user_service.add_user_item(user_id, pokeball.item_id, -1)

        # 判定结果
        is_success = random.random() < success_rate
        message = f"您尝试捕捉野生的 {wild_pokemon.name} (Lv.{wild_pokemon.level})，成功率 {success_rate * 100:.2f}%。\n\n"

        if is_success:
            # 构造并保存宝可梦
            new_pokemon = self.user_pokemon_service._create_and_save_caught_pokemon(user_id, wild_pokemon)
            self.user_service._update_encounter_log(user_id, wild_pokemon.id, captured=True, deleted=True)

            message += (
                f"🎉 捕捉成功！\n"
                f"已添加 {wild_pokemon.name} 到收藏 (ID: {new_pokemon.id})。\n"
                f"消耗: [{pokeball.item_id}] {pokeball.name_zh} (剩余: {pokeball.quantity - 1})"
            )

        else:
            message += (
                f"❌ 捕捉失败！{wild_pokemon.name} 挣脱了！\n"
                f"消耗: [{pokeball.item_id}] {pokeball.name_zh} (剩余: {pokeball.quantity - 1})\n\n"
                f"你可以继续 /捕捉 或 /逃跑。"
            )

        yield event.plain_result(message)

    async def run(self, event: AstrMessageEvent):
        """处理逃跑指令"""
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = await self._check_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        # 检查是否遭遇了训练家
        trainer_id = self.user_pokemon_service.get_user_current_trainer_encounter(user_id)
        if trainer_id:
            # 逃离训练家遭遇
            if random.random() < 0.9:  # 90% 几率逃跑（对训练家可能更高，因为可能比较困难）
                self.user_pokemon_service.clear_user_current_trainer_encounter(user_id)
                # 获取训练家信息用于显示
                trainer = self.adventure_service.trainer_service.get_trainer_by_id(trainer_id)
                trainer_name = trainer.name if trainer else "未知训练家"
                yield event.plain_result(f"🏃 您成功从训练家 {trainer_name} 身边逃跑了！")
            else:
                # 在这里重新获取训练家信息
                current_trainer = self.adventure_service.trainer_service.get_trainer_by_id(trainer_id)
                yield event.plain_result(f"😅 逃跑失败！训练家 {current_trainer.name if current_trainer and current_trainer.name else '未知训练家'} 挑战了你！\n请选择 /战斗 或再次 /逃跑。")
        else:
            # 逃离野生宝可梦遭遇
            wild_pokemon = self.user_pokemon_service.get_user_encountered_wild_pokemon(user_id)
            if not wild_pokemon:
                yield event.plain_result(AnswerEnum.USER_ADVENTURE_NOT_ENCOUNTERED.value)
                return

            if random.random() < 0.8:  # 80% 几率逃跑
                self.user_service._update_encounter_log(user_id, wild_pokemon.id, deleted=True)
                yield event.plain_result(f"🏃 您成功从 {wild_pokemon.name} 身边逃跑了！")
            else:
                yield event.plain_result(f"😅 逃跑失败！{wild_pokemon.name} 还在盯着你...\n请选择 /战斗 或再次 /逃跑。")

    async def learn_move(self, event: AstrMessageEvent):
        """处理学习新技能指令 (入口)"""
        # 复用之前优化好的代码逻辑
        user_id = userid_to_base32(event.get_sender_id())
        # 统一处理注册检查
        check_res = await self._check_registered(user_id)
        if not check_res.success:
            yield event.plain_result(check_res.message)
            return

        args = event.message_str.split()
        if len(args) == 1:
            async for r in self._handle_show_learnable_moves(event, user_id): yield r
        elif len(args) == 2:
            async for r in self._handle_show_learnable_moves_for_single_pokemon(event, user_id, args): yield r
        elif len(args) >= 3:
            async for r in self._handle_learn_move_action(event, user_id, args): yield r
        else:
            yield event.plain_result("❌ 格式错误！正确格式: /学习技能 [宝可梦ID] [技能ID] [槽位编号(可选)]")

    # ----------------- 私有辅助方法 -----------------

    async def _check_registered(self, user_id) -> BaseResult:
        return self.user_service.check_user_registered(user_id)

    def _format_battle_result_message(self, d: BattleResult) -> str:
        """格式化战斗结果文本"""
        wild = d.wild_pokemon

        if d.is_trainer_battle:
            # 训练家战斗：显示训练家信息而不是野生宝可梦
            lines = [
                "⚔️ 宝可梦对战开始！\n\n",
                # f"训练家: {wild['name']}\n"  # wild['name'] 在训练家战斗中是训练家名称
            ]
        else:
            # 野生宝可梦战斗
            lines = [
                "⚔️ 宝可梦战斗开始！",
                f"野生宝可梦: {wild['name']} (Lv.{wild['level']})\n"
            ]

        if d.battle_log:
            lines.append("👥 参战宝可梦:")
            for i, record in enumerate(d.battle_log, 1):
                res = "获胜" if record['result'] == 'win' else "失败"

                # 检查是否包含对手宝可梦信息（训练家战斗）
                if 'trainer_pokemon_name' in record and record['trainer_pokemon_name']:
                    # 训练家战斗：显示对手宝可梦信息
                    opponent_info = f" vs {record['trainer_pokemon_name']} (Lv.{record['trainer_pokemon_level']})"
                else:
                    # 野生宝可梦战斗：使用野生宝可梦信息
                    opponent_info = f" vs {wild['name']} (Lv.{wild['level']})"

                lines.append(
                    f"  {i}. {record['pokemon_name']} (Lv.{record['level']}){opponent_info} - {res} (胜率:{record['win_rate']}%)")
            lines.append("")

        lines.append(f"🎯 战斗结果: {'胜利' if d.result == 'success' else '失败'}")

        if d.log_id:
            lines.append(f"📜 日志ID: {d.log_id} (使用 /查看战斗 {d.log_id} 查看详情)")

        # 经验值部分
        if d.exp_details and d.exp_details.get("team_pokemon_results"):
            lines.append("\n📈 经验值获取:")
            for res in d.exp_details["team_pokemon_results"]:
                if not res.get("success"): continue

                name = res.get("pokemon_name")
                lines.append(f"  {name} +{res.get('exp_gained')} EXP")

                lvl_info = res.get("level_up_info", {})
                if lvl_info.get("should_level_up"):
                    lines.append(f"  🎉 升级！Lv.{lvl_info['new_level']} (提升 {lvl_info['levels_gained']} 级)")

                    move_res = lvl_info.get("move_learning_result")
                    if move_res and move_res.get("new_moves"):
                        # 格式化为 技能名[ID], 技能名[ID], ...
                        moves_with_ids = ", ".join(f"{m.get('name', '未知')}[{m.get('id')}]"
                                                   for m in move_res['new_moves'])
                        if move_res.get("requires_choice"):
                            lines.append(f"\n\n  ⚡ 领悟新技能: {moves_with_ids} (技能槽已满，请使用 /学习技能)")
                        else:
                            lines.append(f"\n\n  ⚡ 学会新技能: {moves_with_ids}")

                    evolution_info = lvl_info.get("evolution_info")
                    if evolution_info['can_evolve']:
                        print(evolution_info)
                        lines.append(f"\n\n  🔄 可以进化为: {evolution_info['evolved_species_name']} (ID: {evolution_info['evolved_species_id']})")
                lines.append("")

        return "\n".join(lines)

    async def _handle_show_learnable_moves(self, event, user_id):
        """子逻辑：显示宝可梦可学习的技能"""
        result = self.team_service.get_user_team(user_id)
        if not result.success or not result.data:
            yield event.plain_result(AnswerEnum.USER_TEAM_NOT_SET.value)
            return
        user_team = result.data
        message = ["🔍 检查队伍中是否有宝可梦可以学习新技能：\n"]
        has_new_move = False

        for i in user_team:
            pid = i.id
            result = self.user_pokemon_service.get_user_pokemon_by_id(user_id, pid)
            if not result.success or not result.data:
                continue

            p_data: UserPokemonInfo = result.data
            # 获取该宝可梦从1级到当前等级的所有可学习技能
            all_learnable_moves = self.move_service.get_level_up_moves(p_data.species_id, p_data.level)

            # 获取当前已拥有的技能
            current_moves_ids = [getattr(p_data.moves, f"move{i}_id") or 0 for i in range(1, 5)]

            # 过滤掉已拥有的技能
            learnable_moves = [move_id for move_id in all_learnable_moves if move_id not in current_moves_ids and move_id != 0]
            if learnable_moves:
                has_new_move = True
                move_names = [self.move_service.get_move_name_str(mid) for mid in learnable_moves]
                message.append(f"  🌟 {p_data.name} (Lv.{p_data.level}) 可以学习: {', '.join(move_names)}")

        if not has_new_move:
            message.append("  ✅ 没有宝可梦有待学习的新技能！")

        yield event.plain_result("\n".join(message))

    async def _handle_show_learnable_moves_for_single_pokemon(self, event, user_id, args):
        """子逻辑：显示指定宝可梦可以学习的技能"""
        try:
            pokemon_id = int(args[1])
        except ValueError:
            yield event.plain_result("❌ 宝可梦ID必须是数字")
            return

        # 获取指定的宝可梦信息
        result = self.user_pokemon_service.get_user_pokemon_by_id(user_id, pokemon_id)
        if not result.success or not result.data:
            yield event.plain_result("❌ 找不到指定的宝可梦！")
            return

        p_data = result.data

        # 获取该宝可梦从1级到当前等级的所有可学习技能
        all_learnable_moves = self.move_service.get_level_up_moves(p_data.species_id, p_data.level)

        # 获取当前已拥有的技能
        current_moves_ids = [getattr(p_data.moves, f"move{i}_id") or 0 for i in range(1, 5)]

        # 过滤掉已拥有的技能
        learnable_moves = [move_id for move_id in all_learnable_moves if move_id not in current_moves_ids and move_id != 0]

        if learnable_moves:
            move_names = [f"{self.move_service.get_move_name_str(mid)}[{mid}]" for mid in learnable_moves]
            message = [
                f"📖 {p_data.name} (ID: {p_data.id}, Lv.{p_data.level}) 可以学习的技能：\n",
                f"  💫 {', '.join(move_names)}"
            ]
        else:
            message = [
                f"📖 {p_data.name} (ID: {p_data.id}, Lv.{p_data.level}) 当前没有可学习的新技能！\n",
                "  ✅ 所有该等级可学习的技能都已掌握。"
            ]

        yield event.plain_result("\n".join(message))

    async def _handle_learn_move_action(self, event, user_id, args):
        """子逻辑：执行学习技能操作"""
        try:
            pokemon_id = int(args[1])
            move_id = int(args[2])
        except ValueError:
            yield event.plain_result("❌ ID必须是数字")
            return

        result = self.user_pokemon_service.get_user_pokemon_by_id(user_id, pokemon_id)
        if not result.success or not result.data:
            yield event.plain_result("❌ 找不到指定的宝可梦！")
            return

        p_data = result.data

        # 1. 校验合法性
        _, new_moves = self.exp_service.check_learnable_moves(
            p_data.species_id, p_data.level, p_data.level, p_data.moves
        )
        # 允许学习 "新解锁技能" 或者 "当前等级本来就该有的技能"
        if move_id not in new_moves:
            current_lvl_moves = self.move_service.get_level_up_moves(p_data.species_id, p_data.level)
            if move_id not in current_lvl_moves:
                yield event.plain_result(f"❌ {p_data.name} 无法学习这个技能！")
                return

        target_move_name = self.move_service.get_move_name_str(move_id)

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
            updated_moves, success = self.exp_service.add_move_to_pokemon(p_data.moves, move_id)
            if success:
                update_result = self.user_pokemon_service.update_user_pokemon_moves(user_id, p_data.id, updated_moves)
                if update_result.success:
                    yield event.plain_result(f"🎉 {p_data.name} 学会了技能 {target_move_name}！")
                else:
                    yield event.plain_result(f"❌ 更新技能失败: {update_result.message}")
            else:
                yield event.plain_result(f"❌ 添加技能失败！")
            return
        except ValueError:
            # 没有空位 (ValueError: 0 is not in list)
            pass

        # 4. 技能槽已满的处理
        if len(args) < 4:
            # 显示替换菜单
            lines = [f"💥 {p_data.name} 的技能槽已满！请选择要替换的技能：\n"]
            for i, mid in enumerate(current_moves_ids, 1):
                lines.append(f"  技能{i}: {self.move_service.get_move_name_str(mid)}")

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

        update_result = self.user_pokemon_service.update_user_pokemon_moves(user_id, p_data.id, p_data.moves)
        if update_result.success:
            old_move_name = self.move_service.get_move_name_str(old_move_id)
            yield event.plain_result(
                f"✅ {p_data.name} 成功替换技能！\n"
                f"  - 遗忘: {old_move_name}\n"
                f"  - 学会: {target_move_name}"
            )
        else:
            yield event.plain_result(f"❌ 更新技能失败: {update_result.message}")