
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

def create_mock_context(pokemon, moves=None):
    if moves is None:
        moves = []
    return BattleContext(
        pokemon=pokemon,
        moves=moves,
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

def test_rain_mechanics():
    print("--- Testing Rain Mechanics (Drizzle ID: 2) ---")
    logger = ListBattleLogger()
    logic = BattleLogic()
    logic.calculate_type_effectiveness = MagicMock(return_value=1.0)
    
    # User has Drizzle
    user_poke = create_mock_pokemon("User", ability_id=2) # Drizzle
    user_ctx = create_mock_context(user_poke)
    
    wild_poke = create_mock_pokemon("Wild", ability_id=0)
    wild_ctx = create_mock_context(wild_poke)
    
    user_state = BattleState.from_context(user_ctx)
    wild_state = BattleState.from_context(wild_ctx)
    
    # 1. Trigger Entry Effect (Start Rain)
    logic.handle_battle_start(user_state, wild_state, logger)
    
    print(f"Current Weather: {logic.current_weather}")
    if logic.current_weather == "rain":
        print("PASS: Drizzle started rain.")
    else:
        print("FAIL: Drizzle did not start rain.")
        
    # 2. Check Damage Mods
    move_water = BattleMoveInfo(
        move_id=1, move_name="Water Move", type_name="water", power=100,
        accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    move_fire = BattleMoveInfo(
        move_id=2, move_name="Fire Move", type_name="fire", power=100,
        accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    
    # Mock stats to ensure consistency
    logic._get_modified_stats = MagicMock(return_value=user_poke.stats)
    logic._get_atk_def_ratio = MagicMock(return_value=1.0)
    
    # Calculate Water Damage
    dmg_water, _, _ = logic._calculate_base_damage_params(user_state, wild_state, move_water)
    print(f"Water Damage (Rain): {dmg_water}")
    
    # Calculate Fire Damage
    dmg_fire, _, _ = logic._calculate_base_damage_params(user_state, wild_state, move_fire)
    print(f"Fire Damage (Rain): {dmg_fire}")
    
    # Approximate values: Base ~24. Water * 1.5 ~ 36. Fire * 0.5 ~ 12.
    if dmg_water > 25 and dmg_fire < 25:
          print("PASS: Rain boosted Water and weakened Fire.")
    else:
          print("FAIL: Rain damage modifiers incorrect.")
          
    # 3. Check AI Scoring
    print("\n--- Testing AI Awareness of Rain ---")
    score_water = logic._calculate_unified_move_score(user_state, wild_state, move_water, logger)
    score_fire = logic._calculate_unified_move_score(user_state, wild_state, move_fire, logger)
    
    print(f"Score Water: {score_water}")
    print(f"Score Fire: {score_fire}")
    
    if score_water > score_fire * 2:
        print("PASS: AI favored Water move in Rain.")
    else:
        print("FAIL: AI did not favor Water move well enough.")

if __name__ == "__main__":
    test_rain_mechanics()
