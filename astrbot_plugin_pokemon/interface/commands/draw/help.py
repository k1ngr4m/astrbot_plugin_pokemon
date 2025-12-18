import math
import os
from functools import lru_cache
from typing import List, Tuple, Dict, Any
from PIL import Image, ImageDraw

# 保持原有的导入
from .styles import COLOR_TITLE, COLOR_CMD, COLOR_LINE, COLOR_SHADOW, load_font
from .gradient_utils import create_vertical_gradient

# --- 配置常量 (保持不变) ---
LAYOUT_CONFIG = {
    "width": 800,
    "padding": 30,
    "card_h": 85,
    "card_pad": 15,
    "logo_size": 160,
    "logo_y": 25,
    "shadow_offset": 3,
    "colors": {
        "bg_top": (240, 248, 255),
        "bg_bot": (255, 255, 255),
        "card_bg": (255, 255, 255),
        "card_outline": COLOR_LINE,
        "shadow": (220, 220, 220),
        "text_desc": (100, 100, 100),
        "text_hint": (120, 120, 120),
    }
}

HELP_DATA = [
    ("📝 注册与初始化", [
        ("宝可梦注册", "注册成为宝可梦训练家"),
        ("宝可梦签到", "每日签到获取奖励"),
        ("初始选择 [宝可梦ID]", "选择初始宝可梦"),
        ("查看状态", "查看用户个人资料"),
    ], 3),

    ("🎒 用户资产", [
        ("宝可梦背包", "查看你的背包物品"),
    ], 3),

    ("📊 宝可梦和队伍管理", [
        ("我的宝可梦 [宝可梦ID]", "查看你的宝可梦列表/详情"),
        ("学习招式 [宝可梦ID] [招式ID] <槽位>", "让宝可梦学习新技能"),
        ("查看招式 [招式ID]", "查看招式详情"),
        ("宝可梦进化 [宝可梦ID]", "让宝可梦进化"),
        ("查看进化状态 [宝可梦ID]", "查看宝可梦进化状态"),
        ("图鉴", "查看宝可梦图鉴\n用法: /图鉴 (第一页) /图鉴 P+[页码] /图鉴 M+[宝可梦名/ID]"),
    ], 2),

    ("⛰️ 冒险系统", [
        ("设置队伍 [宝可梦ID1]...", "设置你的宝可梦队伍"),
        ("查看队伍", "查看当前队伍配置"),
        ("宝可梦恢复", "恢复队伍中宝可梦的所有状态"),
        ("查看区域", "查看可冒险区域/区域详情"),
        ("冒险 [区域ID]", "开始冒险寻找宝可梦"),
        ("战斗", "与野生宝可梦战斗"),
        ("捕捉 <物品ID>", "尝试用[物品ID]捕捉野生宝可梦"),
        ("逃跑", "从战斗中逃跑"),
        ("查看战斗 [战斗ID]", "查看战斗历史记录详情"),
    ], 2),

    ("🏪 商店系统", [
        ("宝可梦商店 [商店ID]", "查看商店商品/商品详情"),
        ("宝可梦商店购买 [商店ID] [商品ID] [数量]", "购买商品"),
    ], 2),
]


# --- 辅助函数 ---

@lru_cache(maxsize=1)
def get_processed_logo(size: int, bg_color: Tuple[int, int, int]) -> Image.Image:
    """加载并处理Logo（逻辑保持不变，已是最佳实践）"""
    path = os.path.join(os.path.dirname(__file__), "resource", "astrbot_logo.jpg")
    try:
        img = Image.open(path).convert("RGBA")
    except FileNotFoundError:
        return _create_placeholder_logo(size, bg_color)

    img.thumbnail((size, size), Image.Resampling.LANCZOS)

    # 向量化去背
    grayscale = img.convert("L")
    threshold = 240
    mask = grayscale.point(lambda p: 255 if p < threshold else 0)
    r, g, b, _ = img.split()
    img = Image.merge("RGBA", (r, g, b, mask))

    round_mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(round_mask).rounded_rectangle([0, 0, *img.size], radius=20, fill=255)

    final_img = Image.new("RGBA", img.size, (*bg_color, 0))
    final_img.paste(img, (0, 0), mask=img)
    final_img.putalpha(round_mask)

    return final_img


def _create_placeholder_logo(size, bg_color):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size, size], radius=20, fill=bg_color, outline=(180, 180, 180), width=2)
    return img


