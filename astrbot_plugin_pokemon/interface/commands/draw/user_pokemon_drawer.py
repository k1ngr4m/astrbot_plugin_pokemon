import math
import os
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter

from .styles import (
    COLOR_TITLE, COLOR_TEXT_DARK, COLOR_TEXT_GRAY, COLOR_CARD_BG,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, TYPE_COLORS,
    load_font, draw_rounded_rectangle, lighten_color
)
from .gradient_utils import create_vertical_gradient

# --- 配置 ---
LIST_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_h": 100,
    "cols": 2,
    "col_gap": 20,
    "row_gap": 15,
    "bg_colors": ((240, 248, 255), (255, 255, 255))
}

DETAIL_CONFIG = {
    "width": 800,
    "padding": 40,
    "bg_colors": ((255, 250, 240), (255, 255, 255))
}

class BaseDrawer:
    def __init__(self, cfg):
        self.cfg = cfg
        self.width = cfg["width"]
        self.fonts = {
            "title": load_font(32),
            "subtitle": load_font(20),
            "card_title": load_font(24),
            "normal": load_font(18),
            "small": load_font(15),
            "small_bold": load_font(16),
        }
        self.sprite_cache = {}

    def _load_pokemon_sprite(self, pokemon_id: int, size=(80, 80)) -> Image.Image:
        base_path = os.path.dirname(__file__)
        sprite_path = os.path.abspath(os.path.join(
            base_path, "..", "..", "..", "..", "assets", "sprites", "front", f"{pokemon_id}.png"
        ))
        cache_key = f"{pokemon_id}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        try:
            sprite = Image.open(sprite_path).convert("RGBA")
            sprite = sprite.resize(size, Image.Resampling.LANCZOS)
            self.sprite_cache[cache_key] = sprite
            return sprite
        except FileNotFoundError:
            return Image.new("RGBA", size, (0,0,0,0))
    
    def _draw_type_badge(self, draw, x, y, type_text):
        font = self.fonts["small"]
        bg_col = TYPE_COLORS.get(type_text, (150, 150, 150))
        text_w = font.getlength(type_text)
        w, h = int(text_w + 16), 22
        draw_rounded_rectangle(draw, (x, y, x + w, y + h), corner_radius=10, fill=bg_col)
        draw.text((x + w/2, y + h/2), type_text, fill=(255, 255, 255), font=font, anchor="mm")
        return w

