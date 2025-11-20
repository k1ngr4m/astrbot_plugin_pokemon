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
    USER_ADVENTURE_ALREADY_ENCOUNTERED = "❌ 您当前正在冒险中，已经遇到了野生宝可梦。请先处理当前遇到的宝可梦（战斗或捕捉），然后才能重新开始冒险。"
    USER_TEAM_NOT_SET = "❌ 您还没有设置队伍。\n\n请先使用 /设置队伍 指令设置您的出场队伍，才能进行冒险。"
    USER_ADVENTURE_AREA_NOT_SPECIFIED = "❌ 请输入要冒险的区域短码。用法：冒险 <区域短码>\n\n💡 提示：使用 查看区域 指令查看所有可冒险的区域。"
    USER_ADVENTURE_NOT_ENCOUNTERED = "❌ 您当前没有遇到野生宝可梦。\n\n请先使用 /冒险 <区域代码> 指令去冒险遇到野生宝可梦。"

    USER_ITEMS_EMPTY = "🎒 您的背包是空的，快去签到或冒险获得道具吧！"
    # 宝可梦相关提示
    POKEMON_INIT_SELECT_USAGE_ERROR = "❌ 请输入宝可梦ID。\n\n用法：初始选择 <宝可梦ID>"
    POKEMON_ID_INVALID = "❌ 请输入正确的宝可梦ID。"
    POKEMON_NOT_FOUND = "❌ 没有找到对应的宝可梦。"

    # 队伍相关提示
    TEAM_SET_USAGE_ERROR = "❌ 请输入宝可梦ID列表。\n\n用法：设置队伍 <宝可梦ID1> <宝可梦ID2> ...\n\n💡 提示：最多可设置6只宝可梦。\n\n使用 /我的宝可梦 指令查看您的宝可梦列表和对应的ID。"
    TEAM_SET_MAX_POKEMON = "❌ 队伍最多只能包含6只宝可梦。"
    TEAM_SET_MIN_POKEMON = "❌ 请至少选择1只宝可梦加入队伍。"