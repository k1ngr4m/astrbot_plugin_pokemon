
import sys
import os
from unittest.mock import MagicMock

# Mock astrbot module before imports
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()

# Mock random logic
import random
random.uniform = MagicMock(return_value=1.0)
random.random = MagicMock(return_value=0.5)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from astrbot_plugin_pokemon.core.services.battle.battle_engine import BattleState, BattleLogic, ListBattleLogger
from astrbot_plugin_pokemon.core.models.adventure_models import BattleContext, BattleMoveInfo
from astrbot_plugin_pokemon.core.models.pokemon_models import PokemonStats
from astrbot_plugin_pokemon.core.services.battle.ability_plugins import AbilityRegistry, WeakArmorAbility, JustifiedAbility

def create_mock_pokemon(name="TestPoke", ability_id=0, hp=100, attack=50, defense=50, speed=50):
    poke = MagicMock()
    poke.name = name
    poke.ability_id = ability_id
    poke.level = 50
    poke.stats = PokemonStats(hp=hp, attack=attack, defense=defense, sp_attack=50, sp_defense=50, speed=speed)
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

def test_damage_trigger_abilities():
    print("--- Testing Incoming Damage Trigger Abilities (Weak Armor, Justified) ---")
    
    logger = ListBattleLogger()
    logic = BattleLogic()

    # --- Scenario 1: Weak Armor (ID 144) ---
    print("\n[Scenario 1] Weak Armor User hit by Physical Move")
    wa_poke = create_mock_pokemon("WeakArmorUser", ability_id=144, defense=100, speed=100)
    wa_ctx = create_mock_context(wa_poke)
    wa_state = BattleState.from_context(wa_ctx)
    
    attacker_poke = create_mock_pokemon("Attacker", ability_id=0)
    attacker_ctx = create_mock_context(attacker_poke)
    attacker_state = BattleState.from_context(attacker_ctx)
    
    # Physical Move
    move_physical = BattleMoveInfo(move_id=1, move_name="Tackle", damage_class_id=2, priority=0, type_name="normal", power=40, accuracy=100, type_effectiveness=1.0, stab_bonus=1.0, max_pp=35, current_pp=35, meta_category_id=0)
    
    # Special Move (Control)
    move_special = BattleMoveInfo(move_id=2, move_name="Ember", damage_class_id=3, priority=0, type_name="fire", power=40, accuracy=100, type_effectiveness=1.0, stab_bonus=1.0, max_pp=25, current_pp=25, meta_category_id=0)
    
    # 1. Hit by Physical
    print("  Hit by Physical Move (Damage 10)...")
    wa_state.hooks.trigger_event("after_damage", wa_state, attacker_state, move_physical, 10, logger)
    
    def_lvl = wa_state.stat_levels.get(2, 0)
    spd_lvl = wa_state.stat_levels.get(5, 0)
    print(f"  Defense Level: {def_lvl} (Expected -1)")
    print(f"  Speed Level: {spd_lvl} (Expected 2)")
    
    if def_lvl == -1 and spd_lvl == 2:
        print("PASS: Weak Armor triggered correctly on Physical hit.")
    else:
        print("FAIL: Weak Armor logic issue.")
        
    # 2. Hit by Special (Should do nothing)
    print("  Hit by Special Move (Damage 10)...")
    wa_state.hooks.trigger_event("after_damage", wa_state, attacker_state, move_special, 10, logger)
    
    def_lvl_2 = wa_state.stat_levels.get(2, 0)
    spd_lvl_2 = wa_state.stat_levels.get(5, 0)
    if def_lvl_2 == -1 and spd_lvl_2 == 2:
        print("PASS: Weak Armor ignored Special hit.")
    else:
        print(f"FAIL: Weak Armor triggered on Special hit? Def={def_lvl_2}, Spd={spd_lvl_2}")


    # --- Scenario 2: Justified (ID 154) ---
    print("\n[Scenario 2] Justified User hit by Dark Move")
    j_poke = create_mock_pokemon("JustifiedUser", ability_id=154, attack=100)
    j_ctx = create_mock_context(j_poke)
    j_state = BattleState.from_context(j_ctx)
    
    # Dark Move
    move_dark = BattleMoveInfo(move_id=3, move_name="Bite", damage_class_id=2, priority=0, type_name="dark", power=60, accuracy=100, type_effectiveness=1.0, stab_bonus=1.0, max_pp=25, current_pp=25, meta_category_id=0)
    
    # Normal Move
    print("  Hit by Normal Move...")
    j_state.hooks.trigger_event("after_damage", j_state, attacker_state, move_physical, 10, logger)
    atk_lvl_0 = j_state.stat_levels.get(1, 0)
    if atk_lvl_0 == 0:
        print("PASS: Justified ignored non-Dark move.")
        
    print("  Hit by Dark Move...")
    j_state.hooks.trigger_event("after_damage", j_state, attacker_state, move_dark, 10, logger)
    atk_lvl_1 = j_state.stat_levels.get(1, 0)
    print(f"  Attack Level: {atk_lvl_1} (Expected 1)")
    
    if atk_lvl_1 == 1:
        print("PASS: Justified triggered on Dark move.")
    else:
        print("FAIL: Justified failed to trigger.")

if __name__ == "__main__":
    test_damage_trigger_abilities()
