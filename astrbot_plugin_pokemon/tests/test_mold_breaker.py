
import sys
import os
from unittest.mock import MagicMock

# Mock astrbot module before imports
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()

# Mock random to be deterministic
import random
random.uniform = MagicMock(return_value=1.0)
random.random = MagicMock(return_value=0.5)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from astrbot_plugin_pokemon.core.services.battle.battle_engine import BattleState, BattleLogic, ListBattleLogger, NoOpBattleLogger
from astrbot_plugin_pokemon.core.models.adventure_models import BattleContext, BattleMoveInfo
from astrbot_plugin_pokemon.core.models.pokemon_models import PokemonStats
from astrbot_plugin_pokemon.core.services.battle.ability_plugins import AbilityRegistry, LevitateAbility

# 确保特性已注册 (Importing ability_plugins triggers decorators)

def create_mock_pokemon(name="TestPoke", ability_id=0):
    poke = MagicMock()
    poke.name = name
    poke.ability_id = ability_id
    poke.level = 50
    poke.stats = PokemonStats(hp=100, attack=100, defense=50, sp_attack=50, sp_defense=50, speed=50)
    return poke

def create_mock_context(pokemon, types=None):
    if types is None:
        types = ['electric'] # Defender is usually Electric/Steel type for Levitate (e.g. Bronzong/Rotom)
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

def test_mold_breaker():
    print("--- Testing Mold Breaker (ID: 104) vs Levitate (ID: 26) ---")
    logger = ListBattleLogger()
    logic = BattleLogic()
    # Mock effectiveness: Ground vs Electric is usually 2.0 (Super Effective), but Levitate makes it 0.
    # Logic.calculate_type_effectiveness needs to return > 0 for us to test if Levitate sets it to 0.
    # Let's mock it to return 2.0
    logic.calculate_type_effectiveness = MagicMock(return_value=2.0)
    
    # --- Scenario 1: Normal Attacker vs Levitate ---
    print("\n[Scenario 1] Normal Attacker (No Mold Breaker) uses Earthquake vs Levitate")
    
    attacker_poke = create_mock_pokemon("NormalAttacker", ability_id=0)
    attacker_ctx = create_mock_context(attacker_poke, types=['normal'])
    attacker_state = BattleState.from_context(attacker_ctx)
    
    defender_poke = create_mock_pokemon("LevitateDefender", ability_id=26) # Levitate
    defender_ctx = create_mock_context(defender_poke, types=['electric'])
    defender_state = BattleState.from_context(defender_ctx)
    
    # Move: Earthquake (Ground)
    earthquake = BattleMoveInfo(
        move_id=1, move_name="Earthquake", type_name="ground", power=100,
        accuracy=100, damage_class_id=2, priority=0, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=10, current_pp=10, meta_category_id=0
    )
    
    # Mock stats helper methods
    logic._get_modified_stats = MagicMock(side_effect=lambda s: s.context.pokemon.stats)
    
    dmg, eff, _ = logic._calculate_base_damage_params(attacker_state, defender_state, earthquake, logger)
    print(f"Damage: {dmg}, Effectiveness: {eff}")
    
    if dmg == 0 and eff == 0:
        print("PASS: Levitate correctly blocked the attack (Damage is 0).")
    else:
        print(f"FAIL: Attack should have been blocked! Dmg={dmg}, Eff={eff}")

    # --- Scenario 2: Mold Breaker Attacker vs Levitate ---
    print("\n[Scenario 2] Mold Breaker Attacker (ID 104) uses Earthquake vs Levitate")
    
    mb_poke = create_mock_pokemon("MoldBreakerAttacker", ability_id=104) # Mold Breaker
    mb_ctx = create_mock_context(mb_poke, types=['dragon']) # e.g. Haxorus
    mb_state = BattleState.from_context(mb_ctx)
    
    # Reset Defender (Hooks might have been used, safest to recreate or clear hooks - but hooks are re-registered on init)
    defender_state_2 = BattleState.from_context(defender_ctx) # Recreate fresh
    
    dmg_mb, eff_mb, _ = logic._calculate_base_damage_params(mb_state, defender_state_2, earthquake, logger)
    print(f"Damage: {dmg_mb}, Effectiveness: {eff_mb}")
    
    if dmg_mb > 0 and eff_mb > 0:
        print("PASS: Mold Breaker bypassed Levitate! Damage calculated.")
    else:
        print(f"FAIL: Mold Breaker failed to bypass Levitate. Dmg={dmg_mb}, Eff={eff_mb}")

    # --- Scenario 3: AI Scoring Check ---
    print("\n[Scenario 3] AI Scoring Check")
    # Reset logger and ensure no logs from AI
    score_normal = logic._calculate_unified_move_score(attacker_state, defender_state, earthquake, NoOpBattleLogger())
    score_mb = logic._calculate_unified_move_score(mb_state, defender_state_2, earthquake, NoOpBattleLogger())
    
    print(f"Score (Normal): {score_normal}")
    print(f"Score (Mold Breaker): {score_mb}")
    
    # Note: If base logic returns -100 for immune, then score_normal should be -100 (plus jitter).
    # score_mb should be positive (damage > 0)
    
    if score_normal < 0 and score_mb > 10:
        print("PASS: AI recognizes Earthquake is useless for Normal but good for Mold Breaker.")
    else:
        print(f"FAIL: AI scores logic issue. Normal={score_normal}, MB={score_mb}")

if __name__ == "__main__":
    test_mold_breaker()
