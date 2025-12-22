
import math
import os
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
            # 优先使用新字段，兼容旧字段
            user_species_id = sk.get('user_species_id') or sk.get('species_name')
            user_types = sk.get('user_types', [])
            
            # Determine Header Color based on primary type
            u_color = COLOR_TEXT_DARK
            if user_types and len(user_types) > 0:
                u_color = self._get_type_color(user_types[0])
            
            lx = pad + 20
            ly = card_y + 20
            
            # 绘制我方精灵
            if user_species_id and isinstance(user_species_id, int):
                sprite = self._load_pokemon_sprite(user_species_id)
                overlay.paste(sprite, (lx, ly), sprite)
                lx += 110 # Shift text right
            
            draw.text((lx, ly + 20), f"{u_name}", fill=u_color, font=self.fonts["card_title"])
            draw.text((lx, ly + 50), f"Lv.{u_lv}", fill=self.cfg["colors"]["text_sub"], font=self.fonts["normal"])
            
            # VS in Middle
            mx = self.width // 2
            my = card_y + layout["base_h"] // 2
            draw.text((mx, my), "VS", fill=(200, 200, 200), font=self.fonts["title"], anchor="mm")
            
            op_name = sk.get('trainer_pokemon_name') or log_data.get('target_name')
            op_lv = sk.get('trainer_pokemon_level') or sk.get('target_level') or log_data.get('target_level')
            target_species_id = sk.get('target_species_id')
            target_types = sk.get('target_types', [])

            # Determine Opponent Header Color
            op_color = COLOR_TEXT_DARK
            if target_types and len(target_types) > 0:
                op_color = self._get_type_color(target_types[0])

            rx = self.width - pad - 20
            ry = card_y + 20
            
            # 绘制对方精灵 (从右向左布局)
            if target_species_id and isinstance(target_species_id, int):
                sprite = self._load_pokemon_sprite(target_species_id)
                # 翻转对方精灵图以面向左 (可选，根据需求)
                # sprite = sprite.transpose(Image.FLIP_LEFT_RIGHT) 
                overlay.paste(sprite, (rx - 100, ry), sprite) # 100 is sprite width
                rx -= 110 # Shift text left
            
            draw.text((rx, ry + 20), f"{op_name}", fill=op_color, font=self.fonts["card_title"], anchor="rs")
            if op_lv:
                 draw.text((rx, ry + 50), f"Lv.{op_lv}", fill=self.cfg["colors"]["text_sub"], font=self.fonts["normal"], anchor="rs")

            # Result Badge
            res_text = "胜利" if sk.get('result') == 'win' else "失败"
            res_col = COLOR_SUCCESS if sk.get('result') == 'win' else COLOR_ERROR
            
            wr = sk.get('win_rate', 0)
            draw.text((mx, my + 30), f"胜率预测: {wr}%", fill=self.cfg["colors"]["text_sub"], font=self.fonts["small"], anchor="mm")
            
            bx = mx
            by = my - 30
            draw.text((bx, by), res_text, fill=res_col, font=self.fonts["result_win"], anchor="mm")
            
            # --- 详细过程区域 (Bottom Details) ---
            if layout["details"]:
                details_y_start = card_y + layout["base_h"]
                # 分割线
                line_y = details_y_start - 10
                draw.line((pad + 20, line_y, self.width - pad - 20, line_y), fill=(230, 230, 230), width=1)
                
                curr_dy = details_y_start
                for line in layout["details"]:
                    # 使用富文本绘制 helper
                    self._draw_rich_text_line(draw, pad + 30, curr_dy, line, self.fonts["small"])
                    curr_dy += detail_line_height

        image.paste(overlay, (0,0), overlay)
        return image

    def _get_type_color(self, type_input: str) -> Tuple[int, int, int]:
        """获取属性对应的颜色"""
        # 1. 直接尝试作为中文Key查找
        if type_input in TYPE_COLORS:
            return TYPE_COLORS[type_input]

        # 2. 尝试英文转中文映射
        TYPE_EN_TO_ZH = {
            "normal": "一般", "fire": "火", "water": "水", "grass": "草",
            "electric": "电", "ice": "冰", "fighting": "格斗", "poison": "毒",
            "ground": "地面", "flying": "飞行", "psychic": "超能力", "bug": "虫",
            "rock": "岩石", "ghost": "幽灵", "dragon": "龙", "steel": "钢",
            "fairy": "妖精"
        }
        
        type_zh = TYPE_EN_TO_ZH.get(type_input.lower(), "未知")
        return TYPE_COLORS.get(type_zh, COLOR_TEXT_DARK)

    def _draw_rich_text_line(self, draw: ImageDraw.Draw, x: int, y: int, 
                            content: Any, font: ImageFont.FreeTypeFont):
        """绘制单行文本（支持普通字符串或富文本片段列表）"""
        if isinstance(content, str):
            draw.text((x, y), f"• {content}", fill=self.cfg["colors"]["text_main"], font=font)
        elif isinstance(content, list):
            # Rich text segments: [{'text': '...', 'color': '...'}, ...]
            current_x = x
            
            # 绘制列表项符号
            bullet = "• "
            draw.text((current_x, y), bullet, fill=self.cfg["colors"]["text_main"], font=font)
            current_x += font.getlength(bullet)
            
            for segment in content:
                text = segment.get('text', '')
                color_key = segment.get('color', 'default')
                
                # 解析颜色
                if color_key == 'default':
                    fill_color = self.cfg["colors"]["text_main"]
                elif color_key.startswith('type_'):
                    type_en = color_key.replace('type_', '')
                    fill_color = self._get_type_color(type_en)
                elif color_key == 'red' or color_key == 'hp':
                    fill_color = COLOR_ERROR
                elif color_key == 'green':
                    fill_color = COLOR_SUCCESS
                elif color_key == 'blue':
                    fill_color = (66, 133, 244) # Google Blueish
                else:
                    fill_color = self.cfg["colors"]["text_main"]
                
                draw.text((current_x, y), text, fill=fill_color, font=font)
                current_x += font.getlength(text)

def draw_battle_log(log_data: Dict[str, Any]) -> Image.Image:
    drawer = BattleDrawer()
    return drawer.draw(log_data)
