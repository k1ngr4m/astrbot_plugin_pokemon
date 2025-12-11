"""Test the stat change functionality"""

from core.services.stat_modifier_service import StatModifierService, StatID
from core.models.pokemon_models import PokemonStats


def test_stat_changes():
    """Test the stat change functionality"""
    service = StatModifierService()

    # Test base stats
    base_stats = PokemonStats(
        hp=100,
        attack=80,
        defense=70,
        sp_attack=90,
        sp_defense=85,
        speed=100
    )

    print("=== Testing Stat Modifier Service ===")
    print(f"Base stats: {base_stats}")

    # Test multipliers
    print("\n=== Testing Multipliers ===")
    for level in [-6, -3, -1, 0, 1, 3, 6]:
        multiplier = service.get_stat_multiplier(level)
        print(f"Level {level}: multiplier = {multiplier:.3f}")

    # Test stat value calculation
    print("\n=== Testing Modified Stat Values ===")
    test_stat = 100
    for level in [-2, -1, 0, 1, 2]:
        modified_value = service.get_modified_stat_value(test_stat, level)
        print(f"Base {test_stat} + Level {level} = {modified_value}")

    # Test applying stat changes
    print("\n=== Testing Stat Changes Application ===")
    stat_changes = [
        {'stat_id': StatID.ATTACK.value, 'change': 2},  # Attack +2
        {'stat_id': StatID.DEFENSE.value, 'change': -1},  # Defense -1
        {'stat_id': StatID.SPEED.value, 'change': 1}  # Speed +1
    ]

    initial_levels = {StatID.ATTACK.value: 0, StatID.DEFENSE.value: 0, StatID.SPEED.value: 0}
    print(f"Initial levels: {initial_levels}")
    print(f"Stat changes to apply: {stat_changes}")

    modified_stats, new_levels = service.apply_stat_changes(base_stats, stat_changes, initial_levels)
    print(f"Modified stats: {modified_stats}")
    print(f"New levels: {new_levels}")

    # Test with existing levels
    print("\n=== Testing with Existing Levels ===")
    existing_levels = {StatID.ATTACK.value: 1, StatID.DEFENSE.value: -1, StatID.SPEED.value: 0}
    print(f"Existing levels: {existing_levels}")

    modified_stats2, new_levels2 = service.apply_stat_changes(base_stats, stat_changes, existing_levels)
    print(f"Modified stats with existing levels: {modified_stats2}")
    print(f"New levels after changes: {new_levels2}")

    print("\n=== All tests completed successfully! ===")


if __name__ == "__main__":
    test_stat_changes()