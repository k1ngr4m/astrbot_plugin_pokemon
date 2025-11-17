"""
用户提示信息枚举，统一管理所有用户反馈的提示信息
"""
from enum import Enum


class AnswerEnum(Enum):
    """用户提示信息枚举类"""
    # 通用错误提示
    COMMON_ERROR = "❌ 出错啦！请稍后再试。"

    # 用户相关提示
    USER_NOT_REGISTERED = "❌ 您还没有注册，请先使用 /宝可梦注册 命令注册。"
    USER_ALREADY_CHECKED_IN = "❌ 今天您已经签到过了，请明天再来！"
    USER_ALREADY_REGISTERED = "❌ 您已经注册过了，无需重复注册。"
    USER_ALREADY_INITIALIZED_POKEMON = "❌ 用户已初始化选择宝可梦，无需重复选择。"

    POKEMON_INIT_SELECT_USAGE_ERROR = "❌ 请输入宝可梦ID。用法：初始选择 <宝可梦ID>"
    POKEMON_ID_INVALID = "❌ 请输入正确的宝可梦ID。"
    POKEMON_NOT_FOUND = "❌ 没有找到对应的宝可梦。"

    # 其他可能的提示信息可以继续添加
    USER_REGISTERED_SUCCESS = "✅ 您已成功注册！欢迎来到宝可梦世界！"
    COMMAND_ERROR = "❌ 操作失败，请检查输入或稍后重试。"
    INSUFFICIENT_COINS = "❌ 金币不足，无法完成此操作。"
    POKEMON_NOT_OWNED = "❌ 您尚未拥有此宝可梦。"
    TEAM_FULL = "❌ 队伍已满，无法添加更多宝可梦。"
    TEAM_SLOT_EMPTY = "❌ 该队伍位置为空，请先添加宝可梦。"
    AREA_NOT_FOUND = "❌ 没有找到对应的冒险区域。"
    NO_POKEMON_IN_AREA = "❌ 该区域内暂时没有可遇见的宝可梦。"
    BATTLE_NOT_FOUND = "❌ 没有找到对应的战斗记录。"
    ITEM_NOT_FOUND = "❌ 没有找到对应的道具。"
    INSUFFICIENT_ITEMS = "❌ 道具数量不足。"
    INVALID_COMMAND = "❌ 无效的命令格式，请检查后重试。"