class UserPokemonListDrawer(BaseDrawer):
    def __init__(self):
        super().__init__(LIST_CONFIG)

    def draw(self, data: Dict[str, Any]) -> Image.Image:
        # data: {total_count, page, total_pages, list: [{id, name, level, gender, hp, max_hp, sprite_id, types...}]}
        pokemon_list = data.get("list", [])
        
        # Calculate Height
        rows = math.ceil(len(pokemon_list) / self.cfg["cols"])
        content_h = rows * (self.cfg["card_h"] + self.cfg["row_gap"])
        header_h = 100
        footer_h = 60
        total_h = header_h + content_h + footer_h + self.cfg["padding"] * 2
        
        # BG
        image = create_vertical_gradient(self.width, total_h, *self.cfg["bg_colors"])
        overlay = Image.new("RGBA", image.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        
        # Header
        cx = self.width // 2
        draw.text((cx, 50), "我的宝可梦", fill=COLOR_TITLE, font=self.fonts["title"], anchor="mm")
        draw.text((cx, 85), f"第 {data.get('page', 1)} / {data.get('total_pages', 1)} 页 (共 {data.get('total_count', 0)} 只)", 
                  fill=COLOR_TEXT_GRAY, font=self.fonts["subtitle"], anchor="mm")
        
        # Grid
        pad = self.cfg["padding"]
        col_w = (self.width - pad * 2 - self.cfg["col_gap"]) // 2
        start_y = header_h + pad + 10 # Slight visual tweak
        
        for i, p in enumerate(pokemon_list):
            row = i // 2
            col = i % 2
            x = pad + col * (col_w + self.cfg["col_gap"])
            y = start_y + row * (self.cfg["card_h"] + self.cfg["row_gap"])
            
            self._draw_item_card(draw, overlay, x, y, col_w, self.cfg["card_h"], p)
            
        # Footer
        fy = total_h - 40
        draw.text((cx, fy), "使用 /我的宝可梦 <ID> 查看详情 | /我的宝可梦 P<页码> 翻页", 
                  fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="mm")
        
        image.paste(overlay, (0,0), overlay)
        return image

    def _draw_item_card(self, draw, overlay, x, y, w, h, p):
        # Shadow & BG
        draw_rounded_rectangle(draw, (x, y, x+w, y+h), corner_radius=12, fill=COLOR_CARD_BG)
        # Sprite
        sprite = self._load_pokemon_sprite(p.get('sprite_id', 1), size=(70, 70))
        overlay.paste(sprite, (x + 10, y + 15), sprite)
        
        # Info
        ix = x + 90
        iy = y + 15
        
        # Name + Gender
        name = p.get('name', '未知')
        gender = p.get('gender', '')
        # Gender Color
        g_col = (50, 150, 255) if 'm' in gender.lower() or '♂' in gender else (255, 100, 150)
        if 'N' in gender or '⚲' in gender: g_col = COLOR_TEXT_GRAY
        
        draw.text((ix, iy), name, fill=COLOR_TEXT_DARK, font=self.fonts["card_title"])
        nw = self.fonts["card_title"].getlength(name)
        draw.text((ix + nw + 5, iy + 2), gender, fill=g_col, font=self.fonts["subtitle"])
        
        # Level
        draw.text((ix, iy + 35), f"Lv.{p.get('level', 1)}", fill=COLOR_TEXT_GRAY, font=self.fonts["normal"])

        # HP Text (Simple)
        cur, max_hp = p.get('current_hp', 0), p.get('max_hp', 0)
        draw.text((ix + 80, iy + 35), f"HP {cur}/{max_hp}", fill=COLOR_SUCCESS, font=self.fonts["normal"])
        
        # ID Badge (Top Right)
        id_txt = f"#{p.get('id', 0)}"
        iw = self.fonts["small"].getlength(id_txt) + 10
        draw_rounded_rectangle(draw, (x+w-iw-10, y+10, x+w-10, y+30), corner_radius=5, fill=(240, 240, 240))
        draw.text((x+w-10-iw/2, y+20), id_txt, fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="mm")
        
        # Types (Bottom)
        ty = y + 68
        ctx = ix
        for t in p.get('types', []):
            tw = self._draw_type_badge(draw, ctx, ty, t)
            ctx += tw + 5

class UserPokemonDetailDrawer(BaseDrawer):
    def __init__(self):
        super().__init__(DETAIL_CONFIG)

    def draw(self, p: Dict[str, Any]) -> Image.Image:
        # Layout Pre-calc
        total_h = 750 # Estimated
        
        image = create_vertical_gradient(self.width, total_h, *self.cfg["bg_colors"])
        overlay = Image.new("RGBA", image.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        
        pad = self.cfg["padding"]
        cx = self.width // 2
        
        # 1. Header (Sprite + Info)
        sx, sy = pad + 20, pad + 20
        sprite = self._load_pokemon_sprite(p.get('sprite_id', 1), size=(180, 180))
        overlay.paste(sprite, (sx, sy), sprite)
        
        ix = sx + 200
        iy = sy + 20
        
        # Name
        draw.text((ix, iy), p.get('name', ''), fill=COLOR_TITLE, font=self.fonts["title"])
        
        # Lv + Gender
        info_text = f"Lv.{p.get('level')}   {p.get('gender')}"
        draw.text((ix, iy + 45), info_text, fill=COLOR_TEXT_DARK, font=self.fonts["card_title"])
        
        # Type Badges (Inline)
        tx = ix + self.fonts["card_title"].getlength(info_text) + 20
        ty = iy + 48  # Align with baseline area
        for t in p.get('types', []):
            w = self._draw_type_badge(draw, tx, ty, t)
            tx += w + 8
        
        # Attrs
        rows = [
            f"性格: {p.get('nature')}   特性: {p.get('ability')}",
            f"经验: {p.get('exp')}",
            f"捕获时间: {p.get('caught_time', '未知')}"
        ]
        curr_y = iy + 85
        for r in rows:
            draw.text((ix, curr_y), r, fill=COLOR_TEXT_GRAY, font=self.fonts["normal"])
            curr_y += 25
            
        # Separator (Dynamic)
        line_y = max(sy + 185, curr_y + 15)
        draw.line((pad, line_y, self.width-pad, line_y), fill=(220, 220, 220), width=2)
        
        # 2. Stats Table (IV/EV)
        table_y = line_y + 30
        draw.text((pad, table_y), "能力详情 (能力值 | 个体值 IV | 努力值 EV)", fill=COLOR_TITLE, font=self.fonts["card_title"])
        
        # Headers
        headers = ["属性", "能力值", "IV (个体值)", "EV (努力值)"]
        col_ws = [120, 150, 150, 150]
        hx = pad + 20
        hy = table_y + 40
        for i, h in enumerate(headers):
            draw.text((hx, hy), h, fill=COLOR_TEXT_GRAY, font=self.fonts["small_bold"])
            hx += col_ws[i]
            
        # Rows
        stats = p.get('stats_detail', []) # expecting list of (label, val, iv, ev)
        ry = hy + 30
        for row in stats:
            rx = pad + 20
            # Label
            draw.text((rx, ry), row['label'], fill=COLOR_TEXT_DARK, font=self.fonts["normal"])
            rx += col_ws[0]
            # Val (Bar?)
            draw.text((rx, ry), str(row['val']), fill=COLOR_TITLE, font=self.fonts["normal"])
            rx += col_ws[1]
            # IV
            iv_col = COLOR_SUCCESS if row['iv'] == 31 else (COLOR_WARNING if row['iv'] > 25 else COLOR_TEXT_DARK)
            draw.text((rx, ry), f"{row['iv']}/31", fill=iv_col, font=self.fonts["normal"])
            rx += col_ws[2]
            # EV
            ev_col = COLOR_SUCCESS if row['ev'] >= 252 else COLOR_TEXT_DARK
            draw.text((rx, ry), str(row['ev']), fill=ev_col, font=self.fonts["normal"])
            
            ry += 35
            
        # 3. Moves
        moves_y = ry + 20
        draw.text((pad, moves_y), "招式列表", fill=COLOR_TITLE, font=self.fonts["card_title"])
        
        moves = p.get('moves', [])
        # Grid 2x2
        mx_start = pad
        my_start = moves_y + 40
        
        for i, move in enumerate(moves):
            r = i // 2
            c = i % 2
            
            mx = mx_start + c * 350
            my = my_start + r * 60
            
            # Move Card
            draw_rounded_rectangle(draw, (mx, my, mx+330, my+50), corner_radius=8, fill=(245, 245, 250))
            
            m_name = move.get('name', '---')
            m_type = move.get('type', '一般')
            m_pp = f"PP {move.get('pp', 0)}/{move.get('max_pp', 0)}"
            
            # Type Icon
            tw = self._draw_type_badge(draw, mx+10, my+14, m_type)
            # Name
            draw.text((mx+10+tw+10, my+14), m_name, fill=COLOR_TEXT_DARK, font=self.fonts["normal"])
            # PP
            draw.text((mx+320, my+16), m_pp, fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="ra")

        image.paste(overlay, (0,0), overlay)
        return image

def draw_user_pokemon_list(data: Dict) -> Image.Image:
    return UserPokemonListDrawer().draw(data)

def draw_user_pokemon_detail(data: Dict) -> Image.Image:
    return UserPokemonDetailDrawer().draw(data)
