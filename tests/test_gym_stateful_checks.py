import sys
import unittest
from unittest.mock import MagicMock, patch
import math

# Mock astrbot
mock_astrbot = MagicMock()
sys.modules['astrbot'] = mock_astrbot
sys.modules['astrbot.api'] = mock_astrbot
sys.modules['astrbot.core'] = mock_astrbot
sys.modules['astrbot.api.logger'] = mock_astrbot
sys.modules['deprecated'] = MagicMock()
sys.modules['pandas'] = MagicMock()

# Add plugin root
plugin_root = "/Users/linyiming/Projects/PycharmProjects/astrbot/AstrBot/data/plugins/astrbot_plugin_pokemon"
sys.path.append(plugin_root)

from astrbot_plugin_pokemon.core.services.world.adventure_service import AdventureService
from astrbot_plugin_pokemon.core.models.adventure_models import GymInfo, UserGymState, BattleResult
from astrbot_plugin_pokemon.core.models.common_models import BaseResult
from astrbot_plugin_pokemon.core.models.pokemon_models import PokemonStats, PokemonIVs, PokemonEVs

class TestGymStateful(unittest.TestCase):
    def setUp(self):
        self.mock_adventure_repo = MagicMock()
        self.mock_user_repo = MagicMock()
        self.mock_trainer_service = MagicMock()
        self.mock_team_repo = MagicMock()
        self.mock_user_pokemon_repo = MagicMock()
        self.mock_user_item_repo = MagicMock()
        self.mock_item_repo = MagicMock()
        
        self.service = AdventureService(
            adventure_repo=self.mock_adventure_repo,
            user_repo=self.mock_user_repo,
            pokemon_repo=MagicMock(),
            team_repo=self.mock_team_repo,
            pokemon_service=MagicMock(),
            user_pokemon_repo=self.mock_user_pokemon_repo,
            battle_repo=MagicMock(),
            user_item_repo=self.mock_user_item_repo,
            item_repo=self.mock_item_repo,
            move_repo=MagicMock(),
            pokemon_ability_repo=MagicMock(),
            exp_service=MagicMock(),
            config={}
        )
        self.service.set_trainer_service(self.mock_trainer_service)

        # Simulate State persistence
        self.stored_state = None
        self.mock_adventure_repo.get_gym_state.side_effect = lambda uid: self.stored_state
        self.mock_adventure_repo.save_gym_state.side_effect = self._save_state
        self.mock_adventure_repo.delete_gym_state.side_effect = self._delete_state

        # Mock User
        user_mock = MagicMock()
        user_mock.max_unlocked_location_id = 99
        self.mock_user_repo.get_user_by_id.return_value = user_mock

        # Mock Team
        self.mock_team_repo.get_user_team.return_value = MagicMock(team_pokemon_ids=[1])
        self.mock_user_pokemon_repo.get_user_pokemon_by_id.return_value = MagicMock(current_hp=100)

        # Mock Gym
        self.gym = GymInfo(
            id=1, location_id=1, name="Gym 1", description="Test Gym",
            elite_trainer_ids=[101, 102], boss_trainer_id=201, # 3 battles total
            required_level=10, unlock_location_id=2, reward_item_id=999
        )
        self.mock_adventure_repo.get_gym_by_location.return_value = self.gym

    def _save_state(self, state):
        self.stored_state = state

    def _delete_state(self, uid):
        self.stored_state = None

    @patch.object(AdventureService, 'start_trainer_battle')
    def test_challenge_new_gym(self, mock_battle):
        # Setup: Win battle
        mock_battle.return_value = BaseResult(success=True, message="Win", data=MagicMock(result="success"))
        
        # Mock Trainer
        mock_trainer = MagicMock()
        mock_trainer.trainer.name = "Elite 1"
        self.mock_trainer_service.get_trainer_with_pokemon.return_value = mock_trainer

        # Run
        res = self.service.challenge_gym("u1", 1)

        # Verify
        self.assertTrue(res.success)
        self.assertIn("击败了", res.message)
        self.assertIn("可以使用 /背包", res.message) # check stateful message
        
        # Check State
        self.assertIsNotNone(self.stored_state)
        self.assertEqual(self.stored_state.current_stage, 1) # Should advance to 1
        self.assertTrue(self.stored_state.is_active)
        
        # Call start_battle once
        mock_battle.assert_called_once()

    @patch.object(AdventureService, 'start_trainer_battle')
    def test_challenge_resume_gym(self, mock_battle):
        # Setup State: Stage 1 (Elite 2)
        self.stored_state = UserGymState(user_id="u1", gym_id=1, current_stage=1, is_active=True, last_updated=0)
        
        # Setup: Win
        mock_battle.return_value = BaseResult(success=True, message="Win", data=MagicMock(result="success"))
        
        # Run
        res = self.service.challenge_gym("u1", 1)
        
        # Verify
        self.assertTrue(res.success)
        # Should now be stage 2
        self.assertEqual(self.stored_state.current_stage, 2)
        # Should beat Elite 2 (index 1)
        self.mock_trainer_service.get_trainer_with_pokemon.assert_called_with(102)

    @patch.object(AdventureService, 'start_trainer_battle')
    def test_challenge_boss_victory(self, mock_battle):
        # Setup State: Stage 2 (Boss)
        self.stored_state = UserGymState(user_id="u1", gym_id=1, current_stage=2, is_active=True, last_updated=0)
        
        # Setup: Win
        mock_battle.return_value = BaseResult(success=True, message="Win", data=MagicMock(result="success"))
        
        # Mock Boss Trainer with Pokemon to check Buffs
        mock_trainer = MagicMock()
        mock_trainer.trainer.name = "Boss"
        p1 = MagicMock()
        p1.level = 50
        p1.base_stats = PokemonStats(100, 100, 100, 100, 100, 100)
        p1.stats = PokemonStats(0,0,0,0,0,0) # Init stats
        p1.ivs = PokemonIVs(0,0,0,0,0,0)
        mock_trainer.pokemon_list = [p1]
        self.mock_trainer_service.get_trainer_with_pokemon.return_value = mock_trainer
        
        # Mock Badge check
        self.mock_adventure_repo.has_badge.return_value = False
        
        # Run
        res = self.service.challenge_gym("u1", 1)
        
        # Verify Success
        self.assertTrue(res.success)
        self.assertIn("通关", res.message)
        
        # Check State Deleted
        self.assertIsNone(self.stored_state)
        
        # Check Verify Buffs
        # IVs should be 31
        self.assertEqual(p1.ivs.hp_iv, 31)
        # EVs should be 20
        self.assertEqual(p1.evs.attack_ev, 20)
        # Stats recalculation logic check (just check one stat changed)
        # Calc for HP: ((2*100 + 31 + 5)*50)/100 + 50 + 10 = ((236)*50)/100 + 60 = 118 + 60 = 178
        self.assertEqual(p1.stats.hp, 178) 

        # Check Badge and Rewards
        self.mock_adventure_repo.add_user_badge.assert_called_with("u1", 1, 1)
        self.mock_user_item_repo.add_user_item.assert_called_with("u1", 999, 1)

    def test_give_up_gym(self):
        self.stored_state = UserGymState(user_id="u1", gym_id=1, current_stage=1, is_active=True, last_updated=0)
        res = self.service.give_up_gym("u1")
        self.assertTrue(res.success)
        self.assertIsNone(self.stored_state)

if __name__ == '__main__':
    unittest.main()
