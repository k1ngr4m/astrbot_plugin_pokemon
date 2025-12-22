import math
import os
import re
from typing import Tuple, Dict, Any, List
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 复用样式配置
from .styles import (
    COLOR_TITLE, COLOR_CMD, COLOR_LINE, COLOR_SHADOW,
    COLOR_TEXT_DARK, COLOR_CARD_BG, COLOR_CARD_BORDER,
    load_font, COLOR_WARNING, COLOR_ERROR, COLOR_SUCCESS,
    TYPE_COLORS, lighten_color, draw_rounded_rectangle
)
from .gradient_utils import create_vertical_gradient

# --- 配置常量 ---
# --- 配置常量 ---
BATTLE_LOG_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_radius": 15,
    "sprite_size": (100, 100),
    "line_height": 28,  # 统一行高
    "colors": {
        "bg_win": (230, 255, 230), 
        "bg_loss": (255, 230, 230),
        "card_bg": (255, 255, 255, 245),
        "text_main": (50, 50, 50),
        "text_sub": (120, 120, 120),
        "turn_bg": (240, 240, 240)
    }
}

class BattleDrawer:
    def __init__(self):
        self.cfg = BATTLE_LOG_CONFIG
        self.width = self.cfg["width"]
        self.fonts = self._load_fonts()
        self.sprite_cache = {}

    def _load_fonts(self):
        return {
            "title": load_font(32),
            "subtitle": load_font(20),
            "card_title": load_font(24),
            "normal": load_font(18),
            "small": load_font(15),  # 提升 1px 增加可读性
            "result_badge": load_font(22),
            "result_win": load_font(24), # Keep these for backward compat if needed or just use result_badge
            "result_loss": load_font(24),
        }

    def _load_pokemon_sprite(self, pokemon_id: int) -> Image.Image:
        """加载宝可梦精灵图片 (复用逻辑)"""
        base_path = os.path.dirname(__file__)
        sprite_path = os.path.abspath(os.path.join(
            base_path,
            "..", "..", "..", "..", "assets", "sprites", "front", f"{pokemon_id}.png"
        ))

        if pokemon_id in self.sprite_cache:
            return self.sprite_cache[pokemon_id]

        try:
            sprite = Image.open(sprite_path).convert("RGBA")
            sprite = sprite.resize(self.cfg["sprite_size"], Image.Resampling.LANCZOS)
            self.sprite_cache[pokemon_id] = sprite
            return sprite
        except FileNotFoundError:
            return Image.new("RGBA", self.cfg["sprite_size"], (0,0,0,0))

    def _draw_shadow(self, image: Image.Image, xy, radius, blur=15, offset=(0, 5)):
         # 阴影复用 logic check: styles.py not exposing it directly? Copied from PokedexDetail
        shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        x1, y1, x2, y2 = xy
        shadow_draw.rounded_rectangle(
            (x1 + offset[0], y1 + offset[1], x2 + offset[0], y2 + offset[1]),
            radius=radius,
            fill=(0,0,0, 40)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
        image.paste(shadow, (0, 0), shadow)

    def draw(self, log_data: Dict[str, Any]) -> Image.Image:
        """
        log_data structure matches what 'get_battle_log_by_id' returns:
        {
            'id': int,
            'created_at': str,
            'target_name': str,
            'result': 'success' | 'fail',
            'log_data': [
                {
                    'pokemon_name': str, 'level': int, 'result': 'win'|'loss',
                    'win_rate': float, 'trainer_pokemon_name': str(opt) ...
                }, ...
            ]
        }
        """
        # 1. 高度预计算引擎
        pad = self.cfg["padding"]
        line_h = self.cfg["line_height"]
        skirmishes = log_data.get('log_data', [])
        
        current_y = 150 + pad
        layouts = []
        
        for sk in skirmishes:
            details = sk.get('details', [])
            details_h = 0
            for line in details:
                line_str = str(line).strip()
                if not line_str: continue # Ignore empty lines
                
                # Turn Header Logic
                if "第" in line_str and "回合" in line_str:
                    details_h += (line_h + 15) 
                else:
                    details_h += (line_h + 4)
            
            # Base (140) + Details + Buffer (30)
            card_h = 140 + details_h + 30
            layouts.append({"y": current_y, "h": card_h, "details": details})
            current_y += card_h + 20
            
        # 2. 背景与标题
        image = create_vertical_gradient(self.width, current_y + pad, self.cfg["colors"]["bg_win"], (255, 255, 255))
        overlay = Image.new('RGBA', image.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        
        # 标题绘制
        self._draw_header(draw, log_data, pad)

        # 3. 卡片绘制
        for i, sk in enumerate(skirmishes):
            layout = layouts[i]
            self._draw_skirmish_card(draw, overlay, sk, layout, pad, log_data) # Pass log_data

        image.paste(overlay, (0,0), overlay)
        return image

    def _draw_skirmish_card(self, draw, overlay, sk, layout, pad, log_data):
        y, h = int(layout["y"]), int(layout["h"])
        rect = (pad, y, self.width - pad, y + h)
        
        # Draw Shadow & BG
        self._draw_shadow(overlay, rect, self.cfg["card_radius"]) # Pass overlay to shadow helper if it supports image
        # Wait, _draw_shadow takes (image, xy, radius). I passed overlay. Correct.
        draw_rounded_rectangle(draw, rect, self.cfg["card_radius"], fill=self.cfg["colors"]["card_bg"])
        
        # --- Top Info (Refactored from old draw) ---
        card_y = y
        
        # Left: User Pokemon
        u_name = sk.get('pokemon_name', '未知')
        u_lv = sk.get('level', 1)
        user_species_id = sk.get('user_species_id') or sk.get('species_name')
        user_types = sk.get('user_types', [])
        
        u_color = COLOR_TEXT_DARK
        if user_types: u_color = self._get_type_color(user_types[0])
        
        lx = pad + 20
        ly = card_y + 20
        
        # Sprite
        if user_species_id and isinstance(user_species_id, int):
            sprite = self._load_pokemon_sprite(user_species_id)
            overlay.paste(sprite, (lx, ly), sprite)
            lx += 110
            
        # Name & Badge
        title_font = self.fonts["card_title"]
        draw.text((lx, ly + 20), f"{u_name}", fill=COLOR_TEXT_DARK, font=title_font)
        name_w = title_font.getlength(u_name)
        
        badge_text = self._en_to_zh(user_types[0]) if user_types else "一般"
        self._draw_type_badge(draw, int(lx + name_w + 10), int(ly + 24), badge_text, u_color)
        
        # Level
        draw.text((lx, ly + 55), f"Lv.{u_lv}", fill=self.cfg["colors"]["text_sub"], font=self.fonts["normal"])
        
        # HP Bar
        u_cur_hp = sk.get('current_hp', 0)
        u_max_hp = sk.get('max_hp', 100)
        self._draw_hp_bar(draw, lx, ly + 85, 160, u_cur_hp, u_max_hp)
        
        # VS Badge
        mx = self.width // 2
        my = card_y + 140 // 2 # base_h // 2
        draw.ellipse((mx - 25, my - 25, mx + 25, my + 25), fill=(240, 240, 240))
        draw.text((mx, my), "VS", fill=(180, 180, 180), font=self.fonts["title"], anchor="mm")
        
        # Right: Opponent
        op_name = sk.get('trainer_pokemon_name') or log_data.get('target_name')
        op_lv = sk.get('trainer_pokemon_level') or sk.get('target_level') or log_data.get('target_level')
        target_species_id = sk.get('target_species_id')
        target_types = sk.get('target_types', [])
        
        op_color = COLOR_TEXT_DARK
        if target_types: op_color = self._get_type_color(target_types[0])
        
        rx = self.width - pad - 20
        ry = card_y + 20
        
        # Sprite (Right)
        if target_species_id and isinstance(target_species_id, int):
            sprite = self._load_pokemon_sprite(target_species_id)
            overlay.paste(sprite, (rx - 100, ry), sprite)
            rx -= 110
            
        # Name
        draw.text((rx, ry + 20), f"{op_name}", fill=COLOR_TEXT_DARK, font=title_font, anchor="rs")
        op_name_w = title_font.getlength(f"{op_name}")
        
        # Badge
        op_badge_text = self._en_to_zh(target_types[0]) if target_types else "一般"
        small_font = self.fonts["small"]
        badge_w = small_font.getlength(op_badge_text) + 16
        self._draw_type_badge(draw, int(rx - op_name_w - 10 - badge_w), int(ry + 24), op_badge_text, op_color)
        
        # Level
        if op_lv:
             draw.text((rx, ry + 55), f"Lv.{op_lv}", fill=self.cfg["colors"]["text_sub"], font=self.fonts["normal"], anchor="rs")
             
        # HP Bar (Right)
        t_cur_hp = sk.get('target_current_hp', 0)
        t_max_hp = sk.get('target_max_hp', 100)
        self._draw_hp_bar(draw, rx - 160, ry + 85, 160, t_cur_hp, t_max_hp, is_right=True)
        
        # Result & Win Rate
        res_text = "胜利" if sk.get('result') == 'win' else "失败"
        res_col = COLOR_SUCCESS if sk.get('result') == 'win' else COLOR_ERROR
        wr = sk.get('win_rate', 0)
        
        if wr >= 100: wr_col = (255, 215, 0)
        elif wr >= 50: wr_col = (0, 100, 0)
        else: wr_col = COLOR_ERROR
        
        bx = mx
        by = my - 40
        draw.text((bx, by), res_text, fill=res_col, font=self.fonts["result_win"], anchor="mm")
        draw.text((mx, my + 40), f"胜率: {wr}%", fill=wr_col, font=self.fonts["subtitle"], anchor="mm")
        
        # --- 详细过程区域 (Bottom Details - Fixed Logic) ---
        if layout["details"]:
            curr_dy = y + 130 
            draw.line((pad+20, curr_dy, self.width-pad-20, curr_dy), fill=(235, 235, 235), width=1)
            curr_dy += 20
            
            for line in layout["details"]:
                line_str = str(line).strip()
                if not line_str: continue

                if "第" in line_str and "回合" in line_str:
                    self._draw_turn_badge(draw, pad + 30, curr_dy, line_str)
                    curr_dy += self.cfg["line_height"] + 15
                else:
                    self._draw_rich_text_line(draw, pad + 35, curr_dy, line)
                    curr_dy += self.cfg["line_height"] + 4

    def _draw_hp_bar(self, draw: ImageDraw.Draw, x: int, y: int, width: int, current_hp: int, max_hp: int, is_right: bool = False):
        """绘制带高光反闪的血量条"""
        if max_hp <= 0: max_hp = 1
        ratio = max(0, min(1, current_hp / max_hp))
        h = 10
        
        # 背景
        draw_rounded_rectangle(draw, (x, y, x + width, y + h), corner_radius=5, fill=(220, 220, 220))
        
        # 颜色逻辑：>50%绿, >20%黄, 其余红
        if ratio > 0.5: bar_col = (76, 175, 80)
        elif ratio > 0.2: bar_col = (255, 193, 7)
        else: bar_col = (244, 67, 54)
        
        if ratio > 0:
            bar_w = int(width * ratio)
            draw_rounded_rectangle(draw, (x, y, x + bar_w, y + h), corner_radius=5, fill=bar_col)
            # 反闪高光
            draw_rounded_rectangle(draw, (x, y, x + bar_w, y + 3), corner_radius=2, fill=(255, 255, 255, 100))
            
        # HP文字
        hp_text = f"{current_hp}/{max_hp}"
        tx = x + width if is_right else x
        anchor = "ra" if is_right else "la"
        draw.text((tx, y + h + 4), hp_text, fill=self.cfg["colors"]["text_sub"], font=self.fonts["small"], anchor=anchor)

    def _draw_type_badge(self, draw: ImageDraw.Draw, x: int, y: int, type_text: str, color: Tuple[int, int, int]):
        """绘制属性徽章"""
        font = self.fonts["small"]
        text_w = font.getlength(type_text)
        text_h = 14 # Approximate height
        pad_x = 8
        pad_y = 2
        
        rect_w = int(text_w + pad_x * 2)
        rect_h = int(text_h + pad_y * 2)
        
        # Draw Badge Background
        draw_rounded_rectangle(draw, (x, y, x + rect_w, y + rect_h), corner_radius=10, fill=color)
        
        # Draw Text (White)
        draw.text((x + pad_x, y + pad_y), type_text, fill=(255, 255, 255), font=font)
        
        return rect_w

    def _draw_hp_bar(self, draw: ImageDraw.Draw, x: int, y: int, width: int, current_hp: int, max_hp: int, is_right: bool = False):
        """绘制带高光反闪的血量条"""
        if max_hp <= 0: max_hp = 1
        ratio = max(0, min(1, current_hp / max_hp))
        h = 10
        
        # 背景
        draw_rounded_rectangle(draw, (x, y, x + width, y + h), corner_radius=5, fill=(220, 220, 220))
        
        # 颜色逻辑：>50%绿, >20%黄, 其余红
        if ratio > 0.5: bar_col = (76, 175, 80)
        elif ratio > 0.2: bar_col = (255, 193, 7)
        else: bar_col = (244, 67, 54)
        
        if ratio > 0:
            bar_w = int(width * ratio)
            draw_rounded_rectangle(draw, (x, y, x + bar_w, y + h), corner_radius=5, fill=bar_col)
            # 反闪高光
            draw_rounded_rectangle(draw, (x, y, x + bar_w, y + 3), corner_radius=2, fill=(255, 255, 255, 100))
            
        # HP文字
        hp_text = f"{current_hp}/{max_hp}"
        tx = x + width if is_right else x
        anchor = "ra" if is_right else "la"
        draw.text((tx, y + h + 4), hp_text, fill=self.cfg["colors"]["text_sub"], font=self.fonts["small"], anchor=anchor)

    def _draw_type_badge(self, draw: ImageDraw.Draw, x: int, y: int, type_text: str, color: Tuple[int, int, int]):
        """绘制属性徽章"""
        font = self.fonts["small"]
        text_w = font.getlength(type_text)
        text_h = 14
        pad_x = 8
        pad_y = 2
        
        rect_w = int(text_w + pad_x * 2)
        rect_h = int(text_h + pad_y * 2)
        
        draw_rounded_rectangle(draw, (x, y, x + rect_w, y + rect_h), corner_radius=10, fill=color)
        draw.text((x + pad_x, y + pad_y), type_text, fill=(255, 255, 255), font=font)
        return rect_w

    def _draw_turn_badge(self, draw, x, y, text):
        """绘制回合标签"""
        txt = text.replace("-", "").strip()
        w = self.fonts["small"].getlength(txt)
        draw_rounded_rectangle(draw, (int(x), int(y), int(x + w + 20), int(y + 22)), corner_radius=10, fill=self.cfg["colors"]["turn_bg"])
        draw.text((x + 10, y + 2), txt, fill=(120, 120, 120), font=self.fonts["small"])

    def _en_to_zh(self, type_en: str) -> str:
        """属性英文转中文"""
        if type_en in TYPE_COLORS: return type_en # Already ZH
        
        TYPE_EN_TO_ZH = {
            "normal": "一般", "fire": "火", "water": "水", "grass": "草",
            "electric": "电", "ice": "冰", "fighting": "格斗", "poison": "毒",
            "ground": "地面", "flying": "飞行", "psychic": "超能力", "bug": "虫",
            "rock": "岩石", "ghost": "幽灵", "dragon": "龙", "steel": "钢",
            "fairy": "妖精"
        }
        return TYPE_EN_TO_ZH.get(type_en.lower(), "未知")

    def _get_type_color(self, type_input: str) -> Tuple[int, int, int]:
        """获取属性对应的颜色"""
        type_zh = self._en_to_zh(type_input)
        return TYPE_COLORS.get(type_zh, COLOR_TEXT_DARK)

    def _draw_rich_text_line(self, draw, x, y, content):
        """修复版：移除加粗，改用底色和颜色突出，并清理手动缩进"""
        raw_text = "".join([s.get('text','') for s in content]) if isinstance(content, list) else str(content)
        # 清理前缀
        full_text = raw_text.strip().lstrip("·").strip()
        
        # 1. 效果绝佳高亮（底色方案，不遮挡文字）
        if "效果绝佳" in full_text:
            text_w = self.fonts["small"].getlength(full_text)
            draw_rounded_rectangle(draw, (int(x-5), int(y-2), int(x+text_w+10), int(y+18)), corner_radius=4, fill=(255, 0, 0, 15))

        # 2. 图标识别
        icon = "• "
        if any(k in full_text for k in ["used", "使用了"]): icon = "⚔️ "
        elif any(k in full_text for k in ["restored", "回复"]): icon = "💚 "
        elif any(k in full_text for k in ["paralyzed", "burned", "poisoned", "asleep", "frozen", "confused", "麻痹", "灼伤", "中毒", "睡眠", "冰冻", "混乱", "陷入"]): icon = "⚠️ "
        elif any(k in full_text for k in ["fainted", "倒下", "defeated"]): icon = "💀 "

        curr_x = x
        draw.text((curr_x, y), icon, fill=self.cfg["colors"]["text_sub"], font=self.fonts["small"])
        curr_x += self.fonts["small"].getlength(icon)

        # 3. 分段渲染
        if isinstance(content, list):
            is_first = True
            for seg in content:
                txt = seg.get('text', '')
                if is_first:
                    # Clean first segment
                    txt = txt.lstrip().lstrip("·").lstrip()
                    if not txt: continue # Skip if empty after clean
                    is_first = False
                
                color = self._get_color(seg.get('color', 'default'))
                draw.text((curr_x, y), txt, fill=color, font=self.fonts["small"])
                curr_x += self.fonts["small"].getlength(txt)
        else:
            # Clean string
            draw.text((curr_x, y), full_text, fill=self.cfg["colors"]["text_main"], font=self.fonts["small"])
            
    def _get_color(self, color_key: str) -> Tuple[int, int, int]:
        if color_key == 'default': return self.cfg["colors"]["text_main"]
        if color_key.startswith('type_'):
            return self._get_type_color(color_key.replace('type_', ''))
        if color_key in ['red', 'hp']: return COLOR_ERROR
        if color_key == 'green': return COLOR_SUCCESS
        if color_key == 'blue': return (66, 133, 244)
        return self.cfg["colors"]["text_main"]

    def _draw_header(self, draw, log_data, pad):
        cx = self.width // 2
        cy = pad + 40
        title_text = f"战斗日志 #{log_data.get('id')}"
        draw.text((cx, cy), title_text, fill=COLOR_TITLE, font=self.fonts["title"], anchor="mm")
        
        date_text = log_data.get('created_at', '')
        draw.text((cx, cy + 40), date_text, fill=self.cfg["colors"]["text_sub"], font=self.fonts["subtitle"], anchor="mm")

def draw_battle_log(log_data: Dict[str, Any]) -> Image.Image:
    drawer = BattleDrawer()
    return drawer.draw(log_data)
