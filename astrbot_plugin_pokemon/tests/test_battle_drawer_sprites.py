
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

def test_battle_drawer_sprites():
    print("--- Testing Battle Drawer with User & Opponent Sprites ---")
    
    # Mock Log Data with IDs
    log_data = {
        'id': 777,
        'created_at': '2023-01-01',
        'target_name': 'Gym Leader Brock',
        'result': 'success',
        'log_data': [
            {
                'pokemon_name': 'Pikachu',
                'level': 25,
                'user_species_id': 25, # Pikachu ID
                'result': 'win',
                'win_rate': 85.5,
                
                'trainer_pokemon_name': 'Onix',
                'trainer_pokemon_level': 20,
                'target_species_id': 95, # Onix ID
                
                'details': ['Pikachu used Iron Tail!']
            }
        ]
    }
    
    try:
        img = draw_battle_log(log_data)
        print(f"PASS: Image generated successfully. Size: {img.size}")
        # Optionally save to verify visually
        # img.save("test_sprites.png")
    except Exception as e:
        print(f"FAIL: Image generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_battle_drawer_sprites()
