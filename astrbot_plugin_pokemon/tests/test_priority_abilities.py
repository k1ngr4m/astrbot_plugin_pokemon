
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
from astrbot_plugin_pokemon.core.services.battle.ability_plugins import AbilityRegistry, PranksterAbility, GaleWingsAbility

# Helper to create poke
def create_mock_pokemon(name="TestPoke", ability_id=0, hp=100, speed=50):
    poke = MagicMock()
    poke.name = name
    poke.ability_id = ability_id
    poke.level = 50
    poke.stats = PokemonStats(hp=hp, attack=50, defense=50, sp_attack=50, sp_defense=50, speed=speed)
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

def test_priority_abilities():
    print("--- Testing Priority Modification Abilities ---")
    logger = ListBattleLogger()
    logic = BattleLogic()
    logic._get_modified_stats = MagicMock(side_effect=lambda s: s.context.pokemon.stats)

    # --- Scenario 1: Prankster (ID 158) ---
    print("\n[Scenario 1] Prankster (Speed 10) vs Fast Opponent (Speed 100)")
    # Prankster user: Slow
    p_poke = create_mock_pokemon("PranksterUser", ability_id=158, speed=10)
    p_ctx = create_mock_context(p_poke)
    p_state = BattleState.from_context(p_ctx)
    
    # Fast Opponent
    f_poke = create_mock_pokemon("FastOpponent", ability_id=0, speed=100)
    f_ctx = create_mock_context(f_poke)
    f_state = BattleState.from_context(f_ctx)
    
    # Moves
    # Status Move (Class 1) - Priority 0 (Base) -> Prankster should make it +1
    move_status = BattleMoveInfo(move_id=1, move_name="Thunder Wave", priority=0, damage_class_id=1, type_name="electric", power=0, accuracy=100, type_effectiveness=1.0, stab_bonus=1.0, max_pp=10, current_pp=10, meta_category_id=1)
    
    # Attack Move (Class 2) - Priority 0
    move_attack = BattleMoveInfo(move_id=2, move_name="Tackle", priority=0, damage_class_id=2, type_name="normal", power=40, accuracy=100, type_effectiveness=1.0, stab_bonus=1.0, max_pp=35, current_pp=35, meta_category_id=0)
    
    # Check Prankster Priority
    prio_p = logic._get_effective_priority(p_state, move_status)
    print(f"Prankster User Priority (Status Move): {prio_p} (Expected 1)")
    
    priority_order = logic._is_user_first(p_state, f_state, move_status, move_attack)
    print(f"Prankster vs Fast Attack: User goes first? {priority_order}")
    
    if prio_p == 1 and priority_order == True:
        print("PASS: Prankster correctly increased priority for Status Move.")
    else:
        print("FAIL: Prankster logic incorrect.")
        
    # Check Prankster Normal Attack (Should be 0)
    prio_p_atk = logic._get_effective_priority(p_state, move_attack)
    if prio_p_atk == 0:
        print("PASS: Prankster ignores Attack Move.")
    else:
         print(f"FAIL: Prankster boosted Attack Move? {prio_p_atk}")


    # --- Scenario 2: Gale Wings (ID 177) ---
    print("\n[Scenario 2] Gale Wings (Speed 10) vs Fast Opponent (Speed 100)")
    g_poke = create_mock_pokemon("GaleWingsUser", ability_id=177, speed=10)
    g_ctx = create_mock_context(g_poke)
    g_state = BattleState.from_context(g_ctx)
    
    # Flying Move: Brave Bird
    move_flying = BattleMoveInfo(move_id=3, move_name="Brave Bird", priority=0, damage_class_id=2, type_name="flying", power=120, accuracy=100, type_effectiveness=1.0, stab_bonus=1.0, max_pp=15, current_pp=15, meta_category_id=0)
    
    # Case A: Full HP
    prio_g = logic._get_effective_priority(g_state, move_flying)
    print(f"Gale Wings (Full HP) Priority: {prio_g} (Expected 1)")
    
    priority_order_g = logic._is_user_first(g_state, f_state, move_flying, move_attack)
    print(f"Gale Wings (Full HP) vs Fast Attack: User goes first? {priority_order_g}")
    
    if prio_g == 1 and priority_order_g == True:
        print("PASS: Gale Wings boosted Flying move at Full HP.")
    else:
        print("FAIL: Gale Wings logic incorrect at Full HP.")
        
    # Case B: Not Full HP
    g_state.current_hp -= 1
    prio_g_hurt = logic._get_effective_priority(g_state, move_flying)
    print(f"Gale Wings (Hurt) Priority: {prio_g_hurt} (Expected 0)")
    
    priority_order_g_hurt = logic._is_user_first(g_state, f_state, move_flying, move_attack)
    if prio_g_hurt == 0 and priority_order_g_hurt == False:
         print("PASS: Gale Wings inactive when not full HP.")
    else:
         print("FAIL: Gale Wings still active when hurt?")

if __name__ == "__main__":
    test_priority_abilities()
