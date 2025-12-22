import sys
import os
from unittest.mock import MagicMock
from PIL import Image

# Mock astrbot
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from astrbot_plugin_pokemon.interface.commands.draw.user_pokemon_drawer import draw_user_pokemon_list, draw_user_pokemon_detail

ARTIFACT_DIR = "/Users/linyiming/.gemini/antigravity/brain/ee6a0e70-0ea9-403a-b31b-aa54016bef5a"

def verify_ui():
    print("--- Verifying UI Layouts ---")
    
    # 1. Test List View
    list_data = {
        'page': 1,
        'total_pages': 5,
        'total_count': 50,
        'list': [
            {
                'id': 1, 'sprite_id': 1, 'name': '妙蛙种子', 'gender': '♂', 'level': 5,
                'current_hp': 20, 'max_hp': 45, 'nature': '固执', 'ability': '茂盛',
                'types': ['草', '毒']
            },
            {
                'id': 4, 'sprite_id': 4, 'name': '小火龙', 'gender': '♀', 'level': 10,
                'current_hp': 5, 'max_hp': 39, 'nature': '内敛', 'ability': '猛火',
                'types': ['火']
            },
            {
                'id': 150, 'sprite_id': 150, 'name': '超梦', 'gender': '无', 'level': 70,
                'current_hp': 200, 'max_hp': 250, 'nature': '胆小', 'ability': '压迫感',
                'types': ['超能力']
            },
            {
                'id': 25, 'sprite_id': 25, 'name': '皮卡丘', 'gender': '♂', 'level': 50,
                'current_hp': 0, 'max_hp': 120, 'nature': '爽朗', 'ability': '静电',
                'types': ['电']
            }
        ]
    }
    
    try:
        img_list = draw_user_pokemon_list(list_data)
        list_path = os.path.join(ARTIFACT_DIR, "verify_list.png")
        img_list.save(list_path)
        print(f"PASS: List View generated. Saved to {list_path}")
    except Exception as e:
        print(f"FAIL: List View generation failed: {e}")
        import traceback
        traceback.print_exc()

    # 2. Test Detail View
    detail_data = {
        'id': 6, 'sprite_id': 6, 'name': '喷火龙', 'gender': '♂', 'level': 100,
        'types': ['火', '飞行'],
        'nature': '固执', 'ability': '猛火', 'caught_time': '2023-10-01 12:00',
        'exp': 1059860,
        'stats_detail': [
            {'label': 'HP', 'val': 297, 'iv': 31, 'ev': 0},
            {'label': '攻击', 'val': 282, 'iv': 31, 'ev': 252},
            {'label': '防御', 'val': 192, 'iv': 20, 'ev': 0},
            {'label': '特攻', 'val': 228, 'iv': 15, 'ev': 0},
            {'label': '特防', 'val': 206, 'iv': 31, 'ev': 4},
            {'label': '速度', 'val': 299, 'iv': 31, 'ev': 252},
        ],
        'moves': [
            {'name': '喷射火焰', 'type': '火', 'pp': 10, 'max_pp': 15},
            {'name': '空气斩', 'type': '飞行', 'pp': 5, 'max_pp': 15},
            {'name': '龙之波动', 'type': '龙', 'pp': 10, 'max_pp': 10},
            {'name': '日光束', 'type': '草', 'pp': 0, 'max_pp': 10}
        ]
    }
    
    try:
        img_detail = draw_user_pokemon_detail(detail_data)
        detail_path = os.path.join(ARTIFACT_DIR, "verify_detail.png")
        img_detail.save(detail_path)
        print(f"PASS: Detail View generated. Saved to {detail_path}")
    except Exception as e:
        print(f"FAIL: Detail View generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_ui()
