import os
import math
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter

from astrbot.api import logger
from .styles import (
    COLOR_TITLE, COLOR_TEXT_DARK, COLOR_TEXT_GRAY, COLOR_CARD_BG,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, TYPE_COLORS,
    load_font, draw_rounded_rectangle, lighten_color
)
from .gradient_utils import create_vertical_gradient

# --- 配置 ---
ITEM_LIST_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_h": 80,
    "cols": 2,
    "col_gap": 20,
    "row_gap": 15,
    "bg_colors": ((240, 248, 255), (255, 255, 255))
}

class ItemDrawer:
    def __init__(self, cfg):
        self.cfg = cfg
        self.width = cfg["width"]
        self.fonts = {
            "title": load_font(32),
            "subtitle": load_font(20),
            "card_title": load_font(18),
            "normal": load_font(16),
            "small": load_font(14),
            "small_bold": load_font(15),
        }
        self.sprite_cache = {}

    def _load_item_sprite(self, item_name_en: str, size=(60, 60)) -> Image.Image:
        """加载物品图标，使用类似宝可梦精灵图的方式处理"""
        base_path = os.path.dirname(__file__)
        # 尝试加载物品图标 (从正确路径 assets/items)
        sprite_path = os.path.abspath(os.path.join(
            base_path, "..", "..", "..", "..", "assets", "items", f"{item_name_en}.png"
        ))
        cache_key = f"{item_name_en}_{size}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        try:
            sprite = Image.open(sprite_path).convert("RGBA")
            sprite = sprite.resize(size, Image.Resampling.LANCZOS)
            self.sprite_cache[cache_key] = sprite
            return sprite
        except FileNotFoundError:
            # 如果找不到物品图标，创建一个简单的占位符
            placeholder = Image.new("RGBA", size, (200, 200, 200, 255))
            draw = ImageDraw.Draw(placeholder)
            text = "?"
            font = load_font(30)
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = (size[0] - text_width) // 2
            text_y = (size[1] - text_height) // 2
            draw.text((text_x, text_y), text, fill="black", font=font)

            self.sprite_cache[cache_key] = placeholder
            return placeholder

    def _draw_item_category_badge(self, draw, x, y, category_name):
        font = self.fonts["small"]
        bg_col = (100, 150, 200)  # 蓝色背景
        text_w = font.getlength(category_name)
        w, h = int(text_w + 12), 20
        draw_rounded_rectangle(draw, (x, y, x + w, y + h), corner_radius=8, fill=bg_col)
        draw.text((x + w/2, y + h/2), category_name, fill=(255, 255, 255), font=font, anchor="mm")
        return w

class UserItemDrawer(ItemDrawer):
    def __init__(self):
        super().__init__(ITEM_LIST_CONFIG)

    def draw(self, data: Dict[str, Any]) -> Image.Image:
        """绘制用户物品列表画面"""
        # 直接使用已分页的物品列表
        item_list = data.get("items", [])
        # logger.info(f"[DEBUG] item_list: {item_list}")
        # 计算高度
        rows = math.ceil(len(item_list) / self.cfg["cols"])
        content_h = rows * (self.cfg["card_h"] + self.cfg["row_gap"])
        header_h = 100
        footer_h = 60
        total_h = header_h + content_h + footer_h + self.cfg["padding"] * 2

        # 背景
        image = create_vertical_gradient(self.width, total_h, *self.cfg["bg_colors"])
        overlay = Image.new("RGBA", image.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)

        # 标题
        cx = self.width // 2
        draw.text((cx, 50), "我的物品", fill=COLOR_TITLE, font=self.fonts["title"], anchor="mm")
        draw.text((cx, 85),
                  f"第 {data.get('page', 1)} / {data.get('total_pages', 1)} 页 (共 {data.get('total_count', 0)} 件物品)",
                  fill=COLOR_TEXT_GRAY, font=self.fonts["subtitle"], anchor="mm")

        # 网格布局
        pad = self.cfg["padding"]
        col_w = (self.width - pad * 2 - self.cfg["col_gap"]) // 2
        start_y = header_h + pad + 10  # 轻微视觉调整

        for i, item in enumerate(item_list):
            row = i // 2
            col = i % 2
            x = pad + col * (col_w + self.cfg["col_gap"])
            y = start_y + row * (self.cfg["card_h"] + self.cfg["row_gap"])

            self._draw_item_card(draw, overlay, x, y, col_w, self.cfg["card_h"], item)

        # 底部说明
        fy = total_h - 40
        draw.text((cx, fy), "使用 /我的物品 P<页码> 翻页",
                  fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="mm")

        image.paste(overlay, (0,0), overlay)
        return image

    def _draw_item_card(self, draw, overlay, x, y, w, h, item):
        """绘制单个物品卡"""
        # 阴影与背景
        draw_rounded_rectangle(draw, (x, y, x+w, y+h), corner_radius=12, fill=COLOR_CARD_BG)

        # 物品图标 - 使用英文名称
        item_name_en = item.get('name_en', '').lower().replace(' ', '-').replace("'", '').replace('(', '').replace(')', '')
        # logger.info(f"[DEBUG] item_name_en: {item_name_en}")
        # 如果没有name_en，使用name_zh的处理版本作为备选
        if not item_name_en:
            item_name_en = item.get('name', 'unknown-item').lower().replace(' ', '-').replace("'", '').replace('(', '').replace(')', '')
        sprite = self._load_item_sprite(item_name_en, size=(60, 60))
        overlay.paste(sprite, (x + 10, y + 10), sprite)

        # 信息起始坐标
        ix = x + 85
        iy = y + 12

        # 1. 物品名称
        name = item.get('name', '未知物品')
        draw.text((ix, iy), name, fill=COLOR_TEXT_DARK, font=self.fonts["card_title"])

        # 2. 物品类别徽章 (下移)
        # 优先显示pocket_name（背包名称），如果不存在则显示category_name
        pocket_name = item.get('pocket_name', '')
        category_name = item.get('category_name', f'类别{item.get("category_id", 0)}')

        # 显示pocket_name（背包名称）作为主要分类
        display_name = pocket_name if pocket_name else category_name
        ty = iy + 25
        self._draw_item_category_badge(draw, ix, ty, display_name)

        # 3. 数量 (右下角)
        quantity = item.get('quantity', 0)
        qty_text = f"数量: {quantity}"
        qty_bbox = draw.textbbox((0, 0), qty_text, font=self.fonts["normal"])
        qty_width = qty_bbox[2] - qty_bbox[0]
        draw.text((x + w - 10 - qty_width, y + h - 25), qty_text,
                  fill=COLOR_TEXT_DARK, font=self.fonts["normal"], anchor="ra")
        # 4. 物品ID (左下角)
        id_text = f"#{item.get('item_id', 0)}"
        draw.text((ix, y + h - 25), id_text, fill=COLOR_TEXT_GRAY, font=self.fonts["small"])


def draw_user_items(data: Dict) -> Image.Image:
    """绘制用户物品列表"""
    return UserItemDrawer().draw(data)