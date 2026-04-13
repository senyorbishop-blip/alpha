"""Tests for subclass_lists population in OPEN_5E_SPELLS and resolver integration."""
from __future__ import annotations

import pytest

from server.rules_content import OPEN_5E_SPELLS
from server.character.resolver import resolve_character_runtime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_spell(spell_id: str) -> dict:
    for s in OPEN_5E_SPELLS:
        if s.get("id") == spell_id:
            return s
    raise KeyError(f"Spell not found: {spell_id}")


def _wizard_spells() -> list[dict]:
    return [s for s in OPEN_5E_SPELLS if "Wizard" in (s.get("class_lists") or [])]


# ---------------------------------------------------------------------------
# subclass_lists population tests
# ---------------------------------------------------------------------------

class TestSubclassSpellListsPopulation:
    def test_all_wizard_spells_have_eldritch_knight(self):
        """Every spell with Wizard in class_lists must include eldritch-knight."""
        for spell in _wizard_spells():
            assert "eldritch-knight" in spell["subclass_lists"], (
                f"{spell['id']} (school={spell.get('school')}) missing eldritch-knight"
            )

    def test_all_wizard_spells_have_arcane_trickster(self):
        """Every spell with Wizard in class_lists must include arcane-trickster."""
        for spell in _wizard_spells():
            assert "arcane-trickster" in spell["subclass_lists"], (
                f"{spell['id']} (school={spell.get('school')}) missing arcane-trickster"
            )

    def test_no_duplicate_subclass_ids(self):
        """subclass_lists must not contain duplicate entries for any spell."""
        for spell in OPEN_5E_SPELLS:
            subs = spell.get("subclass_lists") or []
            assert len(subs) == len(set(subs)), (
                f"{spell['id']} has duplicate subclass_lists entries: {subs}"
            )

    def test_non_wizard_spell_has_no_subclass_entries(self):
        """Spells that do not list Wizard must have empty subclass_lists."""
        for spell in OPEN_5E_SPELLS:
            if "Wizard" not in (spell.get("class_lists") or []):
                assert spell.get("subclass_lists") == [], (
                    f"{spell['id']} (class_lists={spell.get('class_lists')}) "
                    f"should have empty subclass_lists, got {spell.get('subclass_lists')}"
                )

    # --- Spot-checks for specific schools and spells ---

    def test_evocation_wizard_spell_has_eldritch_knight(self):
        """Fire Bolt is Evocation + Wizard → eldritch-knight must be present."""
        spell = _get_spell("spell_fire_bolt")
        assert "eldritch-knight" in spell["subclass_lists"]

    def test_evocation_wizard_spell_has_arcane_trickster(self):
        """Fire Bolt is Evocation + Wizard → arcane-trickster must be present (lvl-8 rule)."""
        spell = _get_spell("spell_fire_bolt")
        assert "arcane-trickster" in spell["subclass_lists"]

    def test_abjuration_wizard_spell_has_eldritch_knight(self):
        """Shield is Abjuration + Wizard → eldritch-knight must be present."""
        spell = _get_spell("spell_shield")
        assert "eldritch-knight" in spell["subclass_lists"]

    def test_enchantment_wizard_spell_has_arcane_trickster(self):
        """Hold Person is Enchantment + Wizard → arcane-trickster must be present."""
        spell = _get_spell("spell_hold_person")
        assert "arcane-trickster" in spell["subclass_lists"]

    def test_illusion_wizard_spell_has_arcane_trickster(self):
        """Minor Illusion is Illusion + Wizard → arcane-trickster must be present."""
        spell = _get_spell("spell_minor_illusion")
        assert "arcane-trickster" in spell["subclass_lists"]

    def test_conjuration_wizard_spell_has_both_via_level8_rule(self):
        """Misty Step is Conjuration + Wizard → both subclasses via level-8 rule."""
        spell = _get_spell("spell_misty_step")
        assert "eldritch-knight" in spell["subclass_lists"]
        assert "arcane-trickster" in spell["subclass_lists"]

    def test_cleric_only_evocation_spell_has_no_subclass(self):
        """Sacred Flame is Evocation but Cleric-only → no subclass IDs."""
        spell = _get_spell("spell_sacred_flame")
        assert spell["subclass_lists"] == []

    def test_total_wizard_spell_count_matches_subclass_spell_count(self):
        """The count of spells with eldritch-knight should equal Wizard spell count."""
        wizard_count = len(_wizard_spells())
        ek_count = sum(1 for s in OPEN_5E_SPELLS if "eldritch-knight" in s.get("subclass_lists", []))
        at_count = sum(1 for s in OPEN_5E_SPELLS if "arcane-trickster" in s.get("subclass_lists", []))
        assert ek_count == wizard_count
        assert at_count == wizard_count


# ---------------------------------------------------------------------------
# Resolver integration tests
# ---------------------------------------------------------------------------

