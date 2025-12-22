
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

def test_battle_drawer():
    print("--- Testing Battle Drawer ---")
    
    # Mock Log Data
    log_data = {
        'id': 12345,
        'created_at': '2023-01-01 12:00:00',
        'target_name': 'Gym Leader Brock',
        'result': 'success',
        'log_data': [
            {
                'pokemon_name': 'Pikachu',
                'level': 25,
                'species_id': 25,
                'result': 'win',
                'win_rate': 85.5,
                'trainer_pokemon_name': 'Geodude',
                'trainer_pokemon_level': 20,
                'details': ['Thunderbolt hit!', 'It was super effective!']
            },
            {
                'pokemon_name': 'Charmander',
                'level': 24,
                'species_id': 4,
                'result': 'loss',
                'win_rate': 10.2,
                'trainer_pokemon_name': 'Onix',
                'trainer_pokemon_level': 22,
                'details': ['Rock Throw hit!', 'It was super effective!']
            }
        ]
    }
    
    try:
        img = draw_battle_log(log_data)
        print(f"PASS: Image generated successfully. Size: {img.size}")
        # Optionally save it to inspect manually
        # img.save("test_battle_log.png") 
    except Exception as e:
        print(f"FAIL: Image generation failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_battle_drawer()
