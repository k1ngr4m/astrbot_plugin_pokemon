import random
from typing import List, Tuple, Dict, Any, Optional, Protocol
from dataclasses import dataclass, field

from astrbot.api import logger
from ..models.adventure_models import BattleContext, BattleMoveInfo
from .stat_modifier_service import StatModifierService, StatID


# --- 基础协议与数据类 ---

class BattleLogger(Protocol):
    def log(self, message: str): ...

    def should_log_details(self) -> bool: ...


class ListBattleLogger:
    def __init__(self, log_details: bool = False):
        self.logs = []
        self._log_details = log_details

    def log(self, message: str): self.logs.append(message)

    def should_log_details(self) -> bool: return self._log_details


class NoOpBattleLogger:
    def log(self, message: str): pass

    def should_log_details(self) -> bool: return False


@dataclass
class BattleState:
    """战斗状态快照"""
    context: BattleContext
    current_hp: int
    current_pps: List[int]
    stat_levels: Dict[int, int] = field(default_factory=dict)

    # --- 重构部分 ---
    # 不再为每个技能单独设字段，而是用通用字段记录当前蓄力状态
    # None表示未蓄力，存储move_id表示正在该技能的蓄力回合
    charging_move_id: Optional[int] = None

    # 记录特殊的保护状态类型 (如: 'underground', 'flying', 'diving')
    # 用于判定攻击是否能命中
    protection_status: Optional[str] = None
    # ----------------

    @classmethod
    def from_context(cls, context: BattleContext) -> 'BattleState':
        return cls(
            context=context,
            current_hp=context.current_hp,
            current_pps=[m.current_pp for m in context.moves],
            stat_levels={}
        )


@dataclass
class MoveOutcome:
    """计算结果容器：包含伤害和将要发生的所有效果"""
    damage: int = 0
    missed: bool = False
    is_crit: bool = False
    effectiveness: float = 1.0
    meta_effects: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True  # 用于 OHKO 等特殊判定


# --- 核心逻辑类 ---