class TestResolverSubclassSpellAccess:
    def _ek_result(self, level: int = 3) -> dict:
        return resolve_character_runtime({
            "classes": [{"classId": "fighter", "level": level, "subclassId": "eldritch-knight"}],
            "abilities": {"scores": {"str": 16, "dex": 14, "con": 14, "int": 13, "wis": 10, "cha": 8}},
        })

    def _at_result(self, level: int = 3) -> dict:
        return resolve_character_runtime({
            "classes": [{"classId": "rogue", "level": level, "subclassId": "arcane-trickster"}],
            "abilities": {"scores": {"str": 10, "dex": 16, "con": 12, "int": 14, "wis": 10, "cha": 10}},
        })

    def test_eldritch_knight_gets_available_by_subclass_key(self):
        runtime = self._ek_result()["runtime"]
        assert "availableBySubclass" in runtime["spellAccess"]

    def test_eldritch_knight_available_spells_not_empty(self):
        runtime = self._ek_result()["runtime"]
        assert len(runtime["spellAccess"]["availableBySubclass"]) > 0

    def test_eldritch_knight_has_evocation_wizard_spell(self):
        runtime = self._ek_result()["runtime"]
        assert "spell_fire_bolt" in runtime["spellAccess"]["availableBySubclass"]

    def test_eldritch_knight_has_abjuration_wizard_spell(self):
        runtime = self._ek_result()["runtime"]
        assert "spell_shield" in runtime["spellAccess"]["availableBySubclass"]

    def test_eldritch_knight_has_conjuration_wizard_spell_via_level8_rule(self):
        runtime = self._ek_result()["runtime"]
        assert "spell_misty_step" in runtime["spellAccess"]["availableBySubclass"]

    def test_eldritch_knight_available_spells_equals_all_wizard_spells(self):
        """EK should have access to all Wizard spells (level-8 rule covers all schools)."""
        runtime = self._ek_result()["runtime"]
        wizard_ids = {s["id"] for s in _wizard_spells()}
        available_set = set(runtime["spellAccess"]["availableBySubclass"])
        assert wizard_ids == available_set

    def test_arcane_trickster_gets_available_by_subclass_key(self):
        runtime = self._at_result()["runtime"]
        assert "availableBySubclass" in runtime["spellAccess"]

    def test_arcane_trickster_has_illusion_wizard_spell(self):
        runtime = self._at_result()["runtime"]
        assert "spell_minor_illusion" in runtime["spellAccess"]["availableBySubclass"]

    def test_arcane_trickster_has_enchantment_wizard_spell(self):
        runtime = self._at_result()["runtime"]
        assert "spell_hold_person" in runtime["spellAccess"]["availableBySubclass"]

    def test_arcane_trickster_has_conjuration_wizard_spell_via_level8_rule(self):
        runtime = self._at_result()["runtime"]
        assert "spell_misty_step" in runtime["spellAccess"]["availableBySubclass"]

    def test_arcane_trickster_available_spells_equals_all_wizard_spells(self):
        """AT should have access to all Wizard spells (level-8 rule covers all schools)."""
        runtime = self._at_result()["runtime"]
        wizard_ids = {s["id"] for s in _wizard_spells()}
        available_set = set(runtime["spellAccess"]["availableBySubclass"])
        assert wizard_ids == available_set

    def test_fighter_without_subclass_has_empty_available_by_subclass(self):
        result = resolve_character_runtime({
            "classes": [{"classId": "fighter", "level": 3}],
        })
        runtime = result["runtime"]
        assert runtime["spellAccess"]["availableBySubclass"] == []

    def test_wizard_character_has_empty_available_by_subclass_without_subclass(self):
        result = resolve_character_runtime({
            "classes": [{"classId": "wizard", "level": 5}],
        })
        runtime = result["runtime"]
        assert runtime["spellAccess"]["availableBySubclass"] == []

    def test_eldritch_knight_available_spells_same_at_all_levels(self):
        """Spell access list should be identical regardless of character level.

        The implementation does not filter by level — all Wizard spells are
        pre-populated in subclass_lists for both subclasses, so a level-3 and
        a level-15 EK see the same available pool.
        """
        available_3 = set(self._ek_result(level=3)["runtime"]["spellAccess"]["availableBySubclass"])
        available_8 = set(self._ek_result(level=8)["runtime"]["spellAccess"]["availableBySubclass"])
        available_15 = set(self._ek_result(level=15)["runtime"]["spellAccess"]["availableBySubclass"])
        assert available_3 == available_8 == available_15

    def test_arcane_trickster_available_spells_same_at_all_levels(self):
        """Spell access list should be identical regardless of character level."""
        available_3 = set(self._at_result(level=3)["runtime"]["spellAccess"]["availableBySubclass"])
        available_8 = set(self._at_result(level=8)["runtime"]["spellAccess"]["availableBySubclass"])
        available_15 = set(self._at_result(level=15)["runtime"]["spellAccess"]["availableBySubclass"])
        assert available_3 == available_8 == available_15

    def test_default_runtime_includes_available_by_subclass_key(self):
        """default_runtime() must include availableBySubclass for schema consistency."""
        from server.character.schema import default_runtime
        rt = default_runtime()
        assert "availableBySubclass" in rt["spellAccess"]
        assert rt["spellAccess"]["availableBySubclass"] == []
