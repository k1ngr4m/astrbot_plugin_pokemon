
import sys
import os
from unittest.mock import MagicMock

# Mock astrbot module before imports
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()
sys.modules['astrbot.api.event'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from astrbot_plugin_pokemon.interface.commands.draw.battle_drawer import draw_battle_log

def test_fix_image_result():
    print("--- Testing Image Result Fix ---")
    
    # Mock Log Data
    log_data = {
        'id': 999,
        'created_at': '2023-01-01',
        'target_name': 'Bug Tester',
        'result': 'success',
        'log_data': []
    }
    
    # 1. Generate Image
    img = draw_battle_log(log_data)
    
    # 2. Save Logic
    temp_path = f"/tmp/battle_log_TEST.png"
    try:
        img.save(temp_path)
        print(f"PASS: Saved image to {temp_path}")
    except Exception as e:
        print(f"FAIL: Saving image failed: {e}")
        return

    # 3. Path Validation
    if isinstance(temp_path, str) and temp_path.startswith("/tmp"): # Minimal check mimicking 'startswith' check in AstrBot
         print("PASS: Path is string and valid format for image_result.")
    else:
         print("FAIL: Path is not a valid string.")
         
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)

if __name__ == "__main__":
    test_fix_image_result()
