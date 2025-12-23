"""
宝可梦图鉴详情图片生成器 - 竖向精美版
"""
import math
import os
from typing import Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFilter
from PIL.ImageFont import ImageFont

# 确保 styles.py 中已包含美化所需的函数和常量
from .styles import (
    COLOR_TITLE, COLOR_CMD, COLOR_LINE, COLOR_SHADOW,
    COLOR_TEXT_DARK, COLOR_CARD_BG, COLOR_CARD_BORDER,
    load_font, COLOR_WARNING, COLOR_ERROR, COLOR_SUCCESS,
    TYPE_COLORS, lighten_color, draw_rounded_rectangle
)
from .gradient_utils import create_vertical_gradient

# --- 配置常量 ---
POKEDEX_DETAIL_CONFIG = {
    "width": 850,             # 竖向宽度
    "padding": 40,
    "card_radius": 20,        # 卡片圆角
    "shadow_color": (0, 0, 0, 40),
    "sprite_size": (240, 240), # 精灵图尺寸
    "colors": {
        "card_bg": (255, 255, 255, 240),
        "text_desc": (80, 80, 80),
        "stats_bar_bg": (235, 235, 235),
    },
    "stats_bar_height": 18,
}

class PokedexDetailImageGenerator:
    def __init__(self):
        self.cfg = POKEDEX_DETAIL_CONFIG
        self.width = self.cfg["width"]
        self.fonts = self._load_fonts()
        self.sprite_cache = {}

    def _load_fonts(self):
        return {
            "title_id": load_font(24),
            "title_name": load_font(42),
            "badge": load_font(16),
            "section_title": load_font(24),
            "normal_bold": load_font(18),
            "normal": load_font(16),
            "stats_val": load_font(14),
            "desc": load_font(18),
        }

    def _measure_text(self, text, font) -> Tuple[int, int]:
        if text is None: text = ""
        bbox = font.getbbox(text)
        if bbox is None: return 0, 0
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def _load_pokemon_sprite(self, pokemon_id: int, pokemon_seen: bool = True) -> Image.Image:
        """加载宝可梦精灵图片"""
        base_path = os.path.dirname(__file__)
        # 保持修复后的路径 (4层回退)
        sprite_path = os.path.abspath(os.path.join(
            base_path,
            "..", "..", "..", "..", "assets", "sprites", "front", f"{pokemon_id}.png"
        ))

        if pokemon_seen:
            if pokemon_id in self.sprite_cache:
                return self.sprite_cache[pokemon_id]

            try:
                sprite = Image.open(sprite_path).convert("RGBA")
                sprite = sprite.resize(self.cfg["sprite_size"], Image.Resampling.LANCZOS)
                self.sprite_cache[pokemon_id] = sprite
                return sprite
            except FileNotFoundError:
                placeholder = Image.new("RGBA", self.cfg["sprite_size"], (0,0,0,0))
                return placeholder
        else:
            # 未遇见宝可梦的情况：返回灰色遮罩效果
            sprite = Image.new("RGBA", self.cfg["sprite_size"], (150,150,150,255))
            draw = ImageDraw.Draw(sprite)

            # 绘制一个问号来表示未遇见
            question_mark = "?"
            font = self.fonts["title_name"]  # 使用较大的字体
            bbox = font.getbbox(question_mark)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # 居中绘制问号
            x = (self.cfg["sprite_size"][0] - text_w) // 2
            y = (self.cfg["sprite_size"][1] - text_h) // 2
            draw.text((x, y), question_mark, fill=(255, 255, 255, 255), font=font)

            return sprite

    def _draw_shadow(self, image: Image.Image, xy, radius, blur=15, offset=(0, 5)):
        shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        x1, y1, x2, y2 = xy
        shadow_draw.rounded_rectangle(
            (x1 + offset[0], y1 + offset[1], x2 + offset[0], y2 + offset[1]),
            radius=radius,
            fill=self.cfg["shadow_color"]
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
        image.paste(shadow, (0, 0), shadow)

    def _draw_type_badge(self, draw: ImageDraw.Draw, x: int, y: int, type_name: str):
        text = type_name
        font = self.fonts["badge"]
        text_w, text_h = self._measure_text(text, font)

        pad_x, pad_y = 14, 8
        badge_w = text_w + pad_x * 2
        badge_h = text_h + pad_y * 2
        radius = badge_h // 2

        color = TYPE_COLORS.get(type_name, (150, 150, 150))

        draw_rounded_rectangle(draw, (x, y, x + badge_w, y + badge_h), radius, fill=color)
        draw.text((x + badge_w // 2, y + badge_h // 2), text, fill=(255, 255, 255), font=font, anchor="mm")
        return badge_w

    def _draw_stats_bar_fancy(self, draw: ImageDraw.Draw, x: int, y: int, width: int,
                             value: int, max_value: int, color: Tuple[int, int, int]):
        height = self.cfg["stats_bar_height"]
        radius = height // 2

        draw_rounded_rectangle(draw, (x, y, x + width, y + height), radius, fill=self.cfg["colors"]["stats_bar_bg"])
        current_width = max(height, int((value / max_value) * width))
        draw_rounded_rectangle(draw, (x, y, x + current_width, y + height), radius, fill=color)

        text = str(value)
        draw.text((x + width + 15, y + height // 2), text, fill=COLOR_TEXT_DARK, font=self.fonts["stats_val"], anchor="lm")

    def _wrap_text(self, text: str, font: ImageFont, max_width: int) -> list:
        # 保持修复后的换行逻辑
        lines = []
        words = list(text)
        current_line = ""
        for word in words:
            test_line = current_line + word
            width, _ = self._measure_text(test_line, font)
            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    lines.append(test_line)
                    current_line = ""
        if current_line:
            lines.append(current_line)
        return lines

    def _calculate_layout(self, pokemon_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算竖向布局"""
        pad = self.cfg["padding"]
        content_width = self.width - pad * 2

        # --- 顶部区域 (精灵图 + 基础信息) ---
        top_section_y = pad
        sprite_w, sprite_h = self.cfg["sprite_size"]

        # 左侧：精灵图
        sprite_x = pad
        sprite_y = top_section_y + 20

        # 右侧：基础信息
        info_x = sprite_x + sprite_w + 40
        info_y = top_section_y + 20

        # ID 和 名称
        id_h = self._measure_text("#0000", self.fonts["title_id"])[1]
        name_h = self._measure_text("名字", self.fonts["title_name"])[1]

        # 类型徽章位置
        types_y = info_y + id_h + name_h + 30
        types_height = 40

        # 身高体重位置
        hw_y = types_y + types_height + 25
        hw_height = 30

        top_section_height = max(sprite_h + 40, hw_y + hw_height - top_section_y)

        # --- 中部区域 (种族值卡片) ---
        stats_card_y = top_section_y + top_section_height + 30
        stats_content_pad = 30

        stats_title_y = stats_card_y + stats_content_pad
        stats_start_y = stats_title_y + 45
        stats_row_h = 36
        stats_bar_w = content_width - stats_content_pad * 2 - 80

        stats_card_height = (stats_start_y - stats_card_y) + (stats_row_h * 6) + stats_content_pad

        # --- 底部区域 (描述和状态卡片) ---
        desc_card_y = stats_card_y + stats_card_height + 30
        desc_content_pad = 30

        desc_title_y = desc_card_y + desc_content_pad
        desc_text_y = desc_title_y + 45

        desc_max_w = content_width - desc_content_pad * 2
        desc_lines = self._wrap_text(pokemon_data.get("description", ""),
                                    self.fonts["desc"], desc_max_w)
        desc_text_height = len(desc_lines) * 30

        # 状态栏放在描述下方
        status_y = desc_text_y + desc_text_height + 40

        desc_card_height = (status_y - desc_card_y) + 50

        total_height = desc_card_y + desc_card_height + pad

        return {
            "sprite": {"x": sprite_x, "y": sprite_y},
            "info": {"x": info_x, "y": info_y},
            "types": {"x": info_x, "y": types_y},
            "hw": {"x": info_x, "y": hw_y},

            "stats_card": (pad, stats_card_y, self.width - pad, stats_card_y + stats_card_height),
            "stats_content": {
                "title_y": stats_title_y,
                "rows_y": stats_start_y,
                "row_h": stats_row_h,
                "bar_w": stats_bar_w,
                "x": pad + stats_content_pad
            },

            "desc_card": (pad, desc_card_y, self.width - pad, desc_card_y + desc_card_height),
            "desc_content": {
                "title_y": desc_title_y,
                "text_y": desc_text_y,
                "lines": desc_lines,
                "line_h": 30,
                "x": pad + desc_content_pad
            },

            "status": {"x": pad + desc_content_pad, "y": status_y},
            "total_height": total_height
        }

    def draw(self, pokemon_data: Dict[str, Any]) -> Image.Image:
        layout = self._calculate_layout(pokemon_data)

        # 1. 确定主题色
        types = pokemon_data.get('types', [])
        main_type = types[0] if types else "一般"
        theme_color = TYPE_COLORS.get(main_type, (168, 168, 120))
        bg_top = lighten_color(theme_color, 0.85)
        bg_bot = lighten_color(theme_color, 0.95)

        # 2. 背景
        image = create_vertical_gradient(self.width, layout["total_height"], bg_top, bg_bot)

        # 3. 阴影
        radius = self.cfg["card_radius"]
        self._draw_shadow(image, layout["stats_card"], radius)
        self._draw_shadow(image, layout["desc_card"], radius)

        overlay = Image.new('RGBA', image.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)

        # 4. 卡片背景
        card_bg = self.cfg["colors"]["card_bg"]
        draw_rounded_rectangle(draw, layout["stats_card"], radius, fill=card_bg)
        draw_rounded_rectangle(draw, layout["desc_card"], radius, fill=card_bg)

        # 5. 顶部内容
        # 精灵图阴影
        sx, sy = layout["sprite"]["x"], layout["sprite"]["y"]
        sw, sh = self.cfg["sprite_size"]
        draw.ellipse((sx + 20, sy + sh - 15, sx + sw - 20, sy + sh + 5), fill=(0,0,0, 30))
        # 精灵图
        pokemon_seen = pokemon_data.get("seen", False)
        sprite = self._load_pokemon_sprite(pokemon_data["id"], pokemon_seen)
        overlay.paste(sprite, (sx, sy), sprite)

        # 信息
        ix, iy = layout["info"]["x"], layout["info"]["y"]
        draw.text((ix, iy), f"#{pokemon_data['id']:04d}", fill=theme_color, font=self.fonts["title_id"])
        draw.text((ix, iy + 35), pokemon_data['name_zh'], fill=COLOR_TITLE, font=self.fonts["title_name"])

        # 徽章
        tx, ty = layout["types"]["x"], layout["types"]["y"]
        curr_tx = tx
        for t in types:
            bw = self._draw_type_badge(draw, curr_tx, ty, t)
            curr_tx += bw + 15

        # 身高体重
        hwy = layout["hw"]["y"]
        hx = layout["hw"]["x"]
        def draw_kv(x, k, v, u):
            draw.text((x, hwy), k, fill=COLOR_TEXT_DARK, font=self.fonts["normal"])
            kw = self._measure_text(k, self.fonts["normal"])[0]
            draw.text((x + kw + 5, hwy), str(v), fill=COLOR_TITLE, font=self.fonts["normal_bold"])
            vw = self._measure_text(str(v), self.fonts["normal_bold"])[0]
            draw.text((x + kw + 5 + vw + 2, hwy), u, fill=COLOR_TEXT_DARK, font=self.fonts["normal"])
            return x + kw + vw + 50

        nx = draw_kv(hx, "身高:", pokemon_data.get('height', 0), "m")
        draw_kv(nx, "体重:", pokemon_data.get('weight', 0), "kg")

        # 6. 种族值内容
        sc = layout["stats_content"]
        draw.text((sc["x"], sc["title_y"]), "种族值", fill=COLOR_TITLE, font=self.fonts["section_title"])

        stats_config = [
            ("HP", 'base_hp', (255, 89, 89)),
            ("攻击", 'base_attack', (255, 156, 84)),
            ("防御", 'base_defense', (255, 224, 102)),
            ("特攻", 'base_sp_attack', (109, 190, 255)),
            ("特防", 'base_sp_defense', (151, 222, 133)),
            ("速度", 'base_speed', (247, 148, 211))
        ]
        base_stats = pokemon_data.get('base_stats', {})

        for i, (lbl, key, col) in enumerate(stats_config):
            ry = sc["rows_y"] + i * sc["row_h"]
            draw.text((sc["x"], ry + 8), lbl, fill=self.cfg["colors"]["text_desc"], font=self.fonts["normal"])
            self._draw_stats_bar_fancy(draw, sc["x"] + 50, ry + 2, sc["bar_w"], base_stats.get(key, 0), 255, col)

        # 7. 描述与状态
        dc = layout["desc_content"]
        draw.text((dc["x"], dc["title_y"]), "图鉴描述", fill=COLOR_TITLE, font=self.fonts["section_title"])
        for i, line in enumerate(dc["lines"]):
            draw.text(
                (dc["x"], dc["text_y"] + i * dc["line_h"]),
                line, fill=self.cfg["colors"]["text_desc"], font=self.fonts["desc"]
            )

        stx, sty = layout["status"]["x"], layout["status"]["y"]
        if pokemon_data.get("caught"):
            s_txt, s_col, s_ico = "已捕捉", COLOR_SUCCESS, "✅"
        elif pokemon_data.get("seen"):
            s_txt, s_col, s_ico = "已遇见", COLOR_WARNING, "👁️"
        else:
            s_txt, s_col, s_ico = "未知", COLOR_ERROR, "🔒"
        draw.text((stx, sty), f"{s_ico} {s_txt}", fill=s_col, font=self.fonts["section_title"])

        image.paste(overlay, (0,0), overlay)
        return image

def draw_pokedex_detail(pokemon_data: Dict[str, Any]) -> Image.Image:
    generator = PokedexDetailImageGenerator()
    return generator.draw(pokemon_data)