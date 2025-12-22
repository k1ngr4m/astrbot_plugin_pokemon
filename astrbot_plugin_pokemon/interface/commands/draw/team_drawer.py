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
TEAM_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_h": 125, # Increased height to fit Nature/Ability
    "cols": 2,
    "col_gap": 20,
    "row_gap": 15,
    "bg_colors": ((240, 248, 255), (255, 255, 255))
}

class TeamDrawer:
    def __init__(self):
        self.cfg = TEAM_CONFIG
        self.width = TEAM_CONFIG["width"]
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

    def draw_team_list(self, data: Dict[str, Any]) -> Image.Image:
        # data: {list: [{id, name, level, gender, hp, max_hp, sprite_id, types...}]}
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
        draw.text((cx, 50), "我的队伍", fill=COLOR_TITLE, font=self.fonts["title"], anchor="mm")
        draw.text((cx, 85), f"队伍成员 ({len(pokemon_list)}/6)",
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

            # 标记是否为队长（第一个）
            is_leader = i == 0
            self._draw_team_item_card(draw, overlay, x, y, col_w, self.cfg["card_h"], p, is_leader)

        # Footer
        fy = total_h - 40
        draw.text((cx, fy), "使用 /设置队伍 <ID> 设置队伍",
                  fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="mm")

        image.paste(overlay, (0,0), overlay)
        return image

    def _draw_team_item_card(self, draw, overlay, x, y, w, h, p, is_leader=False):
        # Shadow & BG
        draw_rounded_rectangle(draw, (x, y, x+w, y+h), corner_radius=12, fill=COLOR_CARD_BG)

        # Sprite
        sprite = self._load_pokemon_sprite(p.get('sprite_id', 1), size=(70, 70))
        overlay.paste(sprite, (x + 10, y + 15), sprite)

        # Info 起始坐标
        ix = x + 95
        iy = y + 15

        # 1. 名字与性别 (iy + 0)
        name = p.get('name', '未知')
        gender = p.get('gender', '')
        g_col = (50, 150, 255) if 'm' in gender.lower() or '♂' in gender else (255, 100, 150)
        if 'N' in gender or '⚲' in gender: g_col = COLOR_TEXT_GRAY

        draw.text((ix, iy), name, fill=COLOR_TEXT_DARK, font=self.fonts["card_title"])

        nw = self.fonts["card_title"].getlength(name)
        draw.text((ix + nw + 5, iy + 2), gender, fill=g_col, font=self.fonts["subtitle"])

        # 2. 属性徽章 (下移至 iy + 32)
        ty = iy + 32
        tx = ix
        for t in p.get('types', []):
            tw = self._draw_type_badge(draw, tx, ty, t)
            tx += tw + 5

        # 3. 性格与特性 (下移至 iy + 60，避开上方徽章)
        nature = p.get('nature', '未知')
        ability = p.get('ability', '未知')
        na_text = f"{nature} · {ability}"
        draw.text((ix, iy + 60), na_text, fill=COLOR_TEXT_DARK, font=self.fonts["small"])

        # 4. HP 血条 (下移至 iy + 82，确保不遮挡文字)
        cur, max_hp = p.get('current_hp', 0), p.get('max_hp', 0)
        ratio = max(0, min(1, cur / max_hp)) if max_hp > 0 else 0
        bar_w, bar_h = 140, 6
        bar_x, bar_y = ix, iy + 82  # 关键改动：从 62 改为 82

        draw_rounded_rectangle(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), 3, fill=(230, 230, 230))
        bar_col = COLOR_SUCCESS if ratio > 0.5 else (COLOR_WARNING if ratio > 0.2 else COLOR_ERROR)
        if ratio > 0:
            draw_rounded_rectangle(draw, (bar_x, bar_y, bar_x + int(bar_w * ratio), bar_y + bar_h), 3, fill=bar_col)

        # 5. 等级与数值 (下移至 iy + 95)
        draw.text((ix, iy + 95), f"Lv.{p.get('level', 1)}", fill=COLOR_TEXT_GRAY, font=self.fonts["small"])
        draw.text((ix + 60, iy + 95), f"HP {cur}/{max_hp}", fill=COLOR_TEXT_DARK, font=self.fonts["small"])

        # ID Badge (Top Right)
        id_txt = f"#{p.get('id', 0)}"
        iw = self.fonts["small"].getlength(id_txt) + 10
        draw_rounded_rectangle(draw, (x+w-iw-10, y+10, x+w-10, y+30), corner_radius=5, fill=(240, 240, 240))
        draw.text((x+w-10-iw/2, y+20), id_txt, fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="mm")


def draw_team_list(data: Dict) -> Image.Image:
    return TeamDrawer().draw_team_list(data)