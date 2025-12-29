import os
import math
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter

from .styles import (
    COLOR_TITLE, COLOR_TEXT_DARK, COLOR_TEXT_GRAY, COLOR_CARD_BG,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, TYPE_COLORS,
    load_font, draw_rounded_rectangle, lighten_color
)
from .gradient_utils import create_vertical_gradient


# 优化 IV 文本映射
STAT_MAP = {
    'hp': 'H  P', 'attack': '攻击', 'defense': '防御',
    'sp_attack': '特攻', 'sp_defense': '特防', 'speed': '速度'
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
            "icon": load_font(24),  # 统一加入图标字体
        }
        # 建议：将 cache 提升为类变量或全局单例，避免每个实例重复加载
        self.sprite_cache = {}

    def _get_sprite_path(self, pokemon_id: int) -> str:
        """统一路径管理"""
        # 获取当前文件所在目录 (draw 目录)
        draw_dir = os.path.dirname(__file__)
        # 从 draw 目录向上跳四级到达插件根目录
        # draw_dir: .../astrbot_plugin_pokemon/astrbot_plugin_pokemon/interface/commands/draw
        # 需要跳到插件根目录: .../astrbot_plugin_pokemon/
        plugin_root = os.path.abspath(os.path.join(draw_dir, "..", "..", "..", ".."))
        return os.path.abspath(os.path.join(
            plugin_root, "assets", "sprites", "front", f"{pokemon_id}.png"
        ))

    def _load_pokemon_sprite(self, pokemon_id: int, size=(80, 80), gray=False) -> Image.Image:
        cache_key = f"{pokemon_id}_{size}_{gray}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        try:
            sprite_path = self._get_sprite_path(pokemon_id)
            sprite = Image.open(sprite_path).convert("RGBA")
            if gray:
                # 快速转灰度（用于未见过的图鉴）
                alpha = sprite.getchannel('A')
                sprite = sprite.convert('L').convert('RGBA')
                sprite.putalpha(alpha)

            sprite = sprite.resize(size, Image.Resampling.LANCZOS)
            self.sprite_cache[cache_key] = sprite
            return sprite
        except FileNotFoundError:
            return Image.new("RGBA", size, (0, 0, 0, 0))

    def _draw_type_badge(self, draw, x, y, type_text):
        """通用属性标签绘制"""
        font = self.fonts["small"]
        bg_col = TYPE_COLORS.get(type_text, (150, 150, 150))
        text_w = font.getlength(type_text)
        w, h = int(text_w + 16), 22
        draw_rounded_rectangle(draw, (x, y, x + w, y + h), corner_radius=10, fill=bg_col)
        draw.text((x + w/2, y + h/2), type_text, fill=(255, 255, 255), font=font, anchor="mm")
        return w

    def _draw_item_card(self, draw, overlay, x, y, w, h, p):
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
        if 'N' in gender or ' bisexual ' in gender: g_col = COLOR_TEXT_GRAY

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

        # 4. HP 血条 (iy + 78)
        cur, max_hp = p.get('current_hp', 0), p.get('max_hp', 0)
        ratio = max(0, min(1, cur / max_hp)) if max_hp > 0 else 0
        bar_w, bar_h = 140, 6
        bar_x, bar_y = ix, iy + 78

        draw_rounded_rectangle(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), 3, fill=(230, 230, 230))
        bar_col = COLOR_SUCCESS if ratio > 0.5 else (COLOR_WARNING if ratio > 0.2 else COLOR_ERROR)
        if ratio > 0:
            draw_rounded_rectangle(draw, (bar_x, bar_y, bar_x + int(bar_w * ratio), bar_y + bar_h), 3, fill=bar_col)

        # 5. 等级与数值 (相应调整位置)
        level_y_offset = bar_y + 12
        draw.text((ix, level_y_offset), f"Lv.{p.get('level', 1)}", fill=COLOR_TEXT_GRAY, font=self.fonts["small"])
        draw.text((ix + 60, level_y_offset), f"HP {cur}/{max_hp}", fill=COLOR_TEXT_DARK, font=self.fonts["small"])

        # 获取收藏状态
        is_favorite = p.get('is_favorite', 0)

        # ID Badge (Top Right)
        id_txt = f"#{p.get('id', 0)}"
        iw = self.fonts["small"].getlength(id_txt) + 10
        # 如果有星星，则ID的位置需要调整
        id_x_start = x+w-iw-10  # 为星星留出空间
        # id_x_start = x+w-iw-10 if not is_favorite else x+w-iw-25  # 为星星留出空间
        draw_rounded_rectangle(draw, (id_x_start, y+10, x+w-10, y+30), corner_radius=5, fill=(240, 240, 240))
        draw.text((id_x_start + iw/2, y+20), id_txt, fill=COLOR_TEXT_GRAY, font=self.fonts["small"], anchor="mm")

        # 收藏标识 (Top Right, left of ID)
        if is_favorite:
            # 绘制五角星，放在ID标签的左边
            import math
            star_size = 8
            # 星星绘制在ID标签的左边
            center_x, center_y = id_x_start - 10, y+20  # 在ID框的左边留10像素间距
            # 画五角星
            points = []
            for i in range(5):
                # 外圈点
                angle = math.radians(72 * i - 90)  # -90度开始，使顶部朝上
                points.append((center_x + star_size * math.cos(angle),
                              center_y + star_size * math.sin(angle)))
                # 内圈点
                angle = math.radians(72 * i + 36 - 90)  # 中间角度
                points.append((center_x + star_size * 0.4 * math.cos(angle),
                              center_y + star_size * 0.4 * math.sin(angle)))
            # 绘制星形
            draw.polygon(points, fill=(255, 215, 0))  # 金色/黄色

        # 6. IV标记 (新增：在ID标签下方添加IV标识)
        ivs = p.get('ivs', {})
        if ivs and hasattr(ivs, '__dict__'):
            # 将ivs对象转换为字典
            iv_values = {k: v for k, v in ivs.__dict__.items() if k.endswith('_iv')}
        elif isinstance(ivs, dict):
            iv_values = {k: v for k, v in ivs.items() if k.endswith('_iv')}
        else:
            iv_values = {}

        # 检查是否有完美的IV (0或31) 并生成标记
        perfect_ivs = []
        for key, value in iv_values.items():
            if value == 31 or value == 0:
                # 使用STAT_MAP字典来简化IV文本映射
                stat_name = STAT_MAP.get(key.replace('_iv', ''), '未知')
                if value == 31:
                    perfect_ivs.append(f"{stat_name}\t31")
                else:  # value == 0
                    perfect_ivs.append(f"{stat_name}\t0")

        if perfect_ivs:
            # 在ID标签下方显示IV标记，每个IV单独一行，位置往左调整
            start_y = y + 35  # 在ID标签下方开始
            # 使用更小的字体和不同颜色显示IV标记
            for i, iv_text in enumerate(perfect_ivs):
                iv_y = start_y + i * 18  # 每个IV标记垂直间距18像素
                # 根据IV值选择颜色：31用绿色，0用红色
                iv_color = COLOR_SUCCESS if '31' in iv_text else COLOR_ERROR
                # 往左调整位置，避免超出边距
                draw.text((x+w-iw-30, iv_y), iv_text, fill=iv_color, font=self.fonts["small"])
