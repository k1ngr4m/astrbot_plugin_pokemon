import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock astrbot module before imports
sys.modules['astrbot'] = MagicMock()
sys.modules['astrbot.api'] = MagicMock()
sys.modules['astrbot.api.event'] = MagicMock()
sys.modules['astrbot.api.star'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from astrbot_plugin_pokemon.core.services.world.adventure_service import AdventureService
from astrbot_plugin_pokemon.core.models.pokemon_models import UserPokemonInfo, PokemonStats, PokemonIVs, PokemonEVs, PokemonMoves, PokemonSpecies

class TestPvPSystem(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.adventure_repo = MagicMock()
        self.pokemon_repo = MagicMock()
        self.team_repo = MagicMock()
        self.pokemon_service = MagicMock()
        self.user_repo = MagicMock()
        self.user_pokemon_repo = MagicMock()
        self.battle_repo = MagicMock()
        self.user_item_repo = MagicMock()
        self.move_repo = MagicMock()
        self.ability_repo = MagicMock()
        self.exp_service = MagicMock()
        self.config = {}

        # Mock Nature Service
        self.nature_service = MagicMock()
        self.pokemon_service.nature_service = self.nature_service
        self.nature_service.apply_nature_modifiers.side_effect = lambda stats, n_id: stats  # No modifier

        self.service = AdventureService(
            self.adventure_repo, self.pokemon_repo, self.team_repo,
            self.pokemon_service, self.user_repo, self.user_pokemon_repo,
            self.battle_repo, self.user_item_repo, self.move_repo,
            self.ability_repo, self.exp_service, self.config
        )

    def test_pvp_stats_scaling(self):
        print("Testing PvP Stats Scaling...")
        # Setup mock data
        user_id = "test_user"
        species_id = 1
        
        # Original Pokemon: Level 100, perfect IVs/EVs
        original_stats = PokemonStats(hp=300, attack=300, defense=300, sp_attack=300, sp_defense=300, speed=300)
        original_ivs = PokemonIVs(hp_iv=31, attack_iv=31, defense_iv=31, sp_attack_iv=31, sp_defense_iv=31, speed_iv=31)
        original_evs = PokemonEVs(hp_ev=252, attack_ev=252, defense_ev=252, sp_attack_ev=252, sp_defense_ev=252, speed_ev=252)
        original_moves = PokemonMoves(move1_id=1, move2_id=2, move3_id=3, move4_id=4)
        
        pokemon_info = UserPokemonInfo(
            id=1, species_id=species_id, name="TestMon", 
            level=100, exp=0, gender="M", nature_id=0,
            stats=original_stats, ivs=original_ivs, evs=original_evs, moves=original_moves
        )

        # Mock Species Base Stats
        species = MagicMock()
        species.base_stats = {
            "base_hp": 100, "base_attack": 100, "base_defense": 100,
            "base_sp_attack": 100, "base_sp_defense": 100, "base_speed": 100
        }
        self.pokemon_repo.get_pokemon_by_id.return_value = species

        # Mock Move Repo
        self.move_repo.get_level_up_moves.return_value = [10, 11, 12, 13, 14] # ids

        # Mock _preload_moves (it makes DB calls)
        self.service._preload_moves = MagicMock(return_value=[])
        
        # Mock Battle Logic to avoid errors in context creation if any
        self.service.battle_logic = MagicMock()

        # Execute
        context = self.service._create_pvp_battle_context(user_id, pokemon_info)

        # Verify
        # Level should be 50
        # HP Formula: (Base*2 + IV + EV/4) * Level/100 + Level + 10
        # HP: (100*2 + 31 + 63) * 50/100 + 50 + 10 = 294 * 0.5 + 60 = 147 + 60 = 207
        # Stat Formula: (Base*2 + IV + EV/4) * Level/100 + 5
        # Stat: 294 * 0.5 + 5 = 147 + 5 = 152
        
        scaled_pokemon = context.pokemon
        print(f"Original Level: {pokemon_info.level}, Scaled Level: {scaled_pokemon.level}")
        print(f"Scaled HP: {scaled_pokemon.stats.hp} (Expected 207)")
        print(f"Scaled Attack: {scaled_pokemon.stats.attack} (Expected 152)")
        
        self.assertEqual(scaled_pokemon.stats.hp, 207)
        self.assertEqual(scaled_pokemon.stats.attack, 152)
        
        # Verify Current HP is reset to Max HP (207)
        print(f"Scaled Current HP: {scaled_pokemon.current_hp} (Expected 207)")
        self.assertEqual(scaled_pokemon.current_hp, 207)
        
        # Verify Moves Reset (Should take last 4: 11, 12, 13, 14)
        print(f"Scaled Moves: {[scaled_pokemon.moves.move1_id, scaled_pokemon.moves.move2_id, scaled_pokemon.moves.move3_id, scaled_pokemon.moves.move4_id]}")
        self.assertEqual(scaled_pokemon.moves.move1_id, 11)
        self.assertEqual(scaled_pokemon.moves.move4_id, 14)

    def test_start_pvp_battle(self):
        print("Testing start_pvp_battle...")
        attacker_id = "attacker"
        defender_id = "defender"

        # Mock Teams
        self.team_repo.get_user_team.side_effect = lambda uid: MagicMock(team_pokemon_ids=[1]) if uid in [attacker_id, defender_id] else None
        
        # Mock Pokemon Info
        species = MagicMock()
        species.base_stats = {"base_hp": 100, "base_attack": 100, "base_defense": 100, "base_sp_attack": 100, "base_sp_defense": 100, "base_speed": 100}
        self.pokemon_repo.get_pokemon_by_id.return_value = species
        
        self.user_pokemon_repo.get_user_pokemon_by_id.return_value = UserPokemonInfo(
            id=1, species_id=1, name="TestMon", level=100, exp=0, gender="M", nature_id=0,
            stats=PokemonStats(300, 300, 300, 300, 300, 300), 
            ivs=PokemonIVs(31,31,31,31,31,31), 
            evs=PokemonEVs(252,252,252,252,252,252), 
            moves=PokemonMoves(1,2,3,4),
            current_hp=0  # Simulate fainted Pokemon to ensure it's revived in PvP context
        )
        
        # Mock _preload_moves
        self.service._preload_moves = MagicMock(return_value=[])

        # Mock _run_team_battle
        # Returns: res_str, logs, wild_hp, user_hp, user_contexts
        mock_user_ctx = MagicMock()
        mock_user_ctx.pokemon = MagicMock() # Final user pokemon info
        self.service._run_team_battle = MagicMock(return_value=("success", [], 0, 0, [mock_user_ctx]))
        
        # Mock save_battle_log
        self.battle_repo.save_battle_log.return_value = 123

        # Execute
        result = self.service.start_pvp_battle(attacker_id, defender_id)
        
        # Verify
        self.assertTrue(result.success)
        self.assertEqual(result.data.log_id, 123)
        self.assertTrue(result.data.is_trainer_battle)
        # Verify win_rates and exp_details are present
        self.assertIsNotNone(result.data.win_rates)
        self.assertIsNotNone(result.data.exp_details)
        
        # Verify _run_team_battle called with correct args
        args, kwargs = self.service._run_team_battle.call_args
        self.assertFalse(kwargs['update_persistence']) # Must be False
        self.assertIsNotNone(kwargs['user_contexts']) # Must optionally pass user_contexts


if __name__ == "__main__":
    unittest.main()
