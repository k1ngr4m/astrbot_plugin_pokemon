
import sys
import os
from unittest.mock import MagicMock

# Mock astrbot module before imports
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()

# Mock random logic
import random
random.uniform = MagicMock(return_value=1.0)
random.random = MagicMock(return_value=0.1) # Force low value to trigger 30% chance for Static

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from astrbot_plugin_pokemon.core.services.battle.battle_engine import BattleState, BattleLogic, ListBattleLogger
from astrbot_plugin_pokemon.core.models.adventure_models import BattleContext, BattleMoveInfo
from astrbot_plugin_pokemon.core.models.pokemon_models import PokemonStats
from astrbot_plugin_pokemon.core.services.battle.ability_plugins import AbilityRegistry, RoughSkinAbility, StaticAbility

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

def test_contact_abilities():
    print("--- Testing Contact Move Abilities (Rough Skin, Static) ---")
    
    logger = ListBattleLogger()

    # --- Scenario 1: Rough Skin (ID 24) ---
    print("\n[Scenario 1] Rough Skin User hit by Contact Move")
    rs_poke = create_mock_pokemon("RoughSkinUser", ability_id=24, hp=100)
    rs_ctx = create_mock_context(rs_poke)
    rs_state = BattleState.from_context(rs_ctx)
    
    attacker_poke = create_mock_pokemon("Attacker", ability_id=0, hp=100)
    attacker_ctx = create_mock_context(attacker_poke)
    attacker_state = BattleState.from_context(attacker_ctx)
    
    # Contact Move
    move_contact = BattleMoveInfo(move_id=1, move_name="Tackle", damage_class_id=2, priority=0, type_name="normal", power=40, accuracy=100, type_effectiveness=1.0, stab_bonus=1.0, max_pp=35, current_pp=35, meta_category_id=0, is_contact=True)
    
    # Non-Contact Move
    move_non_contact = BattleMoveInfo(move_id=2, move_name="Earthquake", damage_class_id=2, priority=0, type_name="ground", power=100, accuracy=100, type_effectiveness=1.0, stab_bonus=1.0, max_pp=10, current_pp=10, meta_category_id=0, is_contact=False)
    
    # 1. Hit by Contact
    print("  Hit by Contact Move...")
    rs_state.hooks.trigger_event("after_damage", rs_state, attacker_state, move_contact, 10, logger)
    
    attacker_hp_1 = attacker_state.current_hp
    recoil = 100 // 8 # 12
    expected_hp = 100 - 12
    print(f"  Attacker HP: {attacker_hp_1} (Expected {expected_hp})")
    
    if attacker_hp_1 == expected_hp:
        print("PASS: Rough Skin inflicted recoil.")
    else:
        print(f"FAIL: Rough Skin recoil incorrect. HP={attacker_hp_1}")
        
    # 2. Hit by Non-Contact
    print("\n[Scenario 2] Rough Skin User hit by Non-Contact Move")
    # Reset attacker HP for clarity
    attacker_state.current_hp = 100
    print("  Hit by Non-Contact Move...")
    rs_state.hooks.trigger_event("after_damage", rs_state, attacker_state, move_non_contact, 10, logger)
    
    attacker_hp_2 = attacker_state.current_hp
    print(f"  Attacker HP: {attacker_hp_2} (Expected 100)")
    
    if attacker_hp_2 == 100:
        print("PASS: Rough Skin ignored non-contact move.")
    else:
        print("FAIL: Rough Skin triggered on non-contact?")

    # --- Scenario 3: Static (ID 9) ---
    print("\n[Scenario 3] Static User hit by Contact Move")
    static_poke = create_mock_pokemon("StaticUser", ability_id=9)
    static_ctx = create_mock_context(static_poke)
    static_state = BattleState.from_context(static_ctx)
    
    attacker_state.current_hp = 100
    attacker_state.non_volatile_status = None # Reset Status
    
    print("  Hit by Contact Move (Random < 0.3)...")
    static_state.hooks.trigger_event("after_damage", static_state, attacker_state, move_contact, 10, logger)
    
    status_id = attacker_state.non_volatile_status
    print(f"  Attacker Status: {status_id} (Expected 1 for Paralysis)")
    
    if status_id == 1:
        print("PASS: Static paralyzed the attacker.")
    else:
        print("FAIL: Static failed to paralyze.")

if __name__ == "__main__":
    test_contact_abilities()
