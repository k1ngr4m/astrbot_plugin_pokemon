
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

from astrbot_plugin_pokemon.core.services.battle.battle_engine import BattleState, BattleLogic, ListBattleLogger, NoOpBattleLogger
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

def test_feedback_mechanism():
    print("--- Testing Battle Feedback ---")
    
    # Setup
    logic = BattleLogic()
    logic.calculate_type_effectiveness = MagicMock(return_value=1.0)
    logic._get_modified_stats = MagicMock(return_value=create_mock_pokemon().stats)
    logic._get_atk_def_ratio = MagicMock(return_value=1.0)
    
    # 1. Test Immunity Feedback (Volt Absorb)
    user_poke = create_mock_pokemon("User", ability_id=10) # Volt Absorb
    user_state = BattleState.from_context(create_mock_context(user_poke))
    
    attacker_poke = create_mock_pokemon("Attacker", ability_id=0)
    attacker_state = BattleState.from_context(create_mock_context(attacker_poke))
    
    move_electric = BattleMoveInfo(move_id=1, move_name="Thunder Shock", type_name="electric", power=40, accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0, max_pp=10, current_pp=10, meta_category_id=0)
    
    logger = ListBattleLogger()
    print("Testing Immunity Feedback (Real Logger)...")
    logic._calculate_base_damage_params(attacker_state, user_state, move_electric, logger)
    
    logs = logger.logs
    print(f"Logs: {logs}")
    if any("免疫" in log for log in logs):
        print("PASS: Immunity logged.")
    else:
        print("FAIL: Immunity not logged.")

    # 2. Test Silence (NoOpLogger)
    print("\nTesting Silence (NoOpLogger)...")
    noop = NoOpBattleLogger()
    # We can't easily check 'logs' from NoOp, but we can ensure no error and no print (implicit)
    # Actually, we can check if print() was called if we mock print, but here we just ensure implementation flow.
    # A better check: using a Mock object as logger that mocks NoOpBattleLogger
    mock_noop = MagicMock(spec=NoOpBattleLogger)
    mock_noop.__class__.__name__ = 'NoOpBattleLogger' # Simulate class name
    
    logic._calculate_base_damage_params(attacker_state, user_state, move_electric, mock_noop)
    
    if len(mock_noop.log.mock_calls) == 0:
        print("PASS: No log calls made to NoOpLogger.")
    else:
        print(f"FAIL: Log calls made to NoOpLogger: {mock_noop.log.mock_calls}")
        
    # 3. Test Weather Feedback
    print("\nTesting Weather Feedback (Rain)...")
    # Set rain
    logic.current_weather = "rain"
    from astrbot_plugin_pokemon.core.services.battle.weather_service import WeatherService
    WeatherService.apply_rain(logic, logger) # Register hook
    
    move_water = BattleMoveInfo(move_id=2, move_name="Water Gun", type_name="water", power=40, accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0, max_pp=10, current_pp=10, meta_category_id=0)
    
    logger = ListBattleLogger() # Reset logger
    logic._calculate_base_damage_params(attacker_state, user_state, move_water, logger)
    
    logs = logger.logs
    print(f"Logs: {logs}")
    if any("威力提升" in log for log in logs):
        print("PASS: Rain boost logged.")
    else:
        print("FAIL: Rain boost not logged.")

if __name__ == "__main__":
    test_feedback_mechanism()
