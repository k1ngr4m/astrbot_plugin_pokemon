
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
from astrbot_plugin_pokemon.core.services.battle.weather_service import WeatherService

def create_mock_pokemon(name="TestPoke", ability_id=0, hp=100, types=['normal']):
    poke = MagicMock()
    poke.name = name
    poke.ability_id = ability_id
    poke.level = 50
    poke.stats = PokemonStats(hp=hp, attack=50, defense=50, sp_attack=50, sp_defense=50, speed=50)
    return poke

def create_mock_context(pokemon, types):
    return BattleContext(
        pokemon=pokemon,
        moves=[],
        types=types,
        current_hp=pokemon.stats.hp,
        is_user=True,
        stat_levels={},
        non_volatile_status=None,
        status_turns=0,
        volatile_statuses={},
        charging_move_id=None,
        protection_status=None
    )

def test_sandstorm_mechanics():
    print("--- Testing Sandstorm Mechanics ---")
    
    logic = BattleLogic()
    logger = ListBattleLogger()
    
    # 1. Apply Sandstorm
    WeatherService.apply_sandstorm(logic, logger)
    print(f"Weather set to: {logic.current_weather}")
    
    # 2. Test Sp. Def Boost (Rock Type)
    rock_poke = create_mock_pokemon("RockPoke", hp=100, types=['rock'])
    rock_state = BattleState.from_context(create_mock_context(rock_poke, ['rock']))
    
    # Needs to ensure _get_modified_stats triggers hooks
    # logic._get_modified_stats(rock_state) will call hooks
    
    # We must ensure creating BattleState sets up hooks? No, hooks are set up in BattleState usually? 
    # But BattleState only has `hooks` (HookManager).
    # Field hooks are in `logic.field_hooks`.
    # `_get_modified_stats` calls `state.hooks` AND `self.field_hooks`.
    
    modified_stats = logic._get_modified_stats(rock_state)
    print(f"Rock Sp.Def (Base 50): {modified_stats.sp_defense}")
    
    if modified_stats.sp_defense == 75: # 50 * 1.5
        print("PASS: Rock Sp. Def boosted.")
    else:
        print(f"FAIL: Rock Sp. Def not boosted (Expected 75, got {modified_stats.sp_defense})")
        
    # 3. Test Residual Damage (Normal Type)
    normal_poke = create_mock_pokemon("NormalPoke", hp=160, types=['normal'])
    normal_state = BattleState.from_context(create_mock_context(normal_poke, ['normal']))
    
    print(f"Normal HP Before: {normal_state.current_hp}")
    logic._apply_turn_end_effects(normal_state, rock_state, logger)
    print(f"Normal HP After: {normal_state.current_hp}")
    
    expected_hp = 160 - 10 # 1/16 of 160 is 10
    if normal_state.current_hp == expected_hp:
        print("PASS: Normal type took sandstorm damage.")
    else:
        print(f"FAIL: Normal type damage incorrect (Expected {expected_hp}, got {normal_state.current_hp})")
        
    # 4. Test Residual Immunity (Rock/Ground/Steel)
    rock_state.current_hp = 100
    print(f"Rock HP Before: {rock_state.current_hp}")
    logic._apply_turn_end_effects(rock_state, normal_state, logger)
    print(f"Rock HP After: {rock_state.current_hp}")
    
    if rock_state.current_hp == 100:
        print("PASS: Rock type immune to sandstorm damage.")
    else:
        print(f"FAIL: Rock type took damage.")

if __name__ == "__main__":
    test_sandstorm_mechanics()
