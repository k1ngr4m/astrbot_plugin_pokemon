import math
import os
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter

from .base import BaseDrawer
from .constants import TEAM_CONFIG
from .styles import (
    COLOR_TITLE, COLOR_TEXT_DARK, COLOR_TEXT_GRAY, COLOR_CARD_BG,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, TYPE_COLORS,
    load_font, draw_rounded_rectangle, lighten_color
)
from .gradient_utils import create_vertical_gradient


class TeamDrawer(BaseDrawer):
    def __init__(self):
        super().__init__(TEAM_CONFIG)

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

            self._draw_item_card(draw, overlay, x, y, col_w, self.cfg["card_h"], p)

        # Footer
        fy = total_h - 40
        draw.text((cx, fy), "使用 /设置队伍 <ID> 设置队伍",
                  fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="mm")

        image.paste(overlay, (0,0), overlay)
        return image


def draw_team_list(data: Dict) -> Image.Image:
    return TeamDrawer().draw_team_list(data)