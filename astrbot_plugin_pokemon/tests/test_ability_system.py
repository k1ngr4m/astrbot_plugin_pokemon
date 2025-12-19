
import sys
import os
from unittest.mock import MagicMock

# Mock astrbot module before imports
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()

# Mock random to avoid random damage fluctuation
import random
random.uniform = MagicMock(return_value=1.0)
random.random = MagicMock(return_value=0.5)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from astrbot_plugin_pokemon.core.services.battle.battle_engine import BattleState, BattleLogic, ListBattleLogger
from astrbot_plugin_pokemon.core.models.adventure_models import BattleContext, BattleMoveInfo
from astrbot_plugin_pokemon.core.models.pokemon_models import PokemonStats

# Mock objects
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
    # Mock moves needs to be a list of BattleMoveInfo
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

def test_intimidate():
    print("--- Testing Intimidate (ID: 22) ---")
    logger = ListBattleLogger()
    logic = BattleLogic()
    
    # User has Intimidate
    user_poke = create_mock_pokemon("User", ability_id=22) # Intimidate
    user_ctx = create_mock_context(user_poke)
    
    wild_poke = create_mock_pokemon("Wild", ability_id=0, attack=100)
    wild_ctx = create_mock_context(wild_poke)
    
    user_state = BattleState.from_context(user_ctx)
    wild_state = BattleState.from_context(wild_ctx)
    
    # Trigger entry effect via handle_battle_start
    logic.handle_battle_start(user_state, wild_state, logger)
    
    print("Logs:", logger.logs)
    
    # Check wild pokemon attack stat level
    atk_stage = wild_state.stat_levels.get(1, 0)
    print(f"Wild Attack Stage: {atk_stage}")
    
    if atk_stage == -1:
        print("PASS: Intimidate lowered attack.")
    else:
        print("FAIL: Intimidate did not lower attack.")

def test_blaze():
    print("\n--- Testing Blaze (ID: 66) ---")
    
    # User has Blaze
    user_poke = create_mock_pokemon("User", ability_id=66, hp=100) # Blaze
    user_ctx = create_mock_context(user_poke)
    
    wild_poke = create_mock_pokemon("Wild", ability_id=0)
    wild_ctx = create_mock_context(wild_poke)
    
    user_state = BattleState.from_context(user_ctx)
    wild_state = BattleState.from_context(wild_ctx)
    
    logic = BattleLogic()
    logic.calculate_type_effectiveness = MagicMock(return_value=1.0)
    logic._get_modified_stats = MagicMock(return_value=user_poke.stats) # Mock stats returning base stats
    
    move = BattleMoveInfo(
        move_id=1, move_name="Fire Move", type_name="fire", power=100,
        accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    
    # Case 1: HP > 1/3
    user_state.current_hp = 50
    dmg_high_hp, _, _ = logic._calculate_base_damage_params(user_state, wild_state, move)
    print(f"Damage at 50/100 HP: {dmg_high_hp}")
    
    # Case 2: HP < 1/3
    user_state.current_hp = 30
    dmg_low_hp, _, _ = logic._calculate_base_damage_params(user_state, wild_state, move)
    print(f"Damage at 30/100 HP: {dmg_low_hp}")
    
    if dmg_low_hp > dmg_high_hp:
        print("PASS: Blaze boosted damage at low HP.")
    else:
        print("FAIL: Blaze did not boost damage.")

def test_huge_power():
    print("\n--- Testing Huge Power (ID: 37) ---")
    
    # User has Huge Power (Base Attack = 100)
    user_poke = create_mock_pokemon("User", ability_id=37, attack=100)
    user_ctx = create_mock_context(user_poke)
    
    wild_poke = create_mock_pokemon("Wild", ability_id=0)
    wild_ctx = create_mock_context(wild_poke)
    
    user_state = BattleState.from_context(user_ctx)
    wild_state = BattleState.from_context(wild_ctx)
    
    logic = BattleLogic()
    
    # We need to ensure logic._get_modified_stats actually uses the state hooks
    # _get_modified_stats will look at state.hooks["on_stat_calc"]
    
    modified_stats = logic._get_modified_stats(user_state)
    print(f"Base Attack: {user_poke.stats.attack}")
    print(f"Modified Attack: {modified_stats.attack}")
    
    if modified_stats.attack == user_poke.stats.attack * 2:
        print("PASS: Huge Power doubled attack.")
    else:
        print("FAIL: Huge Power did not double attack.")


def test_levitate():
    print("\n--- Testing Levitate (ID: 26) ---")
    
    # Wild has Levitate
    user_poke = create_mock_pokemon("User", ability_id=0)
    user_ctx = create_mock_context(user_poke)
    
    wild_poke = create_mock_pokemon("Wild", ability_id=26) # Levitate
    wild_ctx = create_mock_context(wild_poke)
    
    user_state = BattleState.from_context(user_ctx)
    wild_state = BattleState.from_context(wild_ctx)
    
    logic = BattleLogic()
    logic.calculate_type_effectiveness = MagicMock(return_value=1.0) # Normal effectiveness
    logic._get_modified_stats = MagicMock(return_value=user_poke.stats)
    
    move = BattleMoveInfo(
        move_id=2, move_name="Ground Move", type_name="ground", power=100,
        accuracy=100, damage_class_id=2, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    
    dmg, eff, _ = logic._calculate_base_damage_params(user_state, wild_state, move)
    print(f"Damage: {dmg}, Effectiveness: {eff}")
    
    if eff == 0.0:
        print("PASS: Levitate provided immunity.")
    else:
        print(f"FAIL: Levitate did not provide immunity (eff={eff}).")

def test_volt_absorb():
    print("\n--- Testing Volt Absorb (ID: 10) ---")
    
    # Wild has Volt Absorb, HP damaged
    wild_poke = create_mock_pokemon("Wild", ability_id=10, hp=100) # Volt Absorb
    wild_ctx = create_mock_context(wild_poke)
    wild_ctx.current_hp = 50 # Damaged
    
    user_poke = create_mock_pokemon("User", ability_id=0)
    user_ctx = create_mock_context(user_poke)
    
    user_state = BattleState.from_context(user_ctx)
    wild_state = BattleState.from_context(wild_ctx)
    
    # Ensure current_hp is reflected in state
    wild_state.current_hp = 50
    
    logic = BattleLogic()
    logic.calculate_type_effectiveness = MagicMock(return_value=1.0)
    logic._get_modified_stats = MagicMock(return_value=user_poke.stats)
    
    # Electric Move
    move = BattleMoveInfo(
        move_id=3, move_name="Electric Move", type_name="electric", power=100,
        accuracy=100, damage_class_id=3, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    
    print(f"HP Before: {wild_state.current_hp}")
    
    # Calculate damage (should trigger immunity and heal)
    dmg, eff, _ = logic._calculate_base_damage_params(user_state, wild_state, move)
    
    print(f"Damage: {dmg}, Effectiveness: {eff}")
    print(f"HP After: {wild_state.current_hp}")
    
    expected_heal = 25 # 100 // 4
    if wild_state.current_hp == 50 + expected_heal and eff == 0.0:
        print("PASS: Volt Absorb healed and provided immunity.")
    else:
        print(f"FAIL: Volt Absorb failed. HP={wild_state.current_hp}, Eff={eff}")

if __name__ == "__main__":
    test_intimidate()
    test_blaze()
    test_huge_power()
    test_levitate()
    test_volt_absorb()
