
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

def test_wild_battle_viz():
    print("--- Testing Wild Battle Visualization (Level + Sprite) ---")
    
    # Mock Wild Battle Log
    log_data = {
        'id': 888,
        'created_at': '2023-01-01',
        'target_name': 'Wild Pidgey',
        'result': 'success',
        'log_data': [
            {
                'pokemon_name': 'Charmander',
                'level': 10,
                'user_species_id': 4, 
                'result': 'win',
                'win_rate': 95.0,
                
                # Wild Pokemon Specifics
                'target_species_id': 16, # Pidgey
                'target_level': 8,      # Level 8
                
                'details': ['Charmander used Scratch!']
            }
        ]
    }
    
    try:
        img = draw_battle_log(log_data)
        print(f"PASS: Image generated successfully. Size: {img.size}")
        # img.save("test_wild.png")
    except Exception as e:
        print(f"FAIL: Image generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_wild_battle_viz()
