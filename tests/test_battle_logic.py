import sys
import os

# Add project root to path
sys.path.append(os.getcwd())
# sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "../../..")))

# Mock astrbot.api.logger
from unittest.mock import MagicMock
mock_astrbot = MagicMock()
mock_logger = MagicMock()
mock_astrbot.api.logger = mock_logger
sys.modules['astrbot'] = mock_astrbot
sys.modules['astrbot.api'] = mock_astrbot.api

from astrbot_plugin_pokemon.core.services.battle_engine import BattleLogic, BattleState, ListBattleLogger
from astrbot_plugin_pokemon.core.models.adventure_models import BattleContext, BattleMoveInfo
from astrbot_plugin_pokemon.core.models.pokemon_models import PokemonStats, WildPokemonInfo, PokemonMoves, PokemonIVs, PokemonEVs

def create_mock_pokemon(name, hp, attack, defense, speed, moves):
    stats = PokemonStats(hp=hp, attack=attack, defense=defense, sp_attack=attack, sp_defense=defense, speed=speed)
    ivs = PokemonIVs(0,0,0,0,0,0)
    evs = PokemonEVs(0,0,0,0,0,0)
    pmoves = PokemonMoves(0,0,0,0)
    
    return WildPokemonInfo(
        id=1, species_id=1, name=name, gender="M", level=50, exp=0,
        stats=stats, ivs=ivs, evs=evs, moves=pmoves
    )

def create_mock_move(name, power, type_name, priority=0, pp=10):
    return BattleMoveInfo(
        power=power, accuracy=100, type_name=type_name, damage_class_id=2,
        priority=priority, type_effectiveness=1.0, stab_bonus=1.0,
        max_pp=pp, current_pp=pp, move_id=1, move_name=name
    )

def test_battle_simulation():
    print("Testing Battle Simulation...")
    logic = BattleLogic()
    
    # User: Fast, Strong Attack
    user_poke = create_mock_pokemon("Pikachu", 100, 50, 30, 100, [])
    user_moves = [create_mock_move("Thunderbolt", 90, "electric")]
    user_ctx = BattleContext(user_poke, user_moves, ["electric"], 100, True)
    
    # Wild: Slow, Tanky
    wild_poke = create_mock_pokemon("Geodude", 100, 30, 50, 20, [])
    wild_moves = [create_mock_move("Tackle", 40, "normal")]
    wild_ctx = BattleContext(wild_poke, wild_moves, ["rock", "ground"], 100, False)
    
    # Run simulation
    user_wins = 0
    simulations = 100
    
    for _ in range(simulations):
        u_state = BattleState.from_context(user_ctx)
        w_state = BattleState.from_context(wild_ctx)
        
        turn = 0
        while u_state.current_hp > 0 and w_state.current_hp > 0 and turn < 20:
            turn += 1
            if logic.process_turn(u_state, w_state, ListBattleLogger()):
                break
        
        if u_state.current_hp > 0:
            user_wins += 1
            
    print(f"User Win Rate: {user_wins}/{simulations}")
    # Pikachu (Electric) vs Geodude (Ground) -> Electric has 0 effect on Ground.
    # Pikachu should lose unless it struggles? 
    # Wait, Thunderbolt on Ground is 0x.
    # So Pikachu will do 0 damage with Thunderbolt.
    # Eventually Pikachu runs out of PP and Struggles?
    # Or logic handles 0 damage.
    
    # Let's see if logic works.
    
def test_real_battle_flow():
    print("\nTesting Real Battle Flow...")
    logic = BattleLogic()
    logger = ListBattleLogger()
    
    # User: Charmander
    user_poke = create_mock_pokemon("Charmander", 50, 40, 30, 40, [])
    user_moves = [create_mock_move("Scratch", 40, "normal", pp=2)] # Low PP to test struggle
    user_ctx = BattleContext(user_poke, user_moves, ["fire"], 50, True)
    
    # Wild: Bulbasaur
    wild_poke = create_mock_pokemon("Bulbasaur", 50, 40, 30, 30, [])
    wild_moves = [create_mock_move("Tackle", 40, "normal")]
    wild_ctx = BattleContext(wild_poke, wild_moves, ["grass"], 50, False)
    
    u_state = BattleState.from_context(user_ctx)
    w_state = BattleState.from_context(wild_ctx)
    
    turn = 0
    while u_state.current_hp > 0 and w_state.current_hp > 0 and turn < 10:
        turn += 1
        print(f"Turn {turn}")
        ended = logic.process_turn(u_state, w_state, logger)
        if ended:
            print("Battle Ended")
            break
            
    for log in logger.logs:
        print(log.strip())
        
    print(f"Final HP: User {u_state.current_hp}, Wild {w_state.current_hp}")
    print(f"User Move PP: {u_state.current_pps[0]}")

if __name__ == "__main__":
    test_battle_simulation()
    test_real_battle_flow()
