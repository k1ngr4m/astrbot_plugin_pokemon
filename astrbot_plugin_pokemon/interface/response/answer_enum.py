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
    USER_ADVENTURE_LOCATION_NOT_SPECIFIED = "❌ 请输入要冒险的区域短码。用法：冒险 <区域ID>\n\n💡 提示：使用 查看区域 指令查看所有可冒险的区域。"
    USER_ADVENTURE_NOT_ENCOUNTERED = "❌ 您当前没有遇到野生宝可梦。\n\n请先使用 /冒险 <区域ID> 指令去冒险遇到野生宝可梦。"
    USER_ITEMS_EMPTY = "🎒 您的背包是空的，快去签到或冒险获得道具吧！"
    USER_POKEBALLS_EMPTY = "❌ 您的背包中没有精灵球，无法进行捕捉！请先通过签到或其他方式获得精灵球。"
    USER_POKEMON_NOT_FOUND = "❌ 您没有这只宝可梦，或宝可梦不存在。"
    USER_CHECKIN_SUCCESS = "✅ 签到成功！\n获得了 {gold_reward} 金币 💰\n获得了 {item_name} x{item_quantity} 🎒\n当前金币总数：{new_coins}"
    USER_POKEMONS_NOT_FOUND = "❌ 您还没有获得任何宝可梦。\n\n请先使用 /冒险 <区域ID> 指令去冒险遇到野生宝可梦，或使用 /捕捉 指令捕捉野生宝可梦。"
    USER_POKEMON_ALL_POKEMON_SUCCESS = "✅ 您当前已获得的所有宝可梦如下：\n\n{pokemon_list}"
    USER_ADVENTURE_COOLDOWN = "❌ 冒险冷却中，请等待 {cooldown} 秒后再试。"

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
    TEAM_SET_INVALID_ID = "❌ 宝可梦ID {id} 格式不正确（仅支持数字ID）。"
    TEAM_SET_INVALID_POKEMON_ID = "❌ 宝可梦 {id} 不属于您或不存在。\n\n请检查您的宝可梦ID是否正确，或使用 /我的宝可梦 指令查看您的宝可梦列表和对应的ID。"
    TEAM_SET_SUCCESS = "✅ 成功设置队伍！队伍成员：{pokemon_names}。"
    TEAM_GET_NO_TEAM = "❌ 您还没有设置队伍。\n\n请先使用 /设置队伍 指令设置您的出场队伍，才能进行冒险。"
    TEAM_GET_INVALID_POKEMON_ID = "❌ 队伍中包含不存在的宝可梦 {id}。\n\n请检查您的队伍设置是否正确，或使用 /我的宝可梦 指令查看您的宝可梦列表和对应的ID。"
    TEAM_GET_SUCCESS = "✅ 成功获取队伍信息。\n\n队伍成员：{pokemon_names}"

    # 冒险相关提示
    ADVENTURE_SUCCESS = "您在 {location_name} 中遇到了野生的 {wild_pokemon_name}！\n\n请使用 /战斗 指令与它战斗，或使用 /捕捉 指令捕捉它。"
    ADVENTURE_NO_LOCATIONS = "❌ 暂无可用的冒险区域。\n\n请联系管理员添加新的冒险区域。"
    ADVENTURE_LOCATIONS_FOUND = "✅ 共有 {count} 个可冒险区域。\n\n使用 /冒险 <区域代码> 指令去冒险。"
    ADVENTURE_LOCATION_INVALID = "❌ 区域ID {location_id} 格式不正确（应为正整数）。"
    ADVENTURE_LOCATION_NOT_FOUND = "❌ 未找到区域 {location_id}。\n\n请检查区域ID是否正确，或使用 /查看区域 指令查看所有可冒险的区域。"
    ADVENTURE_LOCATION_NO_POKEMON = "❌ 区域 {location_name} 中暂无野生宝可梦。\n\n请稍后再试，或联系管理员添加野生宝可梦。"
    ADVENTURE_LOCATION_POKEMON_ENCOUNTERED = "接下来你可以选择战斗、捕捉或逃跑...\n\n 使用 /战斗 指令进行对战！\n\n 使用 /捕捉 指令尝试捕捉它！\n\n 使用 /逃跑 指令安全离开！"
