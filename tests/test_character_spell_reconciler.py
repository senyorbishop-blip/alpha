"""Tests for server/character/spell_reconciler.py.

Covers:
- reconcile_spell_ids with all valid IDs (no DB calls triggered after exact match)
- reconcile_spell_ids logs and keeps unresolvable IDs as-is
- reconcile_spell_ids resolves IDs via normalised-name fallback and logs warning
- reconcile_spell_ids preserves list length (no silent drops)
- reconcile_character_spell_state is a no-op on documents without spellState
- reconcile_character_spell_state mutates both known and prepared lists
- build_profile_upsert_payload calls reconcile_character_spell_state on save
"""
from __future__ import annotations

import logging
import pytest

from server.character.spell_reconciler import (
    reconcile_character_spell_state,
    reconcile_spell_ids,
)
from server.character.service import build_profile_upsert_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spell_lookup(valid_ids: set[str], name_map: dict[str, str] | None = None):
    """Return a (get_spell_by_id, lookup_spell_id_by_normalized_name) pair.

    valid_ids: set of IDs that should return a non-None result from get_spell_by_id.
    name_map:  normalized_name → canonical_id mappings for the fallback lookup.
    """
    name_map = name_map or {}

    def fake_get_spell_by_id(spell_id: str):
        return {"id": spell_id} if spell_id in valid_ids else None

    def fake_lookup_by_name(normalized: str):
        return name_map.get(normalized)

    return fake_get_spell_by_id, fake_lookup_by_name


# ---------------------------------------------------------------------------
# reconcile_spell_ids tests
# ---------------------------------------------------------------------------

