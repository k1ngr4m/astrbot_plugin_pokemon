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
    USER_ADVENTURE_LOCATION_NOT_SPECIFIED = "❌ 请输入要冒险的区域短码。用法：冒险 <区域短码>\n\n💡 提示：使用 查看区域 指令查看所有可冒险的区域。"
    USER_ADVENTURE_NOT_ENCOUNTERED = "❌ 您当前没有遇到野生宝可梦。\n\n请先使用 /冒险 <区域代码> 指令去冒险遇到野生宝可梦。"
    USER_ITEMS_EMPTY = "🎒 您的背包是空的，快去签到或冒险获得道具吧！"
    USER_POKEBALLS_EMPTY = "❌ 您的背包中没有精灵球，无法进行捕捉！请先通过签到或其他方式获得精灵球。"
    USER_POKEMON_NOT_FOUND = "❌ 您没有这只宝可梦，或宝可梦不存在。"
    USER_CHECKIN_SUCCESS = "✅ 签到成功！\n获得了 {gold_reward} 金币 💰\n获得了 {item_name} x{item_quantity} 🎒\n当前金币总数：{new_coins}"
    USER_POKEMONS_NOT_FOUND = "❌ 您还没有获得任何宝可梦。\n\n请先使用 /冒险 <区域代码> 指令去冒险遇到野生宝可梦，或使用 /捕捉 指令捕捉野生宝可梦。"
    USER_POKEMON_ALL_POKEMON_SUCCESS = "✅ 您当前已获得的所有宝可梦如下：\n\n{pokemon_list}"
    # 宝可梦相关提示
    POKEMON_INIT_SELECT_USAGE_ERROR = "❌ 请输入宝可梦ID。\n\n用法：初始选择 <宝可梦ID>"
    POKEMON_ID_INVALID = "❌ 请输入正确的宝可梦ID。"
    POKEMON_NOT_FOUND = "❌ 没有找到对应的宝可梦。"
    POKEMON_INIT_SELECT_INVALID_POKEMON_ID = "❌ 请从妙蛙种子1、小火龙4、杰尼龟7中选择。"
    POKEMON_INIT_SELECT_SUCCESS = "✅ 成功将 {pokemon_name} 初始选择为宝可梦！\n\n它已根据种族模板完善了个体值、努力值等特性。\n\n您可以使用 /我的宝可梦 来查看您的宝可梦详情。"

    # 队伍相关提示
    TEAM_SET_USAGE_ERROR = "❌ 请输入宝可梦ID列表。\n\n用法：设置队伍 <宝可梦ID1> <宝可梦ID2> ...\n\n💡 提示：最多可设置6只宝可梦。\n\n使用 /我的宝可梦 指令查看您的宝可梦列表和对应的ID。"
    TEAM_SET_MAX_POKEMON = "❌ 队伍最多只能包含6只宝可梦。"
    TEAM_SET_MIN_POKEMON = "❌ 请至少选择1只宝可梦加入队伍。"