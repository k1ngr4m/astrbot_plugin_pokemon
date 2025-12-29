import math
import os
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter

from .base import BaseDrawer, STAT_MAP
from .constants import LIST_CONFIG, DETAIL_CONFIG
from .styles import (
    COLOR_TITLE, COLOR_TEXT_DARK, COLOR_TEXT_GRAY, COLOR_CARD_BG,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, TYPE_COLORS,
    load_font, draw_rounded_rectangle, lighten_color
)
from .gradient_utils import create_vertical_gradient


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


class UserPokemonDetailDrawer(BaseDrawer):
    def __init__(self):
        super().__init__(DETAIL_CONFIG)

    def draw(self, p: Dict[str, Any]) -> Image.Image:
        pad = self.cfg["padding"]
        # --- 【优化】将起始 y 坐标上移，减少顶部空白 ---
        sy = pad
        sprite_size = 180

        # 为了计算动态高度，我们先预估位置
        # 计算 Moves 列表结束的位置
        moves_count = len(p.get('moves', []))
        moves_rows = math.ceil(moves_count / 2)
        # 预估高度 = 头部(200) + 属性表(300) + 技能标题(60) + 技能行(rows * 60) + 底部边距
        dynamic_h = sy + 200 + 300 + 60 + (moves_rows * 70) + pad
        total_h = max(700, int(dynamic_h))  # 最小保证 700

        image = create_vertical_gradient(self.width, total_h, *self.cfg["bg_colors"])
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))  # 透明背景
        draw = ImageDraw.Draw(overlay)

        # 1. Header
        sprite = self._load_pokemon_sprite(p.get('sprite_id', 1), size=(sprite_size, sprite_size))
        overlay.paste(sprite, (pad, sy), sprite)

        ix = pad + sprite_size + 20
        # --- 【优化】文字信息也随之上移 ---
        iy = sy + 10

        # Name
        draw.text((ix, iy), p.get('name', ''), fill=COLOR_TITLE, font=self.fonts["title"])

        # Species Name (显示物种名称，紧接在昵称下方)
        species_name = p.get('species_name', '')
        if species_name:
            species_y = iy + 35  # 紧接在昵称下方
            draw.text((ix, species_y), f"({species_name})", fill=COLOR_TEXT_GRAY, font=self.fonts["normal"])
            ty = species_y + 35  # 更新类型标签的Y坐标
        else:
            ty = iy + 45  # 没有物种名称时的原始坐标

        # 独立一行的属性展示
        tx = ix
        for t in p.get('types', []):
            tw = self._draw_type_badge(draw, tx, ty, t)
            tx += tw + 8

        # 信息描述下移
        info_y = ty + 35
        draw.text((ix, info_y), f"Lv.{p.get('level')}  {p.get('gender')}", fill=COLOR_TEXT_DARK, font=self.fonts["card_title"])

        rows = [
            f"性格: {p.get('nature')}   特性: {p.get('ability')}",
            f"持有物: {p.get('held_item_name', '无')}",  # 持有物信息
            f"捕获时间: {p.get('caught_time', '未知')}"
        ]
        curr_y = info_y + 35
        for r in rows:
            draw.text((ix, curr_y), r, fill=COLOR_TEXT_GRAY, font=self.fonts["normal"])
            curr_y += 28

        # 分割线动态位置
        line_y = max(sy + sprite_size + 10, curr_y + 20)
        draw.line((pad, line_y, self.width - pad, line_y), fill=(220, 220, 220), width=2)

        # Optional: Background Tint based on Primary Type
        if p.get('types'):
            # 如果有多种类型，混合两种颜色；否则使用单一类型颜色
            primary_type = p.get('types')[0]
            if len(p.get('types', [])) > 1:
                secondary_type = p.get('types')[1]
                primary_col = TYPE_COLORS.get(primary_type, (200, 200, 200))
                secondary_col = TYPE_COLORS.get(secondary_type, (200, 200, 200))
                # 混合两种颜色，取平均值
                mixed_col = tuple(int((c1 + c2) / 2) for c1, c2 in zip(primary_col, secondary_col))
                tint_col = mixed_col
            else:
                tint_col = TYPE_COLORS.get(primary_type, (200, 200, 200))

            # Create a very light tint
            tint_h = int(line_y)
            tint_layer = Image.new("RGBA", (self.width, tint_h), (*tint_col, 40))
            image.paste(tint_layer, (0, 0), tint_layer)


        # 2. Stats Table (IV/EV)
        table_y = line_y + 30
        draw.text((pad, table_y), "能力详情", fill=COLOR_TITLE, font=self.fonts["card_title"])

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