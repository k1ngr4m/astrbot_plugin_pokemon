
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

def test_rich_battle_log():
    print("--- Testing Rich Text Battle Log (Colors) ---")
    
    # Mock Log Data with Types and Rich Text Details
    log_data = {
        'id': 999,
        'created_at': '2023-01-01',
        'target_name': 'Gym Leader Misty',
        'result': 'success',
        'log_data': [
            {
                'pokemon_name': 'Pikachu',
                'level': 50,
                'user_species_id': 25,
                'user_types': ['电'], # Should color name Yellow (Chinese Key Test)
                
                'trainer_pokemon_name': 'Starmie',
                'trainer_pokemon_level': 52,
                'target_species_id': 121,
                'target_types': ['水', '超能力'], # Should color name Blue (Water)
                
                'result': 'win',
                'win_rate': 60.0,
                
                'details': [
                    # Rich Text Line 1: Move Usage
                    [
                        {'text': 'Pikachu', 'color': 'type_electric'},
                        {'text': ' used ', 'color': 'default'},
                        {'text': 'Thunderbolt', 'color': 'type_electric'},
                        {'text': '!', 'color': 'default'}
                    ],
                    # Rich Text Line 2: Effectiveness (Red)
                    [
                        {'text': "It's super effective!", 'color': 'red'}
                    ],
                    # Rich Text Line 3: Damage (Crit/Super - Red)
                    [
                        {'text': "Dealt ", 'color': 'default'},
                        {'text': "120", 'color': 'red'},
                        {'text': " damage.", 'color': 'default'}
                    ],
                    # Rich Text Line 4: Ineffective (Blue)
                    [
                        {'text': "It's not very effective...", 'color': 'blue'}
                    ],
                    # Legacy String Line (backward compatibility)
                    "Starmie fainted!"
                ]
            }
        ]
    }
    
    try:
        img = draw_battle_log(log_data)
        print(f"PASS: Image generated successfully. Size: {img.size}")
        # img.save("test_rich_log.png")
    except Exception as e:
        print(f"FAIL: Image generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rich_battle_log()
