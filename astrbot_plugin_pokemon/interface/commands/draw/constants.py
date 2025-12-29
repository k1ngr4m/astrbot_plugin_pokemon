# --- 配置 ---
LIST_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_h": 180,  # Increased height to fit 6 IV indicators (was 125)
    "cols": 2,
    "col_gap": 20,
    "row_gap": 15,
    "bg_colors": ((240, 248, 255), (255, 255, 255))
}

TEAM_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_h": 125,  # Increased height to fit Nature/Ability
    "cols": 2,
    "col_gap": 20,
    "row_gap": 15,
    "bg_colors": ((240, 248, 255), (255, 255, 255))
}

POKEDEX_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_h": 100,
    "cols": 4,
    "col_gap": 15,
    "row_gap": 15,
    "bg_colors": ((240, 248, 255), (255, 255, 255))
}

DETAIL_CONFIG = {
    "width": 800,
    "padding": 40,
    "bg_colors": ((255, 250, 240), (255, 255, 255))
}

# 优化 IV 文本映射
STAT_MAP = {
    'hp': 'H  P', 'attack': '攻击', 'defense': '防御',
    'sp_attack': '特攻', 'sp_defense': '特防', 'speed': '速度'
}

# 优化队伍配置
BATTLE_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_h": 125,
    "cols": 2,
    "col_gap": 20,
    "row_gap": 15,
    "bg_colors": ((240, 248, 255), (255, 255, 255))
}