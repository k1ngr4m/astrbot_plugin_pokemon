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
    "card_h": 125, # Increased height to fit Nature/Ability
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
                # 修正：先替换sp_attack和sp_defense，再替换其他
                stat_name = key.replace('_iv', '')
                if stat_name == 'sp_attack':
                    stat_name = '特攻'
                elif stat_name == 'sp_defense':
                    stat_name = '特防'
                else:
                    stat_name = stat_name.replace('hp', 'H  P').replace('attack', '攻击').replace('defense', '防御').replace('speed', '速度')
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
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 1. Header
        sprite = self._load_pokemon_sprite(p.get('sprite_id', 1), size=(sprite_size, sprite_size))
        overlay.paste(sprite, (pad, sy), sprite)

        ix = pad + sprite_size + 20
        # --- 【优化】文字信息也随之上移 ---
        iy = sy + 10
        
        # Name
        draw.text((ix, iy), p.get('name', ''), fill=COLOR_TITLE, font=self.fonts["title"])
        
        # 独立一行的属性展示
        ty = iy + 45
        tx = ix
        for t in p.get('types', []):
            tw = self._draw_type_badge(draw, tx, ty, t)
            tx += tw + 8

        # 信息描述下移
        info_y = ty + 35
        draw.text((ix, info_y), f"Lv.{p.get('level')}  {p.get('gender')}", fill=COLOR_TEXT_DARK, font=self.fonts["card_title"])

        rows = [
            f"性格: {p.get('nature')}   特性: {p.get('ability')}",
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
            primary_type = p.get('types')[0]
            tint_col = TYPE_COLORS.get(primary_type, (200, 200, 200))
            # Create a very light tint
            tint_h = int(line_y)
            tint_layer = Image.new("RGBA", (self.width, tint_h), (*tint_col, 40)) 
            image.paste(tint_layer, (0, 0), tint_layer)

        
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
