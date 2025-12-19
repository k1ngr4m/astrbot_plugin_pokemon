
import sys
import os
from unittest.mock import MagicMock

# Mock astrbot module before imports
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()

# Mock random 
import random
random.uniform = MagicMock(return_value=1.0)
random.random = MagicMock(return_value=0.5)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from astrbot_plugin_pokemon.core.services.battle.battle_engine import BattleState, BattleLogic, ListBattleLogger
from astrbot_plugin_pokemon.core.models.adventure_models import BattleContext, BattleMoveInfo
from astrbot_plugin_pokemon.core.models.pokemon_models import PokemonStats

def create_mock_pokemon(name="TestPoke", ability_id=0, hp=100):
    poke = MagicMock()
    poke.name = name
    poke.ability_id = ability_id
    poke.level = 50
    poke.stats = PokemonStats(hp=hp, attack=50, defense=50, sp_attack=50, sp_defense=50, speed=50)
    return poke

def create_mock_context(pokemon):
    return BattleContext(
        pokemon=pokemon,
        moves=[],
        types=['normal'],
        current_hp=pokemon.stats.hp,
        is_user=True,
        stat_levels={},
        non_volatile_status=None,
        status_turns=0,
        volatile_statuses={},
        charging_move_id=None,
        protection_status=None
    )

def test_weather_expiration():
    print("--- Testing Weather Expiration ---")
    logger = ListBattleLogger(log_details=True)
    logic = BattleLogic()
    
    # User has Drizzle
    user_poke = create_mock_pokemon("User", ability_id=2) # Drizzle
    user_state = BattleState.from_context(create_mock_context(user_poke))
    wild_state = BattleState.from_context(create_mock_context(create_mock_pokemon("Wild", ability_id=0)))
    
    # 1. Trigger Entry -> Start Rain
    logic.handle_battle_start(user_state, wild_state, logger)
    print(f"Start Weather: {logic.current_weather}, Turns: {logic.weather_turns}")
    
    if logic.current_weather == "rain" and logic.weather_turns == 5:
        print("PASS: Rain started with 5 turns.")
    else:
        print("FAIL: Rain start fail.")
        return

    # 2. Simulate 4 turns
    for i in range(4):
        logic._update_weather_count(logger)
        print(f"End Turn {i+1}: Weather={logic.current_weather}, Turns={logic.weather_turns}")
        
    if logic.current_weather == "rain" and logic.weather_turns == 1:
        print("PASS: Rain persists after 4 turns.")
    else:
        print(f"FAIL: Rain ended too early or count wrong. Turns: {logic.weather_turns}")
        
    # 3. Last turn (Turn 5) -> Should clear
    logic._update_weather_count(logger)
    print(f"End Turn 5: Weather={logic.current_weather}, Turns={logic.weather_turns}")
    
    if logic.current_weather is None:
        print("PASS: Rain cleared after 5 turns.")
    else:
        print("FAIL: Rain did not clear.")

    # 4. Verify Hooks Removed
    # Create a water move and check damage
    # Mocking hook behavior: if hook exists, it modifies, else pure calculation
    # We can check registery directly or calculate damage
    
    move_water = BattleMoveInfo(
        move_id=1, move_name="Water Move", type_name="water", power=100,
        accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    # Mock stats
    logic._get_modified_stats = MagicMock(return_value=user_poke.stats)
    logic._get_atk_def_ratio = MagicMock(return_value=1.0)
    logic.calculate_type_effectiveness = MagicMock(return_value=1.0)
    
    dmg_normal, _, _ = logic._calculate_base_damage_params(user_state, wild_state, move_water)
    print(f"Damage post-rain: {dmg_normal}")
    
    # Without rain (1.5x), damage should be base ~46. With rain ~68.
    if dmg_normal < 60:
        print("PASS: Water damage returned to normal.")
    else:
        print(f"FAIL: Water damage still boosted ({dmg_normal}).")

if __name__ == "__main__":
    test_weather_expiration()
