from pathlib import Path

from server.character.routes import _builder_class_spell_pool, _fallback_highest_unlocked_spell_level


def test_warlock_fallback_unlock_level_reports_leveled_spells():
    pool = _builder_class_spell_pool().get("warlock", set())
    assert pool, "Expected class spell pool metadata for warlock."
    # Warlock must not render as cantrips-only at low levels in the builder.
    assert _fallback_highest_unlocked_spell_level("warlock", 1, pool) >= 1
    assert _fallback_highest_unlocked_spell_level("warlock", 5, pool) >= 2


def test_builder_state_does_not_autoload_persisted_draft_without_opt_in():
    src = Path("client/static/js/character/builder/builder_state.js").read_text(encoding="utf-8")
    assert "loadPersistedDraft: false" in src
    assert "createOpts.loadPersistedDraft ? loadPersistedDraft() : null" in src
