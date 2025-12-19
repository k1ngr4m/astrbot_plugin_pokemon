
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

def create_mock_pokemon(name="TestPoke", ability_id=0, hp=100, attack=50, defense=50, sp_attack=50, sp_defense=50, speed=50):
    poke = MagicMock()
    poke.name = name
    poke.ability_id = ability_id
    poke.level = 50
    poke.stats = PokemonStats(hp=hp, attack=attack, defense=defense, sp_attack=sp_attack, sp_defense=sp_defense, speed=speed)
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

def test_ai_avoid_immunity():
    print("--- Testing AI Avoid Immunity (Volt Absorb) ---")
    logger = ListBattleLogger()
    logic = BattleLogic()
    logic.calculate_type_effectiveness = MagicMock(return_value=1.0)
    
    # User has Electric Move
    user_poke = create_mock_pokemon("User", ability_id=0)
    move_electric = BattleMoveInfo(
        move_id=1, move_name="Electric Move", type_name="electric", power=100,
        accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    user_ctx = create_mock_context(user_poke, moves=[move_electric])
    
    # Wild has Volt Absorb (ID 10)
    wild_poke = create_mock_pokemon("Wild", ability_id=10)
    wild_ctx = create_mock_context(wild_poke)
    
    user_state = BattleState.from_context(user_ctx)
    wild_state = BattleState.from_context(wild_ctx)
    
    # Need to set up get_atk_def_ratio mock since we are mocking objects
    logic._get_atk_def_ratio = MagicMock(return_value=1.0)
    logic._get_modified_stats = MagicMock(return_value=user_poke.stats)
    
    # Check score
    score = logic._calculate_unified_move_score(user_state, wild_state, move_electric, logger)
    print(f"Score against Volt Absorb: {score}")
    
    if score == -100.0:
        print("PASS: AI correctly identified immunity and gave negative score.")
    else:
        print("FAIL: AI did not avoid immunity.")

def test_ai_prefer_blaze():
    print("\n--- Testing AI Prefer Blaze (Blaze) ---")
    logger = ListBattleLogger()
    logic = BattleLogic()
    logic.calculate_type_effectiveness = MagicMock(side_effect=lambda types, target_types: 1.0)
    logic._get_atk_def_ratio = MagicMock(return_value=1.0)
    logic._get_modified_stats = MagicMock(return_value=PokemonStats(hp=100, attack=50, defense=50, sp_attack=50, sp_defense=50, speed=50))
    
    # User has Blaze (ID 66)
    user_poke = create_mock_pokemon("User", ability_id=66, hp=100)
    
    move_fire = BattleMoveInfo(
        move_id=1, move_name="Fire Move", type_name="fire", power=100,
        accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    move_normal = BattleMoveInfo(
        move_id=2, move_name="Normal Move", type_name="normal", power=100,
        accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    
    user_ctx = create_mock_context(user_poke, moves=[move_fire, move_normal])
    wild_poke = create_mock_pokemon("Wild", ability_id=0)
    wild_ctx = create_mock_context(wild_poke)
    
    user_state = BattleState.from_context(user_ctx)
    wild_state = BattleState.from_context(wild_ctx)
    
    # Case 1: High HP (No Boost)
    print("Scenario: High HP")
    score_fire = logic._calculate_unified_move_score(user_state, wild_state, move_fire, logger)
    score_normal = logic._calculate_unified_move_score(user_state, wild_state, move_normal, logger)
    
    print(f"Score Fire: {score_fire}, Score Normal: {score_normal}")
    # Scores should be roughly equal (ignoring minor variations if any)
    
    # Case 2: Low HP (Blaze Boost)
    print("Scenario: Low HP (< 1/3)")
    user_state.current_hp = 30
    
    score_fire_boosted = logic._calculate_unified_move_score(user_state, wild_state, move_fire, logger)
    score_normal_boosted = logic._calculate_unified_move_score(user_state, wild_state, move_normal, logger)
    
    print(f"Score Fire (Boosted): {score_fire_boosted}, Score Normal: {score_normal_boosted}")
    
    if score_fire_boosted > score_fire * 1.4: # Should be roughly 1.5x
         print("PASS: AI score for Fire move increased significantly at low HP.")
    else:
         print("FAIL: AI score did not reflect Blaze boost.")

if __name__ == "__main__":
    test_ai_avoid_immunity()
    test_ai_prefer_blaze()
