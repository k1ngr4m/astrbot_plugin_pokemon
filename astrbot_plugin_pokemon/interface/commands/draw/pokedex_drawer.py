import math
import os
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter

from .base import BaseDrawer
from .constants import POKEDEX_CONFIG
from .styles import (
    COLOR_TITLE, COLOR_TEXT_DARK, COLOR_TEXT_GRAY, COLOR_CARD_BG,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, TYPE_COLORS,
    load_font, draw_rounded_rectangle, lighten_color
)
from .gradient_utils import create_vertical_gradient


class PokedexDrawer(BaseDrawer):
    def __init__(self):
        super().__init__(POKEDEX_CONFIG)

    def _load_pokemon_sprite(self, pokemon_id: int, size=(60, 60), pokemon_seen: bool = True) -> Image.Image:
        if pokemon_seen:
            cache_key = f"{pokemon_id}_{size}"
            if cache_key in self.sprite_cache:
                return self.sprite_cache[cache_key]

            try:
                sprite = super()._load_pokemon_sprite(pokemon_id, size)
                self.sprite_cache[cache_key] = sprite
                return sprite
            except FileNotFoundError:
                return Image.new("RGBA", size, (0,0,0,0))
        else:
            # 未遇见宝可梦的情况：返回灰色遮罩效果
            sprite = Image.new("RGBA", size, (150,150,150,255))
            draw = ImageDraw.Draw(sprite)

            # 绘制问号，表示未遇见
            question_mark = "?"
            font = self.fonts["name"] if "name" in self.fonts else self.fonts["small"]  # 回退到 small 字体
            bbox = font.getbbox(question_mark)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # 居中绘制问号
            x = (size[0] - text_w) // 2
            y = (size[1] - text_h) // 2
            draw.text((x, y), question_mark, fill=(255, 255, 255, 255), font=font)

            return sprite

    def draw_pokedex_list(self, data: Dict[str, Any]) -> Image.Image:
        # data: {list: [{id, name, caught, seen, sprite_id}], page_info: {current_page, total_count, caught_count, seen_count, total_pages}}
        pokemon_list = data.get("list", [])
        page_info = data.get("page_info", {})

        # Calculate Height
        rows = math.ceil(len(pokemon_list) / self.cfg["cols"])
        content_h = max(200, rows * (self.cfg["card_h"] + self.cfg["row_gap"]))  # 最小高度200
        header_h = 100
        footer_h = 60
        total_h = header_h + content_h + footer_h + self.cfg["padding"] * 2

        # BG
        image = create_vertical_gradient(self.width, total_h, *self.cfg["bg_colors"])
        overlay = Image.new("RGBA", image.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)

        # Header
        cx = self.width // 2
        draw.text((cx, 50), "宝可梦图鉴", fill=COLOR_TITLE, font=self.fonts["title"], anchor="mm")

        # 显示进度信息
        caught_count = page_info.get('caught_count', 0)
        seen_count = page_info.get('seen_count', 0)
        total_count = page_info.get('total_count', 0)
        current_page = page_info.get('current_page', 1)
        total_pages = page_info.get('total_pages', 1)

        progress_text = f"进度: 已捕捉 {caught_count} / 已遇见 {seen_count} / 共 {total_count} 个宝可梦 | 第 {current_page}/{total_pages} 页"
        draw.text((cx, 85), progress_text, fill=COLOR_TEXT_GRAY, font=self.fonts["subtitle"], anchor="mm")

        # Grid
        pad = self.cfg["padding"]
        col_w = (self.width - pad * 2 - self.cfg["col_gap"] * (self.cfg["cols"] - 1)) // self.cfg["cols"]
        start_y = header_h + pad + 10

        for i, p in enumerate(pokemon_list):
            row = i // self.cfg["cols"]
            col = i % self.cfg["cols"]
            x = pad + col * (col_w + self.cfg["col_gap"])
            y = start_y + row * (self.cfg["card_h"] + self.cfg["row_gap"])

            self._draw_pokedex_item_card(draw, overlay, x, y, col_w, self.cfg["card_h"], p)

        # Footer
        fy = total_h - 40
        draw.text((cx, fy), "使用 /图鉴 M[名字/ID] 查看详细信息", fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="mm")

        image.paste(overlay, (0,0), overlay)
        return image

    def _draw_pokedex_item_card(self, draw, overlay, x, y, w, h, p):
        # Card BG
        draw_rounded_rectangle(draw, (x, y, x+w, y+h), corner_radius=10, fill=COLOR_CARD_BG)

        # Sprite Center
        sprite_id = p.get('sprite_id', p.get('id', 1))
        pokemon_seen = p.get('seen', False)
        sprite = self._load_pokemon_sprite(sprite_id, size=(50, 50), pokemon_seen=pokemon_seen)
        sprite_x = x + (w - 50) // 2
        sprite_y = y + 8
        overlay.paste(sprite, (sprite_x, sprite_y), sprite)

        # Number: #001
        pokemon_id = p.get('id', 0)
        id_text = f"#{pokemon_id:04d}"
        id_bbox = self.fonts["number"].getbbox(id_text)
        id_w = id_bbox[2] - id_bbox[0]
        draw.text((x + 5, y + 5), id_text, fill=COLOR_TEXT_GRAY, font=self.fonts["number"])

        # Status Icon (Right top)
        if p.get('caught', False):
            status_icon = "🟢"  # 已捕捉
        elif p.get('seen', False):
            status_icon = "👁️"  # 已遇见
        else:
            status_icon = "❓"  # 未知
        draw.text((x + w - 30, y + 5), status_icon, fill=COLOR_TEXT_DARK, font=self.fonts["icon"])

        # Name (Center bottom)
        name = p.get('name', '???')
        name_bbox = self.fonts["name"].getbbox(name)
        name_w = name_bbox[2] - name_bbox[0]
        name_x = x + (w - name_w) // 2
        name_y = y + h - 25
        name_color = COLOR_TEXT_DARK if p.get('seen', False) else COLOR_TEXT_GRAY
        draw.text((name_x, name_y), name, fill=name_color, font=self.fonts["name"])


def draw_pokedex_list(data: Dict) -> Image.Image:
    return PokedexDrawer().draw_pokedex_list(data)