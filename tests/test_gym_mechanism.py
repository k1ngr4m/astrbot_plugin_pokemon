import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock astrbot and other dependencies BEFORE importing service
mock_astrbot = MagicMock()
# Mock entire package structure
sys.modules['astrbot'] = mock_astrbot
sys.modules['astrbot.api'] = mock_astrbot
sys.modules['astrbot.core'] = mock_astrbot # Added this
sys.modules['astrbot.api.logger'] = mock_astrbot
sys.modules['deprecated'] = MagicMock()
sys.modules['pandas'] = MagicMock() # Mock pandas

# Add plugin root to sys.path
plugin_root = "/Users/linyiming/Projects/PycharmProjects/astrbot/AstrBot/data/plugins/astrbot_plugin_pokemon"
sys.path.append(plugin_root)

from astrbot_plugin_pokemon.core.services.world.adventure_service import AdventureService
from astrbot_plugin_pokemon.core.models.adventure_models import GymInfo, LocationInfo
from astrbot_plugin_pokemon.core.models.common_models import BaseResult

class TestGymSystem(unittest.TestCase):
    def setUp(self):
        self.mock_adventure_repo = MagicMock()
        self.mock_user_repo = MagicMock()
        self.mock_trainer_service = MagicMock()
        self.service = AdventureService(
            adventure_repo=self.mock_adventure_repo,
            user_repo=self.mock_user_repo,
            pokemon_repo=MagicMock(),
            team_repo=MagicMock(),
            pokemon_service=MagicMock(),
            user_pokemon_repo=MagicMock(),
            battle_repo=MagicMock(),
            user_item_repo=MagicMock(),
            item_repo=MagicMock(),
            move_repo=MagicMock(),
            pokemon_ability_repo=MagicMock(),
            exp_service=MagicMock(),
            config={}
        )
        self.service.set_trainer_service(self.mock_trainer_service)

    def test_get_all_locations_filtering(self):
        # Setup locations
        loc1 = LocationInfo(id=1, name="Town", min_level=1, max_level=5, description="")
        loc2 = LocationInfo(id=2, name="Forest", min_level=5, max_level=10, description="")
        self.mock_adventure_repo.get_all_locations.return_value = [loc1, loc2]

        # Test with user max unlocked = 1
        user_mock = MagicMock()
        user_mock.max_unlocked_location_id = 1
        self.mock_user_repo.get_user_by_id.return_value = user_mock

        res = self.service.get_all_locations(user_id="test_user")
        self.assertTrue(res.success)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0].id, 1)

        # Test with user max unlocked = 2
        user_mock.max_unlocked_location_id = 2
        res = self.service.get_all_locations(user_id="test_user")
        self.assertEqual(len(res.data), 2)
    
    @patch.object(AdventureService, 'start_trainer_battle')
    def test_challenge_gym_success(self, mock_battle):
        # Setup Gym
        gym = GymInfo(
            id=1, location_id=1, name="Gym 1", description="Test Gym",
            elite_trainer_ids=[101, 102], boss_trainer_id=201,
            required_level=10, unlock_location_id=2, reward_item_id=999
        )
        self.mock_adventure_repo.get_gym_by_location.return_value = gym
        
        # Setup User
        user_mock = MagicMock()
        user_mock.max_unlocked_location_id = 1
        self.mock_user_repo.get_user_by_id.return_value = user_mock
        
        # Setup Team
        self.service.team_repo.get_user_team.return_value = MagicMock(team_pokemon_ids=[1, 2, 3])
        self.service.user_pokemon_repo.get_user_pokemon_by_id.return_value = MagicMock(current_hp=100) # Alive

        # Mock Trainers
        self.mock_trainer_service.get_trainer_with_pokemon.return_value = MagicMock()

        # Mock Battle Success
        success_result = BaseResult(success=True, message="Success", data=MagicMock(result="success"))
        mock_battle.return_value = success_result

        # Run
        res = self.service.challenge_gym("test_user", 1)
        
        self.assertTrue(res.success)
        self.assertIn("恭喜", res.message)
        
        # Verify calls
        # 2 elites + 1 boss = 3 battles
        self.assertEqual(mock_battle.call_count, 3)
        self.mock_user_repo.update_user_max_location.assert_called_with("test_user", 2)
        self.service.user_item_repo.add_user_item.assert_called_with("test_user", 999, 1)

if __name__ == '__main__':
    unittest.main()
