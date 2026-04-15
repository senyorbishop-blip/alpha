import math

from server import encumbrance


def test_carry_capacity_uses_updated_formula_for_scalar_path():
    strength = 10
    expected = math.floor((strength * 15) * 1.25) + 10
    assert encumbrance.get_carry_capacity(strength) == expected


def test_carry_capacity_uses_updated_formula_for_new_and_existing_character_shapes():
    strength = 14
    expected = math.floor((strength * 15) * 1.25) + 10

    newly_created_character = {"abilities": {"scores": {"str": strength}}}
    existing_character = {"abilities": {"str": strength}}

    assert encumbrance.get_carry_capacity(newly_created_character)["carryCapacity"] == expected
    assert encumbrance.get_carry_capacity(existing_character)["carryCapacity"] == expected


def test_over_capacity_threshold_matches_capacity():
    strength = 12
    thresholds = encumbrance.get_encumbrance_thresholds(strength, "medium")
    capacity = encumbrance.get_carry_capacity(strength, "medium")

    assert thresholds[encumbrance.ENC_OVER] == capacity
    assert encumbrance.get_encumbrance_state(strength, "medium", capacity) != encumbrance.ENC_OVER
    assert encumbrance.get_encumbrance_state(strength, "medium", capacity + 0.01) == encumbrance.ENC_OVER