class TestReconcileSpellIds:
    def test_empty_list_returns_empty(self, monkeypatch):
        monkeypatch.setattr(
            "server.character.spell_reconciler.get_spell_by_id",
            lambda _: None,
        )
        assert reconcile_spell_ids([]) == []

    def test_all_valid_ids_passed_through_unchanged(self, monkeypatch):
        fake_get, fake_lookup = _make_spell_lookup({"fireball", "magic_missile"})
        monkeypatch.setattr("server.character.spell_reconciler.get_spell_by_id", fake_get)
        monkeypatch.setattr(
            "server.character.spell_reconciler.lookup_spell_id_by_normalized_name",
            fake_lookup,
        )

        result = reconcile_spell_ids(["fireball", "magic_missile"])
        assert result == ["fireball", "magic_missile"]

    def test_unresolvable_id_kept_as_is_and_logged(self, monkeypatch, caplog):
        monkeypatch.setattr(
            "server.character.spell_reconciler.get_spell_by_id", lambda _: None
        )
        monkeypatch.setattr(
            "server.character.spell_reconciler.lookup_spell_id_by_normalized_name",
            lambda _: None,
        )

        with caplog.at_level(logging.WARNING, logger="server.character.spell_reconciler"):
            result = reconcile_spell_ids(["unknown-spell-xyz"], list_name="known")

        assert result == ["unknown-spell-xyz"]
        assert any("unknown-spell-xyz" in r.message for r in caplog.records)
        assert any("keeping as-is" in r.message for r in caplog.records)

    def test_name_fallback_replaces_id_and_logs_warning(self, monkeypatch, caplog):
        # "Fireball" (display name) isn't a valid slug but normalises to "fireball"
        # which maps to the canonical id "fireball_srd".
        fake_get, fake_lookup = _make_spell_lookup(
            set(), name_map={"fireball": "fireball_srd"}
        )
        monkeypatch.setattr("server.character.spell_reconciler.get_spell_by_id", fake_get)
        monkeypatch.setattr(
            "server.character.spell_reconciler.lookup_spell_id_by_normalized_name",
            fake_lookup,
        )

        with caplog.at_level(logging.WARNING, logger="server.character.spell_reconciler"):
            result = reconcile_spell_ids(["Fireball"], list_name="known")

        assert result == ["fireball_srd"]
        assert any("fireball_srd" in r.message for r in caplog.records)

    def test_list_length_preserved_for_mix_of_valid_and_unresolvable(self, monkeypatch):
        fake_get, fake_lookup = _make_spell_lookup({"fireball"})
        monkeypatch.setattr("server.character.spell_reconciler.get_spell_by_id", fake_get)
        monkeypatch.setattr(
            "server.character.spell_reconciler.lookup_spell_id_by_normalized_name",
            fake_lookup,
        )

        result = reconcile_spell_ids(["fireball", "does_not_exist"])
        assert len(result) == 2
        assert result[0] == "fireball"
        assert result[1] == "does_not_exist"

    def test_blank_ids_are_stripped_from_output(self, monkeypatch):
        monkeypatch.setattr(
            "server.character.spell_reconciler.get_spell_by_id", lambda _: None
        )
        monkeypatch.setattr(
            "server.character.spell_reconciler.lookup_spell_id_by_normalized_name",
            lambda _: None,
        )
        result = reconcile_spell_ids(["", "  ", "fireball"])
        # blank entries are skipped; "fireball" is kept as-is (unresolvable in stub)
        assert "" not in result
        assert "fireball" in result

    def test_list_name_appears_in_log_message(self, monkeypatch, caplog):
        monkeypatch.setattr(
            "server.character.spell_reconciler.get_spell_by_id", lambda _: None
        )
        monkeypatch.setattr(
            "server.character.spell_reconciler.lookup_spell_id_by_normalized_name",
            lambda _: None,
        )

        with caplog.at_level(logging.WARNING, logger="server.character.spell_reconciler"):
            reconcile_spell_ids(["bad-id"], list_name="prepared")

        assert any("prepared" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# reconcile_character_spell_state tests
# ---------------------------------------------------------------------------

class TestReconcileCharacterSpellState:
    def test_no_op_when_spellstate_absent(self, monkeypatch):
        monkeypatch.setattr(
            "server.character.spell_reconciler.get_spell_by_id", lambda _: None
        )
        doc = {"identity": {"name": "Test"}}
        result = reconcile_character_spell_state(doc)
        # Document unchanged — no spellState key present
        assert "spellState" not in result

    def test_no_op_when_document_not_a_dict(self, monkeypatch):
        monkeypatch.setattr(
            "server.character.spell_reconciler.get_spell_by_id", lambda _: None
        )
        assert reconcile_character_spell_state(None) is None
        assert reconcile_character_spell_state("not-a-dict") == "not-a-dict"

    def test_reconciles_known_and_prepared_lists(self, monkeypatch):
        fake_get, fake_lookup = _make_spell_lookup(
            {"fireball"}, name_map={"magicmissile": "magic_missile"}
        )
        monkeypatch.setattr("server.character.spell_reconciler.get_spell_by_id", fake_get)
        monkeypatch.setattr(
            "server.character.spell_reconciler.lookup_spell_id_by_normalized_name",
            fake_lookup,
        )

        doc = {
            "spellState": {
                "known": ["fireball", "Magic Missile"],
                "prepared": ["Magic Missile"],
            }
        }
        result = reconcile_character_spell_state(doc)
        assert result["spellState"]["known"] == ["fireball", "magic_missile"]
        assert result["spellState"]["prepared"] == ["magic_missile"]

    def test_leaves_non_list_known_untouched(self, monkeypatch):
        monkeypatch.setattr(
            "server.character.spell_reconciler.get_spell_by_id", lambda _: None
        )
        doc = {"spellState": {"known": None, "prepared": []}}
        result = reconcile_character_spell_state(doc)
        # known is None, not a list — should not be replaced
        assert result["spellState"]["known"] is None


# ---------------------------------------------------------------------------
# Integration: build_profile_upsert_payload calls reconciler
# ---------------------------------------------------------------------------

class TestBuildProfileUpsertPayloadCallsReconciler:
    """Verify the reconciler is invoked when build_profile_upsert_payload is called."""

    def test_reconciler_called_during_upsert(self, monkeypatch):
        called_with: list[dict] = []

        def fake_reconcile(document):
            called_with.append(document)
            return document

        monkeypatch.setattr(
            "server.character.service.reconcile_character_spell_state",
            fake_reconcile,
        )

        doc = {
            "identity": {"name": "Zara"},
            "spellState": {"known": ["fireball"], "prepared": []},
        }
        build_profile_upsert_payload(doc)

        assert len(called_with) == 1
        assert called_with[0] is doc

    def test_non_dict_document_does_not_call_reconciler(self, monkeypatch):
        called = []

        def fake_reconcile(document):
            called.append(document)
            return document

        monkeypatch.setattr(
            "server.character.service.reconcile_character_spell_state",
            fake_reconcile,
        )
        # Non-dict should skip the reconciler guard
        build_profile_upsert_payload(None)
        assert called == []
