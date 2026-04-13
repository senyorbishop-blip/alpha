from pathlib import Path


def test_known_issues_doc_has_new_systems_readiness_snapshot():
    src = Path("docs/known-issues-founder-beta.md").read_text(encoding="utf-8")
    assert "## New systems: founder-beta readiness snapshot" in src
    for label in [
        "Living world state",
        "Campaign hub",
        "Faction reputation",
        "Guild rank",
        "Big-screen mode",
        "Assistant DM permissions",
        "Split-party support",
        "Prep packs",
        "Cinematic overlays",
    ]:
        assert label in src


def test_founder_beta_checklists_include_new_systems_hardening_gate():
    master = Path("docs/founder-beta/master-checklist.md").read_text(encoding="utf-8")
    release = Path("docs/founder-beta/release-go-no-go-checklist.md").read_text(encoding="utf-8")

    assert "Assistant DM permissions verified" in master
    assert "Split-party assign/context flows verified" in master
    assert "Faction reputation + guild-rank gated quest behavior smoke-tested" in master
    assert "Prep-pack import checked" in master
    assert "New-system hardening pass completed" in release


def test_runtime_contracts_for_new_systems_stay_wired_in_live_paths():
    handlers = Path("server/handlers/__init__.py").read_text(encoding="utf-8")
    play = Path("client/templates/play.html").read_text(encoding="utf-8")

    # Server dispatch contracts
    assert '"assistant_dm_permissions_set": handle_assistant_dm_permissions_set' in handlers
    assert '"split_party_assign": handle_split_party_assign' in handlers
    assert '"split_party_set_context": handle_split_party_set_context' in handlers
    assert '"prep_pack_library_list": handle_prep_pack_library_list' in handlers
    assert '"prep_pack_import": handle_prep_pack_import' in handlers

    # Live client contracts in play.html
    assert 'id="player-display-toggle-btn"' in play
    assert 'toggleBigScreenDisplayMode()' in play
    assert 'sendWS({ type: \'assistant_dm_permissions_set\'' in play
    assert 'sendWS({ type: \'prep_pack_library_list\'' in play
    assert 'sendWS({ type: \'prep_pack_import\'' in play
    assert '#session-event-overlay[data-cinematic="true"]' in play

    # Split-party coverage currently lives in backend and test contracts.
    split_party_tests = Path("tests/test_split_party.py").read_text(encoding="utf-8")
    assert "test_split_party_" in split_party_tests