class BattleLogic:
    # --- 1. 常量定义 (易维护区) ---
    TRAINER_ENCOUNTER_RATE = 0.3
    CRIT_RATE = 0.0625
    STRUGGLE_MOVE_ID = -1
    SELF_DESTRUCT_ID = 120

    # --- Target ID 常量定义 ---
    # 2: Opponent, 8: All Opponents, 9: Random Opponent, 10: Selected, 11: All Opponents, 14: All Pokemon
    TARGETS_OPPONENT = {2, 8, 9, 10, 11, 14}

    # 3: Selected(User), 4: User, 5: All Users, 7: User(Random), 13: User+Allies, 15: User+Allies
    TARGETS_USER = {3, 4, 5, 7, 13, 15}

    # 属性映射
    TYPE_NAME_MAPPING = {
        '一般': 'normal', 'normal': 'normal', '火': 'fire', 'fire': 'fire',
        '水': 'water', 'water': 'water', '电': 'electric', 'electric': 'electric',
        '草': 'grass', 'grass': 'grass', '冰': 'ice', 'ice': 'ice',
        '格斗': 'fighting', 'fighting': 'fighting', '毒': 'poison', 'poison': 'poison',
        '地面': 'ground', 'ground': 'ground', '飞行': 'flying', 'flying': 'flying',
        '超能力': 'psychic', 'psychic': 'psychic', '虫': 'bug', 'bug': 'bug',
        '岩石': 'rock', 'rock': 'rock', '幽灵': 'ghost', 'ghost': 'ghost',
        '龙': 'dragon', 'dragon': 'dragon', '恶': 'dark', 'dark': 'dark',
        '钢': 'steel', 'steel': 'steel', '妖精': 'fairy', 'fairy': 'fairy'
    }

    # 属性克制表 (完整版建议放在独立JSON或Config文件，此处保留核心)
    TYPE_CHART = {
        'normal': {'rock': 0.5, 'ghost': 0.0, 'steel': 0.5},
        'fire': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 2.0, 'bug': 2.0, 'rock': 0.5, 'dragon': 0.5,
                 'steel': 2.0},
        'water': {'fire': 2.0, 'water': 0.5, 'grass': 0.5, 'ground': 2.0, 'rock': 2.0, 'dragon': 0.5},
        'electric': {'water': 2.0, 'electric': 0.5, 'grass': 0.5, 'ground': 0.0, 'flying': 2.0, 'dragon': 0.5},
        'grass': {'fire': 0.5, 'water': 2.0, 'grass': 0.5, 'poison': 0.5, 'ground': 2.0, 'flying': 0.5, 'bug': 0.5,
                  'rock': 2.0, 'dragon': 0.5, 'steel': 0.5},
        'ice': {'fire': 0.5, 'water': 0.5, 'grass': 2.0, 'ice': 0.5, 'ground': 2.0, 'flying': 2.0, 'dragon': 2.0,
                'steel': 0.5},
        'fighting': {'normal': 2.0, 'ice': 2.0, 'poison': 0.5, 'flying': 0.5, 'psychic': 0.5, 'bug': 0.5, 'rock': 2.0,
                     'ghost': 0.0, 'dark': 2.0, 'steel': 2.0, 'fairy': 0.5},
        'poison': {'grass': 2.0, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'ghost': 0.5, 'steel': 0.0, 'fairy': 2.0},
        'ground': {'fire': 2.0, 'electric': 2.0, 'grass': 0.5, 'poison': 2.0, 'flying': 0.0, 'bug': 0.5, 'rock': 2.0,
                   'steel': 2.0},
        'flying': {'electric': 0.5, 'grass': 2.0, 'fighting': 2.0, 'bug': 2.0, 'rock': 0.5, 'steel': 0.5},
        'psychic': {'fighting': 2.0, 'poison': 2.0, 'psychic': 0.5, 'dark': 0.0, 'steel': 0.5},
        'bug': {'fire': 0.5, 'grass': 2.0, 'fighting': 0.5, 'poison': 0.5, 'flying': 0.5, 'psychic': 2.0, 'ghost': 0.5,
                'dark': 2.0, 'steel': 0.5, 'fairy': 0.5},
        'rock': {'fire': 2.0, 'ice': 2.0, 'fighting': 0.5, 'ground': 0.5, 'flying': 2.0, 'bug': 2.0, 'steel': 0.5},
        'ghost': {'normal': 0.0, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5},
        'dragon': {'dragon': 2.0, 'steel': 0.5, 'fairy': 0.0},
        'dark': {'fighting': 0.5, 'psychic': 2.0, 'ghost': 2.0, 'dark': 0.5, 'fairy': 0.5},
        'steel': {'fire': 0.5, 'water': 0.5, 'electric': 0.5, 'ice': 2.0, 'rock': 2.0, 'steel': 0.5, 'fairy': 2.0},
        'fairy': {'fighting': 2.0, 'poison': 0.5, 'bug': 0.5, 'dragon': 2.0, 'dark': 2.0, 'steel': 0.5}
    }

    # 状态与异常映射
    STAT_NAMES = {
        1: "HP", 2: "攻击", 3: "防御", 4: "特攻", 5: "特防",
        6: "速度", 7: "命中", 8: "闪避"
    }

    AILMENT_MAP = {
        1: "paralysis", 2: "sleep", 3: "freeze", 4: "burn", 5: "poison",
        6: "confusion", 12: "torment", 13: "disable", 14: "yawn"
    }

    # 中文状态名称映射
    AILMENT_CHINESE_MAP = {
        1: "麻痹", 2: "睡眠", 3: "冰冻", 4: "灼伤", 5: "中毒",
        6: "混乱", 12: "挑衅", 13: "技能封印", 14: "瞌睡"
    }

    def __init__(self, move_repo=None):
        self.stat_modifier_service = StatModifierService()
        self.move_repo = move_repo
        if move_repo and hasattr(move_repo, 'move_repo'):
            self.move_service = move_repo
        else:
            self.move_service = None
        self._struggle_move = self._create_struggle_move()

        # --- 两回合蓄力技能配置表 ---
        # key: move_id
        # msg_charge: 第一回合蓄力时的提示语
        # msg_release: 第二回合释放后的提示语 (可选)
        # protect_type: 第一回合获得的保护类型 (underground/flying/diving/bouncing/bounced/None)
        # stat_boost: 第一回合提升的能力 (可选, 格式同 stat_changes)
        # turn_2_boost: 第二回合提升的能力 (如大地掌控)
        # bypass_protect: 第二回合攻击时是否穿透保护 (如暗影潜袭)
        self.TWO_TURN_MOVES_CONFIG = {
            19: {  # 飞翔 (Fly)
                "msg_charge": "飞上了天空！",
                "msg_release": "从天空中下来了！",
                "protect_type": "flying"
            },
            84: {  # 飞天 (Fly，可能是另一个ID)
                "msg_charge": "飞到了天上！",
                "msg_release": "从天空中下来了！",
                "protect_type": "flying"
            },
            76: {  # 日光束 (Solar Beam)
                "msg_charge": "收集满满的日光！",
                "msg_release": "发射了光束！"
            },
            91: {  # 挖洞 (Dig)
                "msg_charge": "挖洞潜入了地下！",
                "msg_release": "从地下钻出来了！",
                "protect_type": "underground"
            },
            90: {  # 潜水 (Dive) - 另一个ID
                "msg_charge": "潜入了水下！",
                "msg_release": "从水中浮上来了！",
                "protect_type": "diving"
            },
            130: {  # 火箭头锤 (Skull Bash)
                "msg_charge": "把头缩进去，防御提高了！",
                "msg_release": "收回了缩进的头！",
                "stat_boost": [{'stat_id': 3, 'change': 1}],  # 防御+1
            },
            291: { # 潜水 (Dive)
                "msg_charge": "潜入了水中！",
                "msg_release": "从水中浮上来了！",
                "protect_type": "diving"
            },
            340: {  # 弹跳 (Bounce)
                "msg_charge": "弹跳到高高的空中！",
                "msg_release": "从高空中降落！",
                "protect_type": "flying"  # 类似飞行
            },
            467: { # 暗影潜袭 (Shadow Force)
                "msg_charge": "消失踪影！",
                "msg_release": "从阴影中现身！",
                "protect_type": "vanished",
                "bypass_protect": True # 可以击中保护
            },
            566: { # 潜灵奇袭 (Phantom Force)
                "msg_charge": "消失在某处！",
                "msg_release": "从某处现身！",
                "protect_type": "vanished",
                "bypass_protect": True
            },
            601: { # 大地掌控 (Geomancy)
                "msg_charge": "吸收能量！",
                "msg_release": "完成了能量吸收！",
                # 注意：大地掌控是第二回合加属性，这个比较特殊，可以在通用逻辑里特判
                "turn_2_boost": [{'stat_id': 4, 'change': 1}, {'stat_id': 5, 'change': 1}, {'stat_id': 6, 'change': 1}] # 特攻+1, 特防+1, 速度+1
            },
            669: {  # 日光刃 (Solar Blade)
                "msg_charge": "收集满满的日光！",
                "msg_release": "用剑攻击了！"
            },
            800: {  # 流星光束 (Meteor Beam)
                "msg_charge": "聚集宇宙之力，特攻提高了！",
                "msg_release": "发射了流星光束！",
                "stat_boost": [{'stat_id': 4, 'change': 1}]  # 特攻+1
            },
        }
        # 定义哪些技能可以击中特定的保护状态
        # key: protect_type, value: list of move_ids that can hit
        self.PROTECTION_PENETRATION = {
            "underground": [89, 1000],        # 地震(89)等
            "flying": [87, 1001],            # 打雷(87)等
            "diving": [1002],                # 冲浪等
            "bounced": [89],                 # 弹跳状态被地震击中
        }

    def _is_type(self, type_raw: str, target_type_en: str) -> bool:
        """判断输入的类型是否属于目标类型（自动处理中英文映射）"""
        mapped = self.TYPE_NAME_MAPPING.get(type_raw, type_raw.lower())
        return mapped == target_type_en

    def _create_struggle_move(self) -> BattleMoveInfo:
        return BattleMoveInfo(
            power=40, accuracy=100.0, type_name='normal', damage_class_id=2,
            priority=0, type_effectiveness=1.0, stab_bonus=1.0,
            max_pp=10, current_pp=10, move_id=self.STRUGGLE_MOVE_ID, move_name="挣扎",
            meta_category_id=0  # 视为普通伤害
        )

    def get_struggle_move(self) -> BattleMoveInfo:
        return self._struggle_move

    # --- 2. 公共接口 (对外逻辑) ---

    def process_turn(self, user_state: BattleState, wild_state: BattleState, logger_obj: BattleLogger) -> bool:
        """处理一个完整回合。如果战斗结束返回 True。"""
        # 1. AI 决策
        u_move = self.get_best_move(user_state, wild_state, logger_obj)
        w_move = self.get_best_move(wild_state, user_state, logger_obj)

        # 2. 速度判定
        user_first = self._is_user_first(user_state, wild_state, u_move, w_move)
        first = (user_state, wild_state, u_move) if user_first else (wild_state, user_state, w_move)
        second = (wild_state, user_state, w_move) if user_first else (user_state, wild_state, u_move)

        # 3. 执行行动
        if self._execute_action(first[0], first[1], first[2], logger_obj): return True
        if self._execute_action(second[0], second[1], second[2], logger_obj): return True

        return False

    def get_best_move(self, attacker_state: BattleState, defender_state: BattleState,
                      logger_obj: Optional[BattleLogger] = None) -> BattleMoveInfo:
        """智能选择最佳技能"""
        attacker_ctx = attacker_state.context
        current_pps = attacker_state.current_pps

        # 筛选可用技能
        available_moves = [
            m for i, m in enumerate(attacker_ctx.moves) if current_pps[i] > 0
        ]

        if not available_moves:
            if logger_obj and logger_obj.should_log_details():
                logger.info("[DEBUG] 没有可用招式，使用挣扎")
            return self.get_struggle_move()

        # 评分与选择
        best_move = None
        best_score = -999.0

        for move in available_moves:
            # 特殊逻辑：自爆独立加分
            if move.move_id == self.SELF_DESTRUCT_ID:
                score = self._calculate_self_destruct_score(attacker_state, defender_state, move, logger_obj)
            else:
                score = self._calculate_unified_move_score(attacker_state, defender_state, move, logger_obj)

            # 增加随机抖动
            score += random.uniform(0, 3)

            if logger_obj and logger_obj.should_log_details():
                logger.info(f"[DEBUG] {move.move_name} (Cat:{move.meta_category_id}) 评分: {score:.2f}")

            if score > best_score:
                best_score = score
                best_move = move

        return best_move if best_move else random.choice(available_moves)

    # --- 3. 执行层 (控制器) ---

    def _execute_action(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                        logger_obj: BattleLogger) -> bool:
        """执行单次行动。返回战斗是否结束。"""
        is_struggle = (move.move_id == self.STRUGGLE_MOVE_ID)
        move_config = self.TWO_TURN_MOVES_CONFIG.get(move.move_id)

        # 添加调试日志
        if logger_obj.should_log_details():
            logger.info(f"[DEBUG] 开始执行行动: {attacker.context.pokemon.name} 使用 {move.move_name} (ID: {move.move_id})")
            logger.info(f"[DEBUG] 攻击方当前状态: charging_move_id={attacker.charging_move_id}, protection_status={attacker.protection_status}")
            logger.info(f"[DEBUG] 防御方当前状态: charging_move_id={defender.charging_move_id}, protection_status={defender.protection_status}")
            logger.info(f"[DEBUG] 技能配置: {move_config}")

        # --- Phase 1: 蓄力状态检查 (Charging Check) ---

        # 如果当前正在蓄力，且使用的就是蓄力技能 -> 说明是第二回合，准备攻击
        if attacker.charging_move_id == move.move_id:
            # 清除蓄力状态
            attacker.charging_move_id = None
            attacker.protection_status = None
            # (注意：此时不return，继续向下执行伤害计算)

            # 特殊处理：大地掌控在第二回合提升能力
            if move_config and "turn_2_boost" in move_config:
                attacker.stat_levels = attacker.stat_levels or {}
                _, new_levels = self.stat_modifier_service.apply_stat_changes(
                    attacker.context.pokemon.stats, move_config["turn_2_boost"], attacker.stat_levels)
                attacker.stat_levels = new_levels
                logger_obj.log(f"{attacker.context.pokemon.name}的能力提升了！\n\n")

                # 添加调试日志
                if logger_obj.should_log_details():
                    logger.info(f"[DEBUG] 大地掌控第二回合提升能力: {move_config['turn_2_boost']}")

        # 如果当前没有蓄力，但是使用了蓄力技能 -> 说明是第一回合，进入蓄力
        elif move_config:
            # 1. 设置状态
            attacker.charging_move_id = move.move_id
            attacker.protection_status = move_config.get("protect_type")

            # 2. 扣除PP & 日志
            pp_str = self._get_pp_str(attacker, move)
            logger_obj.log(f"{attacker.context.pokemon.name} 使用了 {move.move_name}{pp_str}！\n\n")
            logger_obj.log(f"{attacker.context.pokemon.name} {move_config['msg_charge']}\n\n")

            # 添加调试日志
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 攻击方开始蓄力: charging_move_id={attacker.charging_move_id}, protection_status={attacker.protection_status}")

            if not is_struggle: self._deduct_pp(attacker, move)

            # 3. 应用第一回合的属性提升 (如流星光束、火箭头锤)
            if "stat_boost" in move_config:
                attacker.stat_levels = attacker.stat_levels or {}
                _, new_levels = self.stat_modifier_service.apply_stat_changes(
                    attacker.context.pokemon.stats, move_config["stat_boost"], attacker.stat_levels)
                attacker.stat_levels = new_levels
                logger_obj.log(f"{attacker.context.pokemon.name}的能力提升了！\n\n")

                # 添加调试日志
                if logger_obj.should_log_details():
                    logger.info(f"[DEBUG] 第一回合蓄力技能提升能力: {move_config['stat_boost']}")

            return False  # 第一回合结束，不造成伤害

        # --- Phase 2: 命中与保护判定 (Protection Check) ---

        # 检查防御方是否处于无敌/特殊保护状态
        if defender.protection_status:
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 防御方处于保护状态: {defender.protection_status}")

            can_hit = False

            # 1. 技能本身是否无视保护 (如暗影潜袭)
            if move_config and move_config.get("bypass_protect"):
                can_hit = True
                if logger_obj.should_log_details():
                    logger.info(f"[DEBUG] 技能可以穿透保护 (bypass_protect=True)")

            # 2. 技能属性是否克制该保护状态 (如地震打挖洞)
            allowed_moves = self.PROTECTION_PENETRATION.get(defender.protection_status, [])
            if move.move_id in allowed_moves:
                can_hit = True
                if logger_obj.should_log_details():
                    logger.info(f"[DEBUG] 技能可以穿透保护 (在穿透列表中)")

            if not can_hit:
                if logger_obj.should_log_details():
                    logger.info(f"[DEBUG] 攻击未能命中处于保护状态的防御方")

                if not is_struggle: self._deduct_pp(attacker, move)
                logger_obj.log(f"{attacker.context.pokemon.name} 使用了 {move.move_name}！\n\n")
                logger_obj.log("但是没有击中目标！\n\n")
                return False
            else:
                if logger_obj.should_log_details():
                    logger.info(f"[DEBUG] 攻击成功穿透保护")

        # D. 准备日志信息
        # 只有非蓄力技能或者是蓄力技能的第二回合才会走到这里
        # 补一条日志：如果是蓄力技能释放
        if move_config and "msg_release" in move_config:
             logger_obj.log(f"{attacker.context.pokemon.name} {move_config['msg_release']}\n\n")
        elif not move_config:
             # 普通技能日志
             pp_str = self._get_pp_str(attacker, move)
             logger_obj.log(f"{attacker.context.pokemon.name} 使用了 {move.move_name}{pp_str}！\n\n")

        # B. 消耗 PP
        if not is_struggle:
            self._deduct_pp(attacker, move)

        # E. 计算结果 (Calculate)
        # 此步骤只计算数据，不修改任何状态
        if logger_obj.should_log_details():
            logger.info(f"[DEBUG] 开始计算招式结果: {move.move_name}")
        outcome = self._calculate_move_outcome(attacker, defender, move)
        if logger_obj.should_log_details():
            logger.info(f"[DEBUG] 招式结果计算完成: 伤害={outcome.damage}, 命中={not outcome.missed}, 暴击={outcome.is_crit}, 效果={outcome.effectiveness}x")

        # F. 应用结果 (Apply)

        # 1. 命中判定
        if outcome.missed:
            # 只有非OHKO的未命中才显示"没有击中"
            # OHKO的未命中在meta_effects里处理了
            if move.meta_category_id != 9:
                logger_obj.log("没有击中目标！\n\n")

        # 2. 伤害判定 (如果有伤害)
        if outcome.damage > 0:
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 造成伤害: {outcome.damage} 点, 防御方HP从 {defender.current_hp} 变为 {max(0, defender.current_hp - outcome.damage)}")

            defender.current_hp -= outcome.damage
            if is_struggle:
                logger_obj.log(f"{attacker.context.pokemon.name} 使用了挣扎！（PP耗尽）\n\n")
            logger_obj.log(f"造成 {outcome.damage} 点伤害。\n\n")

            # 效果拔群等提示
            if outcome.is_crit:
                logger_obj.log("击中要害！\n\n")
                if logger_obj.should_log_details():
                    logger.info("[DEBUG] 触发暴击")
            if outcome.effectiveness > 1.0:
                logger_obj.log("效果绝佳！\n\n")
                if logger_obj.should_log_details():
                    logger.info("[DEBUG] 效果绝佳")
            elif outcome.effectiveness == 0.0:
                logger_obj.log("似乎没有效果！\n\n")
                if logger_obj.should_log_details():
                    logger.info("[DEBUG] 技能对目标无效")
            elif outcome.effectiveness < 1.0:
                logger_obj.log("效果不佳！\n\n")
                if logger_obj.should_log_details():
                    logger.info("[DEBUG] 效果不佳")

        # 3. 应用特效 (Meta Effects)
        # 包括：异常状态、能力变化、回复、吸血、反伤、一击必杀
        if logger_obj.should_log_details():
            logger.info(f"[DEBUG] 开始应用特效: {len(outcome.meta_effects)} 个效果")

        self._log_meta_effects(attacker, defender, outcome.meta_effects, logger_obj)
        self._apply_meta_effect_changes(attacker, defender, outcome.meta_effects)

        if logger_obj.should_log_details():
            # 记录属性变化
            if any(e.get('type') == 'stat_change' for e in outcome.meta_effects):
                logger.info(f"[DEBUG] 应用属性变化后 - 攻击方属性等级: {attacker.stat_levels}, 防御方属性等级: {defender.stat_levels}")

        # 4. 应用额外属性变化 (Residual Stat Changes)
        # 处理那些虽然是攻击技能，但带有额外属性变化的情况
        if move.move_id > 0 and move.stat_changes and move.meta_category_id not in [2, 6, 7]:
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 应用额外属性变化 - 技能 {move.move_name} 的 stat_changes: {move.stat_changes}")
            self._apply_residual_stat_changes(attacker, defender, move, logger_obj)
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 额外属性变化应用后 - 攻击方属性等级: {attacker.stat_levels}, 防御方属性等级: {defender.stat_levels}")

        # G. 特殊逻辑处理

        # 1. 挣扎反伤
        if is_struggle:
            recoil = max(1, attacker.context.pokemon.stats.hp // 4)
            old_hp = attacker.current_hp
            attacker.current_hp -= recoil
            logger_obj.log(f"{attacker.context.pokemon.name} 因挣扎受到 {recoil} 点反作用伤害！\n\n")
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 挣扎反伤: HP从 {old_hp} 变为 {attacker.current_hp} (减少 {recoil} 点)")

        # 2. 自爆逻辑
        if move.move_id == self.SELF_DESTRUCT_ID:
            old_hp = attacker.current_hp
            attacker.current_hp = 0
            logger_obj.log(f"{attacker.context.pokemon.name} 发生了爆炸，因此倒下了！\n\n")
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 自爆逻辑: HP从 {old_hp} 变为 {attacker.current_hp} (减少 {old_hp} 点)")

        # H. 胜负判定
        if attacker.current_hp <= 0:
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 攻击方 {attacker.context.pokemon.name} HP归零，战斗结束")
            # logger_obj.log(f"{attacker.context.pokemon.name} 倒下了！\n\n") # 交给外部或最后统一显示
            return True
        if defender.current_hp <= 0:
            if logger_obj.should_log_details():
                logger.info(f"[DEBUG] 防御方 {defender.context.pokemon.name} HP归零，战斗结束")
            logger_obj.log(f"{defender.context.pokemon.name} 倒下了！\n\n")
            return True

        if logger_obj.should_log_details():
            logger.info(f"[DEBUG] 回合结束，攻击方HP: {attacker.current_hp}, 防御方HP: {defender.current_hp}")

        return False

    # --- 4. 计算层 (业务逻辑) ---

    def _calculate_move_outcome(self, attacker: BattleState, defender: BattleState,
                                move: BattleMoveInfo) -> MoveOutcome:
        """核心计算函数：计算伤害和生成特效"""
        outcome = MoveOutcome()

        # 1. 命中判定 (OHKO 除外)
        if move.meta_category_id != 9:
            if random.random() * 100 > move.accuracy:
                outcome.missed = True
                return outcome

        # 2. 基础伤害计算
        # 注意：即使是 Status Move (Power=0)，下面的公式计算出 damage=2，但后续 meta logic 会决定是否使用
        base_dmg, eff, is_crit = self._calculate_base_damage_params(attacker, defender, move)
        outcome.effectiveness = eff
        outcome.is_crit = is_crit

        # 如果是攻击类技能 (Category 0, 4, 6, 7, 8, 9)，计算最终伤害
        # 注意 Category 9 (OHKO) 在 resolve_meta 里覆盖伤害
        DAMAGING_CATEGORIES = [0, 4, 6, 7, 8]
        if move.meta_category_id in DAMAGING_CATEGORIES or (move.power > 0 and move.meta_category_id == 0):
            outcome.damage = int(base_dmg)

        # 3. 特效解析 (Meta Logic)
        # 这里处理所有副作用：异常、能力升降、吸血、OHKO判定
        outcome.meta_effects = self._resolve_meta_effects(attacker, defender, move, outcome)

        return outcome

    def _resolve_meta_effects(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                              outcome: MoveOutcome) -> List[Dict]:
        """根据 meta_category_id 生成特效列表"""
        cat = move.meta_category_id
        effects = []

        # Cat 1: Ailment (纯异常)
        if cat == 1:
            effects.extend(self._gen_ailment_effect(defender, move))

        # Cat 2: Stat Raise (纯提升)
        elif cat == 2:
            effects.extend(self._gen_stat_change_effect(attacker, move, default_target="user"))

        # Cat 3: Heal (回复/自残)
        elif cat == 3:
            effects.extend(self._gen_heal_effect(attacker, move))

        # Cat 4: Damage + Ailment
        elif cat == 4:
            # 只有造成伤害且目标存活时才触发
            if outcome.damage > 0:  # 简化判定，实际应该看是否被免疫
                effects.extend(self._gen_ailment_effect(defender, move))

        # Cat 5: Swagger (混乱+提升攻击)
        elif cat == 5:
            effects.extend(self._gen_ailment_effect(defender, move, force_status_id=6))  # 混乱
            # 无论混乱是否命中，通常都会尝试提升能力(依赖具体世代，这里简化为独立触发)
            effects.extend(self._gen_stat_change_effect(defender, move, default_target="opponent"))

        # Cat 6: Damage + Lower
        elif cat == 6:
            effects.extend(self._gen_stat_change_effect(defender, move, default_target="opponent"))

        # Cat 7: Damage + Raise
        elif cat == 7:
            effects.extend(self._gen_stat_change_effect(attacker, move, default_target="user"))

        # Cat 8: Damage + Drain (吸血)
        elif cat == 8:
            drain_pct = getattr(move, 'drain', 50) or 50
            heal_amt = int(outcome.damage * (drain_pct / 100.0))
            if heal_amt > 0:
                effects.append({"type": "heal", "amount": heal_amt, "from_drain": True, "damage_dealt": outcome.damage})

        # Cat 9: OHKO (一击必杀)
        elif cat == 9:
            success, reason = self._check_ohko(attacker, defender, move, outcome.effectiveness)
            if success:
                outcome.damage = defender.current_hp  # 覆盖伤害
                effects.append({"type": "ohko", "success": True})
            else:
                outcome.damage = 0
                effects.append({"type": "ohko", "success": False, "reason": reason})

        # Cat 10-13: 场地等
        elif cat in [10, 11, 12, 13]:
            map_type = {10: "field_effect", 11: "terrain", 12: "force_switch", 13: "unique"}
            effects.append({"type": map_type.get(cat, "unique"), "effect": "active"})

        return effects

    # --- 5. 辅助逻辑 (Helpers) ---

    def _calculate_base_damage_params(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo):
        """计算基础伤害所需的参数"""
        attacker_stats = self._get_modified_stats(attacker)
        defender_stats = self._get_modified_stats(defender)

        # 攻防值选择
        is_physical = (move.damage_class_id == 2)
        atk = attacker_stats.attack if is_physical else attacker_stats.sp_attack
        defense = defender_stats.defense if is_physical else defender_stats.sp_defense

        # 等级因子
        level = attacker.context.pokemon.level

        # 修正因子
        eff = self.calculate_type_effectiveness([move.type_name], defender.context.types)
        stab = 1.5 if move.type_name in attacker.context.types else 1.0
        is_crit = (random.random() < self.CRIT_RATE)
        crit_mod = 1.5 if is_crit else 1.0
        rand_mod = random.uniform(0.85, 1.0)

        # 基础公式
        # ((2*Lv/5 + 2) * Power * A/D) / 50 + 2
        base_raw = ((2 * level / 5 + 2) * move.power * (atk / max(1, defense))) / 50 + 2
        final_dmg = base_raw * eff * stab * crit_mod * rand_mod

        if eff == 0: return 0, 0.0, False  # 免疫

        return final_dmg, eff, is_crit

    def _gen_ailment_effect(self, target: BattleState, move: BattleMoveInfo, force_status_id=None) -> List[Dict]:
        """生成异常状态效果"""
        chance = move.ailment_chance if move.ailment_chance > 0 else 100
        if random.randint(1, 100) > chance: return []

        ailment_id = force_status_id or move.meta_ailment_id

        # 免疫检查
        target_types = [t.lower() for t in target.context.types]
        if (ailment_id == 1 and 'electric' in target_types) or \
                (ailment_id == 5 and ('poison' in target_types or 'steel' in target_types)) or \
                (ailment_id == 4 and 'fire' in target_types) or \
                (ailment_id == 3 and 'ice' in target_types):
            return []

        status_name = self.AILMENT_MAP.get(ailment_id, "unknown")
        if status_name != "unknown":
            return [{"type": "ailment", "status": status_name, "status_id": ailment_id}]
        return []

    def _gen_stat_change_effect(self, target: BattleState, move: BattleMoveInfo, default_target: str) -> List[Dict]:
        """生成能力等级变化效果"""
        # [修复] 概率判定逻辑：
        # 数据库中 stat_chance 为 0 或 None 通常表示 100% 触发（例如 Category 2 的必中变化技）
        # 只有当明确配置了数值（如 0.1 代表 10%）时，才应用概率检查
        raw_chance = int(move.stat_chance * 100) if move.stat_chance is not None else 0
        chance = raw_chance if raw_chance > 0 else 100

        if random.randint(1, 100) > chance: return []

        effects = []
        if hasattr(move, 'stat_changes') and move.stat_changes:
            for change in move.stat_changes:
                # 兼容字典或对象访问
                sid = change.get('stat_id') if isinstance(change, dict) else getattr(change, 'stat_id', None)
                amt = change.get('change') if isinstance(change, dict) else getattr(change, 'change', 0)

                if sid is None or amt == 0: continue

                # 计算实际变化
                curr = target.stat_levels.get(sid, 0)
                new_stage = max(-6, min(6, curr + amt))

                if new_stage != curr:
                    effects.append({
                        "type": "stat_change",
                        "stat_id": sid,
                        "stat_name": self.STAT_NAMES.get(sid, "stat"),
                        "change": new_stage - curr,
                        "new_stage": new_stage,
                        "target_obj": target  # 引用目标对象以便 execute 阶段修改
                    })
        return effects

    def _gen_heal_effect(self, target: BattleState, move: BattleMoveInfo) -> List[Dict]:
        ratio = move.healing
        if ratio == 0: return []

        max_hp = target.context.pokemon.stats.hp
        amt = int(max_hp * ratio)

        if amt > 0:
            return [{"type": "heal", "amount": amt}]
        elif amt < 0:
            return [{"type": "damage", "amount": -amt, "is_recoil": True}]  # 自残
        return []

    def _check_ohko(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo, eff: float) -> Tuple[
        bool, str]:
        if attacker.context.pokemon.level < defender.context.pokemon.level:
            return False, "等级不足"
        if eff == 0:
            return False, "属性免疫"

        acc = 30 + (attacker.context.pokemon.level - defender.context.pokemon.level)
        if random.randint(1, 100) <= acc:
            return True, ""
        return False, "未命中"

    def _deduct_pp(self, attacker: BattleState, move: BattleMoveInfo):
        try:
            idx = attacker.context.moves.index(move)
            old_pp = attacker.current_pps[idx]
            if attacker.current_pps[idx] > 0:
                attacker.current_pps[idx] -= 1
                # 添加调试日志
                if hasattr(logger, 'info'):
                    logger.info(f"[DEBUG] PP消耗: {attacker.context.pokemon.name}的{move.move_name} PP从 {old_pp} 变为 {attacker.current_pps[idx]}")
        except ValueError:
            pass

    def _apply_meta_effect_changes(self, attacker: BattleState, defender: BattleState, effects: List[Dict]):
        """在执行阶段应用 meta effects (修改HP, Stat Levels)"""
        for eff in effects:
            etype = eff.get("type")

            if etype == "heal":
                amt = eff.get("amount", 0)
                old_hp = attacker.current_hp
                attacker.current_hp = min(attacker.context.pokemon.stats.hp, attacker.current_hp + amt)
                attacker.current_hp = max(0, attacker.current_hp)

                # 添加调试日志
                if hasattr(attacker, 'context') and hasattr(attacker.context.pokemon, 'name'):
                    if attacker.context.pokemon.name:  # 确保name存在
                        logger.info(f"[DEBUG] HP回复: {attacker.context.pokemon.name} HP从 {old_hp} 变为 {attacker.current_hp} (回复 {amt} 点)")

            elif etype == "damage":
                amt = eff.get("amount", 0)
                old_hp = attacker.current_hp
                attacker.current_hp = max(0, attacker.current_hp - amt)

                # 添加调试日志
                if hasattr(attacker, 'context') and hasattr(attacker.context.pokemon, 'name'):
                    if attacker.context.pokemon.name:  # 确保name存在
                        logger.info(f"[DEBUG] HP损伤: {attacker.context.pokemon.name} HP从 {old_hp} 变为 {attacker.current_hp} (减少 {amt} 点)")

            elif etype == "stat_change":
                # 从 effect 中获取目标对象和新等级
                target = eff.get("target_obj")
                sid = eff.get("stat_id")
                new_val = eff.get("new_stage")
                if target and sid:
                    old_level = target.stat_levels.get(sid, 0)
                    target.stat_levels[sid] = new_val

                    # 添加调试日志
                    if hasattr(target, 'context') and hasattr(target.context.pokemon, 'name'):
                        if target.context.pokemon.name:  # 确保name存在
                            stat_name = self.STAT_NAMES.get(sid, f"未知属性({sid})")
                            logger.info(f"[DEBUG] 属性变化: {target.context.pokemon.name}的{stat_name}等级从 {old_level} 变为 {new_val}")

    def _log_meta_effects(self, attacker, defender, effects, logger_obj):
        """统一日志记录"""
        for eff in effects:
            etype = eff.get("type")
            if etype == "ailment":
                # 尝试使用中文状态名称
                status_id = eff.get('status_id')
                if status_id and status_id in self.AILMENT_CHINESE_MAP:
                    status_name_chinese = self.AILMENT_CHINESE_MAP[status_id]
                    logger_obj.log(f"{defender.context.pokemon.name}陷入{status_name_chinese}状态！\n\n")
                else:
                    logger_obj.log(f"{defender.context.pokemon.name}陷入{eff['status']}状态！\n\n")
            elif etype == "stat_change":
                t_name = eff['target_obj'].context.pokemon.name
                action = "提升" if eff['change'] > 0 else "降低"
                logger_obj.log(f"{t_name}的{eff['stat_name']}{action}了！\n\n")

                # 添加调试日志
                if logger_obj.should_log_details():
                    logger.info(f"[DEBUG] 属性变化: {t_name}的{eff['stat_name']}等级从 {eff['target_obj'].stat_levels.get(eff['stat_id'], 0)} 变为 {eff['new_stage']} (变化量: {eff['change']})")
            elif etype == "heal":
                if eff.get("from_drain"):
                    logger_obj.log(f"{attacker.context.pokemon.name}通过攻击吸收了{eff['amount']}点HP！\n\n")
                else:
                    logger_obj.log(f"{attacker.context.pokemon.name}回复了{eff['amount']}点HP！\n\n")
            elif etype == "damage":
                logger_obj.log(f"{attacker.context.pokemon.name}损失了{eff['amount']}点HP！\n\n")
            elif etype == "ohko":
                if eff['success']:
                    logger_obj.log("一击必杀！直接击败了对手！\n\n")
                else:
                    logger_obj.log(f"一击必杀失败！{eff.get('reason', '')}\n\n")

    def _apply_residual_stat_changes(self, attacker: BattleState, defender: BattleState, move: BattleMoveInfo,
                                     logger_obj: BattleLogger):
        """
        处理不在主要 Meta Category (2, 6, 7) 中的剩余属性变化。
        例如：某些特殊招式虽然主要分类是 Damage，但依然配置了 stat_changes。
        """
        if not hasattr(move, 'stat_changes') or not move.stat_changes:
            return

        stat_changes = move.stat_changes
        target_id = move.target_id

        # 1. 确定承受能力变化的目标
        target_unit = None

        if target_id in self.TARGETS_OPPONENT:
            target_unit = defender
        elif target_id in self.TARGETS_USER:
            target_unit = attacker
        else:
            # 智能判定 Fallback：
            # 如果包含正面效果(提升)，通常是给自己用的；
            # 如果只有负面效果(降低)，通常是给对手用的。
            has_positive = False
            for c in stat_changes:
                change_val = c.get('change') if isinstance(c, dict) else getattr(c, 'change', 0)
                if change_val > 0:
                    has_positive = True
                    break

            target_unit = attacker if has_positive else defender

        # 2. 应用变化并记录日志
        if target_unit:
            # 确保 stat_levels 已初始化
            if target_unit.stat_levels is None:
                target_unit.stat_levels = {}

            # 遍历每一个具体的能力变化项
            for change in stat_changes:
                # 兼容字典或对象属性访问
                stat_id = change.get('stat_id') if isinstance(change, dict) else getattr(change, 'stat_id', None)
                change_amount = change.get('change') if isinstance(change, dict) else getattr(change, 'change', 0)

                if stat_id is None or change_amount == 0:
                    continue

                # 获取当前等级 (-6 到 +6)
                current_stage = target_unit.stat_levels.get(stat_id, 0)

                # 计算新等级 (Clamp 限制在 -6 到 6 之间)
                new_stage = max(-6, min(6, current_stage + change_amount))

                # 如果等级发生了实际改变
                if new_stage != current_stage:
                    # 更新状态
                    target_unit.stat_levels[stat_id] = new_stage

                    # 记录日志
                    stat_name = self.STAT_NAMES.get(stat_id, f"未知属性({stat_id})")

                    # 判断是“提升”还是“降低” (基于实际产生的变化，而非原始数值)
                    # 例如：如果已经是 +6，再 +1，new_stage == current_stage，不会进到这里，符合逻辑
                    # 如果是 +5，再 +2，new_stage 变成 +6，实际提升了 1 级

                    actual_diff = new_stage - current_stage
                    action_desc = "大幅提升" if actual_diff > 1 else "提升" if actual_diff > 0 else "大幅降低" if actual_diff < -1 else "降低"

                    logger_obj.log(f"{target_unit.context.pokemon.name}的{stat_name}{action_desc}了！\n\n")
    # --- 6. 工具与计算辅助 ---

    def _is_user_first(self, user_state, wild_state, u_move, w_move) -> bool:
        if u_move.priority != w_move.priority: return u_move.priority > w_move.priority
        u_spd = self._get_modified_stats(user_state).speed
        w_spd = self._get_modified_stats(wild_state).speed
        if u_spd != w_spd: return u_spd > w_spd
        return random.random() < 0.5

    def _get_modified_stats(self, state: BattleState):
        if not state.stat_levels: return state.context.pokemon.stats
        mod, _ = self.stat_modifier_service.apply_stat_changes(
            state.context.pokemon.stats, [], state.stat_levels
        )
        return mod

    def calculate_type_effectiveness(self, atk_types: List[str], def_types: List[str]) -> float:
        eff = 1.0
        for at in atk_types:
            at_en = self.TYPE_NAME_MAPPING.get(at, at.lower())
            if at_en not in self.TYPE_CHART: continue
            for dt in def_types:
                dt_en = self.TYPE_NAME_MAPPING.get(dt, dt.lower())
                eff *= self.TYPE_CHART[at_en].get(dt_en, 1.0)
        return eff

    def _get_pp_str(self, attacker, move):
        try:
            curr = attacker.current_pps[attacker.context.moves.index(move)]
        except:
            curr = move.current_pp
        return f" (PP: {curr}/{move.max_pp})"

    def _get_atk_def_ratio(self, attacker_state, defender_state, move):
        """AI评分用的辅助函数"""
        a_stats = self._get_modified_stats(attacker_state)
        d_stats = self._get_modified_stats(defender_state)
        atk = a_stats.attack if move.damage_class_id == 2 else a_stats.sp_attack
        defense = d_stats.defense if move.damage_class_id == 2 else d_stats.sp_defense
        return atk / max(1, defense)

    # --- 7. AI 评分逻辑 (保留之前的优化版) ---

    def _calculate_unified_move_score(self, attacker_state: BattleState, defender_state: BattleState,
                                      move: BattleMoveInfo, logger_obj: Optional[BattleLogger] = None) -> float:
        """
        统一的技能评分函数，根据 meta_category_id 区分处理
        """
        score = 0.0
        cat_id = move.meta_category_id

        # 定义伤害类 meta_category_id (即使 power=0 数据有误，逻辑上也属于攻击招式)
        # 0: Damage, 4: Dmg+Ailment, 6: Dmg+Lower, 7: Dmg+Raise, 8: Dmg+Heal, 9: OHKO
        DAMAGING_CATEGORIES = [0, 4, 6, 7, 8, 9]
        is_damaging_move = cat_id in DAMAGING_CATEGORIES

        # --- 1. 基础伤害评分 (仅针对伤害类技能) ---
        expected_damage = 0
        if is_damaging_move:
            # 基础伤害计算公式
            attacker_stats = self._get_modified_stats(attacker_state)
            defender_stats = self._get_modified_stats(defender_state)

            atk_def_ratio = self._get_atk_def_ratio(attacker_state, defender_state, move)
            level = attacker_state.context.pokemon.level

            eff = self.calculate_type_effectiveness([move.type_name], defender_state.context.types)
            stab = 1.5 if move.type_name in attacker_state.context.types else 1.0

            # 估算基础伤害 (不含随机数和暴击)
            base_damage = ((2 * level / 5 + 2) * move.power * atk_def_ratio) / 50 + 2
            expected_damage = base_damage * (move.accuracy / 100.0) * eff * stab

            score += expected_damage

            # [斩杀奖励]：如果预期伤害能击败对手，给予巨额加分
            # 注意：这里使用 expected_damage 作为近似，实际扣血可能略有不同
            if expected_damage >= defender_state.current_hp:
                score += 1000.0

        # --- 2. 效果/战术评分 (根据 Category 分流) ---

        # Cat 0: 纯伤害 (已在上面计算)
        if cat_id == 0:
            pass

        # Cat 1: 纯异常状态 (如电磁波、鬼火)
        elif cat_id == 1:
            base_score = 15.0
            chance_multiplier = (move.ailment_chance / 100.0) if move.ailment_chance > 0 else 1.0
            score += base_score * chance_multiplier

            # 特殊状态加分
            if move.meta_ailment_id in [1, 4, 5]:  # 麻痹/灼伤/中毒
                score *= 1.4
            elif move.meta_ailment_id in [2, 3]:  # 睡眠/冰冻
                score *= 1.2

            # 对手血量健康时，异常状态价值更高
            hp_ratio = defender_state.current_hp / defender_state.context.pokemon.stats.hp
            if hp_ratio > 0.7:
                score *= 1.3

        # Cat 2: 纯能力提升 (如剑舞)
        elif cat_id == 2:
            # 基础分较低，避免无脑强化
            score += 5.0

            # 使用原逻辑：根据当前强化等级判断是否还需要强化
            if hasattr(move, 'stat_changes') and move.stat_changes:
                for change in move.stat_changes:
                    if change.get('change', 0) > 0:
                        stat_id = change.get('stat_id', 0)
                        current_stage = attacker_state.stat_levels.get(stat_id, 0) if attacker_state.stat_levels else 0

                        # 如果还没强化满，且等级越低，强化意愿越高
                        if current_stage < 6:
                            # 递减收益：0级时加分多，3级时加分少
                            score += 10.0 * (0.7 ** max(0, current_stage))

        # Cat 3: 回复 (如自我再生)
        elif cat_id == 3:
            current_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
            heal_ratio = move.healing

            if heal_ratio > 0:  # 回复
                score += heal_ratio * 100.0
                if current_hp_ratio < 0.5:  # 半血以下急需回复
                    score *= 2.0
            elif heal_ratio < 0:  # 自残/替身
                if current_hp_ratio > 0.8:  # 血量健康时才考虑替身
                    score += 20.0

        # Cat 4: 伤害 + 异常 (如火焰拳)
        elif cat_id == 4:
            # 已经有伤害分了，这里加额外特效分
            ailment_value = 8.0
            if move.meta_ailment_id in [1, 4, 5]:  # 强力状态
                ailment_value = 15.0
            elif move.meta_ailment_id in [2, 3]:  # 限制状态
                ailment_value = 12.0

            chance = (move.ailment_chance / 100.0) if move.ailment_chance > 0 else 1.0
            score += ailment_value * chance

        # Cat 5: 虚张声势类 (混乱但提升对手攻击)
        elif cat_id == 5:
            score += 12.0
            # 如果对手攻击已经很高，风险太大，降低评分
            opp_atk_lvl = defender_state.stat_levels.get(1, 0) if defender_state.stat_levels else 0
            if opp_atk_lvl > 1:
                score *= 0.5

        # Cat 6: 伤害 + 降低能力 (如咬碎)
        elif cat_id == 6:
            if hasattr(move, 'stat_changes'):
                for change in move.stat_changes:
                    if change.get('change', 0) < 0:
                        # 降低对手能力的价值
                        score += 5.0 + abs(change.get('change', 0)) * 2

        # Cat 7: 伤害 + 提升能力 (如原始之力)
        elif cat_id == 7:
            if hasattr(move, 'stat_changes'):
                for change in move.stat_changes:
                    if change.get('change', 0) > 0:
                        # 提升自己能力的价值
                        score += 5.0 + change.get('change', 0) * 3

        # Cat 8: 伤害 + 吸血 (如吸取拳)
        elif cat_id == 8:
            drain_ratio = getattr(move, 'drain', 50) / 100.0
            heal_value = expected_damage * drain_ratio * 0.8
            current_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
            if current_hp_ratio < 0.5:
                heal_value *= 2.0  # 残血时吸血价值极高
            score += heal_value

        # Cat 9: 一击必杀
        elif cat_id == 9:
            score += 10.0  # 基础分
            # 命中率通常只有30%，且对高等级无效，这里的期望伤害计算可能不准，给予额外修正
            if attacker_state.context.pokemon.level < defender_state.context.pokemon.level:
                score = 0  # 无效

        # Cat 10-13: 场地/全场/特殊
        elif cat_id in [10, 11, 12, 13]:
            score += 15.0  # 简单的战术加分

        # --- 额外检查：对于两回合技能的特殊评分 ---
        # 检查是否是两回合技能，如果是第一回合，则考虑整体战略价值
        move_config = self.TWO_TURN_MOVES_CONFIG.get(move.move_id)
        if move_config:
            protect_type = move_config.get("protect_type")

            # 飞天 vs 地面系
            if protect_type == "flying":
                # 查找对手是否有地面系招式
                has_counter_move = any(self._is_type(m.type_name, 'ground') for m in defender_state.context.moves)
                if has_counter_move:
                    score += 10.0  # 对手有地面系技能，使用飞天/飞翔有一定价值
            # 潜水 vs 电系
            elif protect_type == "diving":
                has_counter_move = any(self._is_type(m.type_name, 'electric') for m in defender_state.context.moves)
                if has_counter_move:
                    score += 10.0  # 对手有电系技能，使用潜水有一定价值
            # 挖洞 vs 飞行系
            elif protect_type == "underground":
                has_counter_move = any(self._is_type(m.type_name, 'flying') for m in defender_state.context.moves)
                if has_counter_move:
                    score += 10.0  # 对手有飞行系技能，使用挖洞有一定价值
            # 如果是提升属性的技能
            elif "stat_boost" in move_config or "turn_2_boost" in move_config:
                # 两回合技能，但第一回合就提升属性，对持久战有帮助
                if "stat_boost" in move_config:
                    boost_count = len(move_config["stat_boost"])
                    score += 10.0 * boost_count  # 根据提升的属性数量评分
                elif "turn_2_boost" in move_config:
                    boost_count = len(move_config["turn_2_boost"])
                    score += 10.0 * boost_count  # 根据提升的属性数量评分
            # 如果是穿透保护的技能
            elif move_config.get("bypass_protect"):
                # 这些技能可以穿透保护，对使用保护技能的对手特别有效
                score += 20.0
            else:
                # 对于其他两回合技能，基于基础威力评分
                score += move.power * 0.2

        # --- 3. 战术修正 (Contextual Penalties) ---
        # 这些修正主要用于“如果不造成伤害，这回合是否浪费了”的判断
        # 因此，通常只对【纯变化技能】(非伤害类) 应用严苛的惩罚

        if not is_damaging_move:
            # 3.1 斩杀线检查：如果我有其他技能可以直接打死对手，就不要用变化技能磨叽了
            defender_hp = defender_state.current_hp
            max_other_damage = 0

            # 简单估算一下其他技能的伤害 (只看最大威力的那个)
            # 为了性能，这里不做完整的 simulate，只做粗略估算
            for other_move in attacker_state.context.moves:
                if other_move.power > 0 and other_move.meta_category_id in DAMAGING_CATEGORIES:
                    # 复用上面的估算逻辑简化版
                    atk_def_ratio = self._get_atk_def_ratio(attacker_state, defender_state, other_move)
                    raw_dmg = ((
                                       2 * attacker_state.context.pokemon.level / 5 + 2) * other_move.power * atk_def_ratio) / 50 + 2
                    eff = self.calculate_type_effectiveness([other_move.type_name], defender_state.context.types)
                    if raw_dmg * eff >= defender_hp:
                        max_other_damage = raw_dmg * eff
                        break

            if max_other_damage >= defender_hp:
                score = -100.0  # 绝对不选，直接打死
                if logger_obj and hasattr(logger_obj, 'should_log_details') and logger_obj.should_log_details():
                    logger.info(f"[DEBUG] {move.move_name} 被惩罚: 能直接斩杀时不使用变化技")
                    logger.info(f"[DEBUG] 最大其他技能伤害: {max_other_damage}, 对手HP: {defender_hp}")

            # 3.2 自身状态检查：如果我快死了 (HP < 40%)，别强化了，赶紧输出
            attacker_hp_ratio = attacker_state.current_hp / attacker_state.context.pokemon.stats.hp
            if attacker_hp_ratio < 0.4 and cat_id not in [3, 8]:  # 排除回血技
                score *= 0.1

            # 3.3 对手状态检查：对手快死了，也别用变化技
            defender_hp_ratio = defender_state.current_hp / defender_state.context.pokemon.stats.hp
            if defender_hp_ratio < 0.25:
                score *= 0.1

        return score

    def _calculate_self_destruct_score(self, attacker, defender, move, logger_obj):
        # 简单版自爆评分
        score = self._calculate_unified_move_score(attacker, defender, move, logger_obj)
        if attacker.current_hp / attacker.context.pokemon.stats.hp < 0.3:
            score += 200  # 残血鼓励自爆
        return score