class HelpImageGenerator:
    def __init__(self):
        self.cfg = LAYOUT_CONFIG
        self.width = self.cfg["width"]
        self.fonts = self._load_fonts()

    def _load_fonts(self):
        return {
            "title": load_font(32),
            "subtitle": load_font(28),
            "section": load_font(24),
            "cmd": load_font(18),
            "desc": load_font(16),
        }

    @lru_cache(maxsize=4)
    def _get_card_bg(self, width: int, height: int) -> Image.Image:
        """
        【优化点1】预渲染卡片背景。
        生成一张包含阴影和边框的透明背景图。
        """
        # 画布需要稍微大一点以容纳阴影
        offset = self.cfg["shadow_offset"]
        img_w = width + offset
        img_h = height + offset

        # 使用 RGBA 模式以便透明叠加
        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 1. 绘制阴影
        draw.rounded_rectangle(
            [offset, offset, width + offset, height + offset],
            radius=12, fill=self.cfg["colors"]["shadow"]
        )

        # 2. 绘制卡片本体
        draw.rounded_rectangle(
            [0, 0, width, height],
            radius=12, fill=self.cfg["colors"]["card_bg"],
            outline=self.cfg["colors"]["card_outline"], width=1
        )
        return img

    def _measure_text(self, text, font):
        left, top, right, bottom = font.getbbox(text)
        return right - left, bottom - top

    def calculate_layout(self) -> Tuple[int, List[Dict[str, Any]]]:
        """
        【优化点2】一次性计算高度和所有元素的布局坐标。
        返回: (total_height, render_list)
        """
        render_list = []
        curr_y = self.cfg["logo_y"] + self.cfg["logo_size"] + 30

        # 模拟计算每个section的高度
        _, h_title = self._measure_text("测试", self.fonts["section"])

        for section_title, cmds, cols in HELP_DATA:
            # 记录章节标题位置
            render_list.append({
                "type": "section_title",
                "text": section_title,
                "y": curr_y,
                "h_title": h_title
            })

            # 卡片区域计算
            start_y = curr_y + h_title // 2 + 25
            card_area_w = self.width - 60
            card_w = card_area_w // cols
            real_card_w = card_w - 10

            # 计算每张卡片的坐标
            for idx, (cmd, desc) in enumerate(cmds):
                col = idx % cols
                row = idx // cols
                x = 30 + col * card_w
                y = start_y + row * (self.cfg["card_h"] + self.cfg["card_pad"])

                render_list.append({
                    "type": "card",
                    "cmd": cmd,
                    "desc": desc,
                    "x": x,
                    "y": y,
                    "w": real_card_w
                })

            # 更新下一章的起始 Y 坐标
            rows = math.ceil(len(cmds) / cols)
            curr_y = start_y + rows * (self.cfg["card_h"] + self.cfg["card_pad"]) + 35

        total_height = curr_y + 50  # Footer padding
        return total_height, render_list

    def draw(self) -> Image.Image:
        # 1. 获取布局信息 (Single Pass)
        total_height, render_items = self.calculate_layout()

        # 2. 创建背景
        image = create_vertical_gradient(
            self.width, total_height,
            self.cfg["colors"]["bg_top"], self.cfg["colors"]["bg_bot"]
        )
        draw = ImageDraw.Draw(image)

        # 3. 绘制 Logo (不变)
        logo = get_processed_logo(self.cfg["logo_size"], self.cfg["colors"]["bg_top"])
        image.paste(logo, (30, self.cfg["logo_y"]), logo)

        # 4. 绘制主标题
        title_y = self.cfg["logo_y"] + self.cfg["logo_size"] // 2
        draw.text((self.width // 2, title_y), "宝可梦游戏帮助", fill=COLOR_TITLE, font=self.fonts["title"], anchor="mm")

        # 5. 遍历渲染列表
        for item in render_items:
            if item["type"] == "section_title":
                # 绘制标题
                draw.text((50, item["y"]), item["text"], fill=COLOR_TITLE, font=self.fonts["section"], anchor="lm")
                # 绘制下划线
                w_title = self._measure_text(item["text"], self.fonts["section"])[0]
                line_y = item["y"] + item["h_title"] // 2 + 8
                draw.line([(50, line_y), (50 + w_title, line_y)], fill=COLOR_TITLE, width=3)

            elif item["type"] == "card":
                x, y, w = item["x"], item["y"], item["w"]

                # A. 粘贴预渲染的卡片背景 (速度快)
                bg_img = self._get_card_bg(w, self.cfg["card_h"])
                image.paste(bg_img, (x, y), mask=bg_img)

                # B. 绘制文字
                cx = x + w // 2
                draw.text((cx, y + 18), item["cmd"], fill=COLOR_CMD, font=self.fonts["cmd"], anchor="mt")

                desc_lines = item["desc"].split('\n')
                for i, line in enumerate(desc_lines):
                    draw.text(
                        (cx, y + 45 + i * 18), line,
                        fill=self.cfg["colors"]["text_desc"], font=self.fonts["desc"], anchor="mt"
                    )

        # 6. 底部提示
        draw.text((self.width // 2, total_height - 40), "💡 提示：命令中的 [ID] 表示必填参数，<> 表示可选参数",
                  fill=self.cfg["colors"]["text_hint"], font=self.fonts["desc"], anchor="mm")

        return image


# --- 对外接口 ---
def draw_help_image():
    generator = HelpImageGenerator()
    return generator.draw()