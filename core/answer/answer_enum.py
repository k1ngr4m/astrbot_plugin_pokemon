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
    USER_TEAM_NOT_SET = "❌ 您还没有设置队伍。请先使用 /设置队伍 指令设置您的出场队伍，才能进行冒险。"
    USER_ADVENTURE_AREA_NOT_SPECIFIED = "❌ 请输入要冒险的区域短码。用法：冒险 <区域短码>\n\n💡 提示：使用 查看区域 指令查看所有可冒险的区域。"
    USER_ADVENTURE_NOT_ENCOUNTERED = "❌ 您当前没有遇到野生宝可梦。请先使用 /冒险 <区域代码> 指令去冒险遇到野生宝可梦。"

    # 宝可梦相关提示
    POKEMON_INIT_SELECT_USAGE_ERROR = "❌ 请输入宝可梦ID。用法：初始选择 <宝可梦ID>"
    POKEMON_ID_INVALID = "❌ 请输入正确的宝可梦ID。"
    POKEMON_NOT_FOUND = "❌ 没有找到对应的宝可梦。"

    # 队伍相关提示
    TEAM_SET_USAGE_ERROR = "❌ 请输入宝可梦ID列表。\n\n用法：设置队伍 <宝可梦ID1> <宝可梦ID2> ...\n\n💡 提示：最多可设置6只宝可梦。\n\n使用 /我的宝可梦 指令查看您的宝可梦列表和对应的ID。"
    TEAM_SET_MAX_POKEMON = "❌ 队伍最多只能包含6只宝可梦。"
    TEAM_SET_MIN_POKEMON = "❌ 请至少选择1只宝可梦加入队伍。"



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