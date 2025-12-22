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
BATTLE_LOG_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_radius": 15,
    "sprite_size": (100, 100),
    "colors": {
        "bg_win": (230, 255, 230), # 浅绿
        "bg_loss": (255, 230, 230), # 浅红
        "card_bg": (255, 255, 255, 230),
        "text_main": (50, 50, 50),
        "text_sub": (100, 100, 100),
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
            "small": load_font(14),
            "result_win": load_font(24),
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
        # 1. 计算高度 & 布局预处理
        pad = self.cfg["padding"]
        header_height = 150
        
        skirmishes = log_data.get('log_data', [])
        
        # 预计算每张卡片的高度
        skirmish_layouts = []
        current_y = header_height + pad
        
        base_card_height = 140
        detail_line_height = 25
        detail_pad = 20
        
        for sk in skirmishes:
             details = sk.get('details', [])
             # 计算详情区域高度
             details_height = len(details) * detail_line_height
             if details_height > 0:
                 details_height += detail_pad * 2 # 上下内边距
             
             total_card_h = base_card_height + details_height
             
             skirmish_layouts.append({
                 "y": current_y,
                 "height": total_card_h,
                 "base_h": base_card_height,
                 "details": details,
                 "details_h": details_height
             })
             
             current_y += total_card_h + 20 # 卡片间距

        total_height = current_y + pad
        
        # 2. 背景
        is_win = log_data.get('result') == 'success'
        bg_col_top = (230, 248, 255) if is_win else (255, 235, 235)
        bg_col_bot = (255, 255, 255)
        
        image = create_vertical_gradient(self.width, total_height, bg_col_top, bg_col_bot)
        
        overlay = Image.new('RGBA', image.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        
        # 3. 标题头
        cx = self.width // 2
        cy = pad + 40
        title_text = f"战斗日志 #{log_data.get('id')}"
        draw.text((cx, cy), title_text, fill=COLOR_TITLE, font=self.fonts["title"], anchor="mm")
        
        date_text = log_data.get('created_at', '')
        draw.text((cx, cy + 40), date_text, fill=self.cfg["colors"]["text_sub"], font=self.fonts["subtitle"], anchor="mm")

        # 4. 对局列表渲染
        for i, sk in enumerate(skirmishes):
            layout = skirmish_layouts[i]
            card_y = layout["y"]
            card_h = layout["height"]
            
            rect = (pad, card_y, self.width - pad, card_y + card_h)
            
            # 卡片背景 & 阴影
            self._draw_shadow(image, rect, self.cfg["card_radius"])
            draw_rounded_rectangle(draw, rect, self.cfg["card_radius"], fill=self.cfg["colors"]["card_bg"])
            
            # --- 基础信息区域 (Top) ---
            
            # Left: User Pokemon
            u_name = sk.get('pokemon_name', '未知')
            u_lv = sk.get('level', 1)
            user_species_id = sk.get('user_species_id') or sk.get('species_name')
            user_types = sk.get('user_types', [])
            
            # Determine Header Color based on primary type
            u_color = COLOR_TEXT_DARK
            user_type_str = "一般"
            if user_types and len(user_types) > 0:
                user_type_str = self._en_to_zh(user_types[0])
                u_color = self._get_type_color(user_types[0])
            
            lx = pad + 20
            ly = card_y + 20
            
            # 绘制我方精灵
            if user_species_id and isinstance(user_species_id, int):
                sprite = self._load_pokemon_sprite(user_species_id)
                overlay.paste(sprite, (lx, ly), sprite)
                lx += 110 # Shift text right
            
            # Draw User Name
            title_font = self.fonts["card_title"]
            draw.text((lx, ly + 20), f"{u_name}", fill=COLOR_TEXT_DARK, font=title_font) # Name in Dark
            
            # Draw Type Badge next to Name
            name_w = title_font.getlength(u_name)
            
            # Helper to get ZH name
            badge_text = self._en_to_zh(user_types[0]) if user_types else "一般"
            self._draw_type_badge(draw, int(lx + name_w + 10), int(ly + 24), badge_text, u_color)

            # Draw Level
            draw.text((lx, ly + 55), f"Lv.{u_lv}", fill=self.cfg["colors"]["text_sub"], font=self.fonts["normal"])
            
            # Draw User HP Bar
            u_cur_hp = sk.get('current_hp', 0)
            u_max_hp = sk.get('max_hp', 100)
            self._draw_hp_bar(draw, lx, ly + 85, 160, u_cur_hp, u_max_hp)
            
            # VS in Middle
            mx = self.width // 2
            my = card_y + layout["base_h"] // 2
            
            # Draw VS Circle Badge
            draw.ellipse((mx - 25, my - 25, mx + 25, my + 25), fill=(240, 240, 240))
            draw.text((mx, my), "VS", fill=(180, 180, 180), font=self.fonts["title"], anchor="mm")
            
            # Right: Opponent
            op_name = sk.get('trainer_pokemon_name') or log_data.get('target_name')
            op_lv = sk.get('trainer_pokemon_level') or sk.get('target_level') or log_data.get('target_level')
            target_species_id = sk.get('target_species_id')
            target_types = sk.get('target_types', [])

            # Determine Opponent Header Color
            op_color = COLOR_TEXT_DARK
            op_type_str = "一般"
            if target_types and len(target_types) > 0:
                op_color = self._get_type_color(target_types[0])

            rx = self.width - pad - 20
            ry = card_y + 20
            
            # 绘制对方精灵 (从右向左布局)
            if target_species_id and isinstance(target_species_id, int):
                sprite = self._load_pokemon_sprite(target_species_id)
                overlay.paste(sprite, (rx - 100, ry), sprite) # 100 is sprite width
                rx -= 110 # Shift text left
            
            # Draw Opponent Name (Right Aligned)
            draw.text((rx, ry + 20), f"{op_name}", fill=COLOR_TEXT_DARK, font=title_font, anchor="rs")
            
            # Draw Type Badge (Left of Name)
            op_name_w = title_font.getlength(op_name)
            op_badge_text = self._en_to_zh(target_types[0]) if target_types else "一般"
            # Calculate badge width approx
            small_font = self.fonts["small"]
            badge_w = small_font.getlength(op_badge_text) + 16
            
            self._draw_type_badge(draw, int(rx - op_name_w - 10 - badge_w), int(ry + 24), op_badge_text, op_color)

            if op_lv:
                 draw.text((rx, ry + 55), f"Lv.{op_lv}", fill=self.cfg["colors"]["text_sub"], font=self.fonts["normal"], anchor="rs")

            # Draw Opponent HP Bar (Aligned Right)
            # HP Bar X start = rx - 160 (Increased width)
            t_cur_hp = sk.get('target_current_hp', 0)
            t_max_hp = sk.get('target_max_hp', 100)
            self._draw_hp_bar(draw, rx - 160, ry + 85, 160, t_cur_hp, t_max_hp, is_right=True)

            # Result Badge
            res_text = "胜利" if sk.get('result') == 'win' else "失败"
            res_col = COLOR_SUCCESS if sk.get('result') == 'win' else COLOR_ERROR
            
            wr = sk.get('win_rate', 0)
            
            # Win Rate Dynamic Color
            if wr >= 100:
                wr_color = (255, 215, 0) # Gold
            elif wr >= 50:
                wr_color = (0, 100, 0) # Dark Green
            else:
                wr_color = COLOR_ERROR
                
            bx = mx
            by = my - 40
            draw.text((bx, by), res_text, fill=res_col, font=self.fonts["result_win"], anchor="mm")
            
            draw.text((mx, my + 40), f"胜率: {wr}%", fill=wr_color, font=self.fonts["subtitle"], anchor="mm")
            
            # --- 详细过程区域 (Bottom Details) ---
            if layout["details"]:
                details_y_start = card_y + layout["base_h"]
                # 分割线
                line_y = details_y_start - 10
                draw.line((pad + 20, line_y, self.width - pad - 20, line_y), fill=(230, 230, 230), width=1)
                
                curr_dy = details_y_start
                for line in layout["details"]:
                    # Turn Header Detection
                    line_str = str(line) # In case line is list
                    turn_match = re.search(r"--- 第 (\d+) 回合 ---", line_str)
                    if turn_match:
                        curr_dy += 15 # Add padding before header
                        turn_num = int(turn_match.group(1))
                        self._draw_turn_header(draw, pad + 30, curr_dy, turn_num)
                    else:
                        # Rich Text
                        self._draw_rich_text_line(draw, pad + 30, curr_dy, line, self.fonts["small"])
                    curr_dy += detail_line_height
                    curr_dy += detail_line_height

        image.paste(overlay, (0,0), overlay)
        return image

    def _draw_hp_bar(self, draw: ImageDraw.Draw, x: int, y: int, width: int, current_hp: int, max_hp: int, is_right: bool = False):
        """绘制拟真血量条"""
        if max_hp <= 0: max_hp = 1
        ratio = max(0, min(1, current_hp / max_hp))
        height = 10  # 增加厚度
        
        # 1. 绘制背景阴影/底框
        bg_rect = (x, y, x + width, y + height)
        draw_rounded_rectangle(draw, bg_rect, corner_radius=5, fill=(220, 220, 220))
        
        # 2. 判定颜色 (修正逻辑：>50%绿, 20%-50%黄, <20%红)
        if ratio > 0.5:
            bar_color = (76, 175, 80)   # 绿色
        elif ratio > 0.2:
            bar_color = (255, 193, 7)   # 黄色
        else:
            bar_color = (255, 67, 54)   # 红色
        
        # 3. 绘制进度条
        if ratio > 0:
            bar_w = int(width * ratio)
            # 左对齐绘制
            # draw_rounded_rectangle supports RGBA if fill is tuple
            draw_rounded_rectangle(draw, (x, y, x + bar_w, y + height), corner_radius=5, fill=bar_color)
            
            # Gloss Effect (Top 30%)
            gloss_h = 3
            draw_rounded_rectangle(draw, (x, y, x + bar_w, y + gloss_h), corner_radius=2, fill=(255, 255, 255, 100))
            
        # 4. 绘制 HP 数值 (精致化处理)
        hp_font = self.fonts["small"]
        hp_text = f"{current_hp}/{max_hp}"
        
        # 根据左右位置决定数字是在左还是在右
        if not is_right:
            draw.text((x, y + height + 4), hp_text, fill=self.cfg["colors"]["text_sub"], font=hp_font)
        else:
            # 右侧对齐
            text_w = hp_font.getlength(hp_text)
            draw.text((x + width - text_w, y + height + 4), hp_text, fill=self.cfg["colors"]["text_sub"], font=hp_font)

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

    def _draw_turn_header(self, draw: ImageDraw.Draw, x: int, y: int, turn_num: int):
        """绘制回合标题"""
        text = f"第 {turn_num} 回合"
        font = self.fonts["small"]
        w = int(font.getlength(text))
        h = 20 # fixed height for header
        
        # 绘制圆角矩形底色
        # Centered or aligned? Providing x is start X.
        # User requested: light background.
        bg_color = (240, 240, 240)
        text_color = (100, 100, 100)
        
        draw_rounded_rectangle(draw, (x, y, x + w + 20, y + h), corner_radius=10, fill=bg_color)
        draw.text((x + 10, y + 2), text, fill=text_color, font=font)

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

    def _draw_rich_text_line(self, draw: ImageDraw.Draw, x: int, y: int, 
                            content: Any, font: ImageFont.FreeTypeFont):
        """绘制单行文本（支持普通字符串或富文本片段列表）"""
        
        # Determine Icon and Full Text
        full_text = ""
        if isinstance(content, str):
            full_text = content
        elif isinstance(content, list):
            full_text = "".join([seg.get('text', '') for seg in content])
        
        # Highlighting "Super Effective"
        if "效果绝佳" in full_text:
            # Draw highlight background
            # Approx width: entire card width minus padding? Or just text width?
            # Using text width is safer.
            text_w = font.getlength(full_text) + 20 # +Icon space
            draw.rectangle((x - 2, y, x + text_w, y + 16), fill=(255, 0, 0, 20)) # Very Light Red

        icon = "•"
        if any(k in full_text for k in ["used", "使用了", "attacked"]):
            icon = "⚔️"
        elif any(k in full_text for k in ["restored", "回复", "health"]):
            icon = "💚"
        elif any(k in full_text for k in ["paralyzed", "burned", "poisoned", "asleep", "frozen", "confused", "麻痹", "灼伤", "中毒", "睡眠", "冰冻", "混乱"]):
            icon = "⚠️"
        elif any(k in full_text for k in ["fainted", "倒下", "defeated"]):
            icon = "💀"
            
        current_x = x
        
        # 绘制图标
        bullet = f"{icon} "
        draw.text((current_x, y), bullet, fill=self.cfg["colors"]["text_main"], font=font)
        current_x += font.getlength(bullet)

        if isinstance(content, str):
            draw.text((current_x, y), f"{content}", fill=self.cfg["colors"]["text_main"], font=font)
        elif isinstance(content, list):
             for segment in content:
                text = segment.get('text', '')
                color_key = segment.get('color', 'default')
                
                # Bolding Move Names (User Request: "colored move segments")
                stroke_width = 0
                
                # 解析颜色
                if color_key == 'default':
                    fill_color = self.cfg["colors"]["text_main"]
                elif color_key.startswith('type_'):
                    type_en = color_key.replace('type_', '')
                    fill_color = self._get_type_color(type_en)
                    # Bold usage of Moves
                    stroke_width = 1 
                elif color_key == 'red' or color_key == 'hp':
                    fill_color = COLOR_ERROR
                elif color_key == 'green':
                    fill_color = COLOR_SUCCESS
                elif color_key == 'blue':
                    fill_color = (66, 133, 244) # Google Blueish
                else:
                    fill_color = self.cfg["colors"]["text_main"]
                
                draw.text((current_x, y), text, fill=fill_color, font=font, stroke_width=stroke_width)
                current_x += font.getlength(text)

def draw_battle_log(log_data: Dict[str, Any]) -> Image.Image:
    drawer = BattleDrawer()
    return drawer.draw(log_data)
