"""Tests for PR 5: active-profile/Quick Actions reconnect hardening.

Covers:
  - authoritative_snapshot's character/spells/inventory hydration_status for
    an active profile that is present, missing, or unselected.
  - the JWT-authenticated reconnect-safe fallbacks in
    resolve_owned_profile_or_403 (active-session-profile / token-linked
    profile) that let a restored session keep granting a user access to
    their own active profile without opening up arbitrary profile_id access.
  - the inventory/equipment summary block on the snapshot.
"""
from pathlib import Path

import server.character.routes as character_routes
from server.character.routes import resolve_owned_profile_or_403
from server.session import Session, Token, User

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _profile(profile_id: str, name: str = "") -> dict:
    return {
        "id": profile_id,
        "name": name or profile_id,
        "nativeCharacter": {
            "identity": {"name": name or profile_id, "className": "Sorcerer"},
            "classes": [{"classId": "sorcerer", "level": 5}],
            "abilities": {},
            "spellState": {"known": ["fireball", "fire-bolt"], "prepared": ["fireball"], "slots": {}, "rituals": []},
        },
    }


def _build_session(*, active_profile_id: str = "f-bishop") -> Session:
    session = Session(id="s-active-profile")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="player-1", name="Bishop", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.char_profiles = {"bishop": [_profile("f-bishop", "Bishop")]}
    if active_profile_id:
        session.active_char_profiles = {player.id: active_profile_id}
    return session


def test_authoritative_snapshot_reports_ok_hydration_for_active_profile():
    session = _build_session()
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    payload = msg["payload"]

    assert payload["character"]["active_profile_id"] == "f-bishop"
    assert payload["character"]["hydration_status"] == "ok"
    assert payload["character"]["summary"]["name"] == "Bishop"
    assert payload["spells"]["hydration_status"] == "ok"
    assert payload["spells"]["summary"]["known_count"] == 2


def test_authoritative_snapshot_reports_missing_profile_when_no_active_profile_selected():
    session = _build_session(active_profile_id="")
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    payload = msg["payload"]

    assert payload["character"]["active_profile_id"] == ""
    assert payload["character"]["hydration_status"] == "missing_profile"
    assert payload["spells"]["hydration_status"] == "missing_profile"


def test_authoritative_snapshot_reports_missing_runtime_when_active_profile_row_is_gone():
    # Active profile id is set, but the profile row itself was removed/never
    # restored (e.g. partial DB restore) — this must be distinguishable from
    # "no profile selected" so the client can show a different error.
    session = _build_session(active_profile_id="ghost-profile")
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    payload = msg["payload"]

    assert payload["character"]["active_profile_id"] == "ghost-profile"
    assert payload["character"]["hydration_status"] == "missing_runtime"
    assert payload["spells"]["hydration_status"] == "missing_runtime"


def test_authoritative_snapshot_inventory_summary_includes_equipped_items_for_owner():
    session = _build_session()
    session.player_inventories = {
        "bishop": [
            {"id": "i1", "name": "Thunder Mage Quarterstaff +3", "equipped": True, "rarity": "rare"},
            {"id": "i2", "name": "Dagger", "equipped": True, "rarity": "common"},
            {"id": "i3", "name": "Spare Rope", "equipped": False, "rarity": "common"},
        ]
    }
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    inventory = msg["payload"]["inventory"]

    assert inventory["hydration_status"] == "ok"
    assert inventory["summary"]["item_count"] == 3
    assert inventory["summary"]["equipped_count"] == 2
    names = {item["name"] for item in inventory["summary"]["equipped_items"]}
    assert names == {"Thunder Mage Quarterstaff, +3", "Dagger"}


def test_authoritative_snapshot_never_leaks_other_players_inventory_to_a_player():
    session = _build_session()
    session.player_inventories = {
        "bishop": [{"id": "i1", "name": "Bishop's Dagger", "equipped": True}],
        "other player": [{"id": "j1", "name": "Other Player's Secret Ring", "equipped": True}],
    }
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    assert "Other Player's Secret Ring" not in str(msg["payload"]["inventory"])


def _session_for_spell_access() -> Session:
    session = Session(id="S1")
    dm = User(id="dm-1", name="DM", role="dm")
    player_a = User(id="player-a", name="Player A", role="player")
    session.users = {"dm-1": dm, "player-a": player_a}
    session.char_profiles = {"player a": [_profile("profile-a", "Player A")]}
    return session


def test_active_session_profile_fallback_grants_jwt_user_their_own_active_profile(monkeypatch):
    # Simulates the bug report: the owner-key bucket lookup misses (e.g. the
    # JWT account's display name doesn't match the bucket key after a server
    # restart) but the session already restored active_char_profiles for this
    # user pointing at profile-a — that alone should be enough to authorize.
    session = _session_for_spell_access()
    session.char_profiles = {"someone else": [_profile("profile-a", "Player A")]}
    session.active_char_profiles = {"player-a": "profile-a"}
    auth_user = {"id": "player-a", "name": "Player A"}

    profile = resolve_owned_profile_or_403(session, auth_user, "profile-a")
    assert profile["id"] == "profile-a"


def test_active_session_profile_fallback_does_not_grant_other_profiles(monkeypatch):
    session = _session_for_spell_access()
    session.char_profiles = {
        "someone else": [_profile("profile-a", "Player A")],
        "player b": [_profile("profile-b", "Player B")],
    }
    session.active_char_profiles = {"player-a": "profile-a"}
    auth_user = {"id": "player-a", "name": "Player A"}

    try:
        resolve_owned_profile_or_403(session, auth_user, "profile-b")
        assert False, "expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403


def test_token_linked_profile_fallback_grants_jwt_user_their_linked_profile():
    session = _session_for_spell_access()
    session.char_profiles = {"someone else": [_profile("profile-a", "Player A")]}
    session.tokens["tok-a"] = Token(
        id="tok-a", name="Player A", x=0, y=0, width=40, height=40,
        color="#fff", shape="circle", owner_id="player-a", token_type="player",
        profile_id="profile-a",
    )
    auth_user = {"id": "player-a", "name": "Player A"}

    profile = resolve_owned_profile_or_403(session, auth_user, "profile-a")
    assert profile["id"] == "profile-a"


def test_token_linked_profile_fallback_requires_matching_token_owner():
    session = _session_for_spell_access()
    session.char_profiles = {"someone else": [_profile("profile-a", "Player A")]}
    session.tokens["tok-a"] = Token(
        id="tok-a", name="Someone", x=0, y=0, width=40, height=40,
        color="#fff", shape="circle", owner_id="player-b", token_type="player",
        profile_id="profile-a",
    )
    auth_user = {"id": "player-a", "name": "Player A"}

    try:
        resolve_owned_profile_or_403(session, auth_user, "profile-a")
        assert False, "expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403


def test_play_html_loads_auth_js_before_first_runtime_script():
    src = PLAY.read_text(encoding="utf-8")
    auth_idx = src.index('<script src="/static/js/auth.js"></script>')
    diagnostics_idx = src.index('<script src="/static/js/core/diagnostics.js"></script>')
    assert auth_idx < diagnostics_idx


def test_play_html_defines_apply_authoritative_character_state():
    src = PLAY.read_text(encoding="utf-8")
    assert "function applyAuthoritativeCharacterState(payload, source)" in src
    assert "window.applyAuthoritativeCharacterState = applyAuthoritativeCharacterState" in src
    assert "character:quick-actions-refresh" in src


def test_play_html_handle_authoritative_snapshot_invokes_character_apply_path():
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function handleAuthoritativeSnapshot(payload)")
    end = src.index("window.handleAuthoritativeSnapshot = handleAuthoritativeSnapshot;")
    handler = src[start:end]
    assert "applyAuthoritativeCharacterState(" in handler


def test_quick_actions_payload_in_snapshot_has_weapons_spells_item_cards_and_revisions():
    session = _build_session()
    session.character_runtime_revision = 2
    session.spell_manifest_revision = 3
    session.inventory_revision = 4
    session.quick_actions_revision = 5
    session.player_inventories = {
        "bishop": [
            {"id": "dagger-1", "name": "Dagger", "equipped": True, "equipment_kind": "weapon", "damage_dice": "1d4", "damage_type": "piercing"},
            {"id": "staff-1", "name": "Staff of Fire", "equipped": True, "attunement_required": True, "attuned": True, "equipment_kind": "weapon", "damage_dice": "1d6", "damage_type": "bludgeoning", "charges_current": 0, "charges_max": 3, "granted_spells": [{"id": "fireball", "name": "Fireball", "charge_cost": 1, "cast_level": 3}]},
        ]
    }

    quick = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")["payload"]["quick_actions"]

    assert quick["active_profile_id"] == "f-bishop"
    assert quick["character_runtime_revision"] == 2
    assert quick["spell_manifest_revision"] == 3
    assert quick["inventory_revision"] == 4
    assert quick["quick_actions_revision"] == 5
    assert any(a["kind"] == "weapon_attack" and a["name"] == "Dagger" for a in quick["weapon_actions"])
    assert any(a["kind"] == "weapon_damage" and a["damage_formula"] == "1d4" for a in quick["weapon_actions"])
    assert any(a["name"] == "Staff of Fire" for a in quick["weapon_actions"])
    assert any(s["name"] == "Fireball" and s["requires_slot"] is True and s["requires_cast_level_prompt"] is True for s in quick["spell_actions"])
    assert any(card["spell_id"] == "fireball" and card["disabled"] is True for card in quick["item_spell_cards"])
    assert any(d["code"] == "no_charges" for d in quick["diagnostics"])


def test_quick_actions_payload_reports_item_not_equipped_and_not_attuned():
    session = _build_session()
    session.player_inventories = {
        "bishop": [
            {"id": "staff-1", "name": "Staff of Frost", "equipped": False, "attunement_required": True, "attuned": False, "charges_current": 2, "charges_max": 3, "granted_spells": [{"id": "cone-of-cold", "name": "Cone of Cold", "charge_cost": 1}]},
        ]
    }

    quick = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")["payload"]["quick_actions"]
    codes = {d["code"] for d in quick["diagnostics"]}

    assert "item_not_equipped" in codes
    assert "item_not_attuned" in codes
    assert quick["item_spell_cards"] and all(card["disabled"] for card in quick["item_spell_cards"])


def test_quick_actions_contract_dagger_attack_damage_and_levelled_spell_prompt():
    session = _build_session()
    native = session.char_profiles["bishop"][0]["nativeCharacter"]
    native["spellSaveDc"] = 15
    native["spellAttack"] = "+7"
    native["spellState"] = {
        "known": ["fire-bolt", "fireball"],
        "prepared": ["fire-bolt", "fireball"],
        "slots": {"3": {"max": 2, "used": 0}, "4": {"max": 1, "used": 0}},
    }
    session.player_inventories = {"bishop::profile::f-bishop": [{"id": "dagger-1", "name": "Dagger", "equipped": True, "equipment_kind": "weapon", "damage_dice": "1d4", "damage_type": "piercing"}]}

    quick = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")["payload"]["quick_actions"]

    assert any(a["kind"] == "weapon_attack" and a["name"] == "Dagger" for a in quick["weapon_actions"])
    assert any(a["kind"] == "weapon_damage" and a["damage_formula"] == "1d4" for a in quick["weapon_actions"])
    cantrip = next(a for a in quick["spell_actions"] if a["spell_id"] == "fire-bolt")
    assert cantrip["kind"] == "cantrip_spell"
    assert cantrip["requires_slot"] is False
    assert cantrip["attack_type"] == "Ranged Spell Attack"
    assert cantrip["spell_attack_bonus"] == 7
    fireball = next(a for a in quick["spell_actions"] if a["spell_id"] == "fireball")
    assert fireball["requires_cast_level_prompt"] is True
    assert fireball["can_upcast"] is True
    assert fireball["available_cast_levels"] == [3, 4]
    assert fireball["saving_throw"] == "DEX"
    assert fireball["save_dc"] == 15


def test_quick_actions_contract_quarterstaff_rarity_charges_granted_spells():
    session = _build_session()
    session.player_inventories = {"bishop::profile::f-bishop": [{
        "id": "staff-3", "name": "Quarterstaff +3", "rarity": "very_rare",
        "equipped": True, "attunement_required": True, "attuned": True,
        "equipment_kind": "weapon", "damage_dice": "1d6", "damage_type": "bludgeoning",
        "charges_current": 3, "charges_max": 10,
        "granted_spells": [{"id": "lightning-bolt", "name": "Lightning Bolt", "charge_cost": 2, "cast_level": 3}],
    }]}

    quick = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")["payload"]["quick_actions"]

    assert any(a["kind"] == "weapon_attack" and a["name"] == "Quarterstaff +3" for a in quick["weapon_actions"])
    assert quick["charges"] == [{"item_id": "staff-3", "name": "Quarterstaff +3", "charges_current": 3, "charges_max": 10}]
    card = next(c for c in quick["item_spell_cards"] if c["spell_id"] == "lightning-bolt")
    assert card["kind"] == "item_granted_spell"
    assert card["disabled"] is False
    assert card["charges_current"] == 3
    assert card["charges_max"] == 10


def test_quick_actions_disabled_item_spell_reasons_and_missing_active_profile():
    session = _build_session(active_profile_id="ghost-profile")
    session.player_inventories = {"bishop::profile::ghost-profile": [
        {"id": "s1", "name": "Packed Staff", "equipped": False, "attunement_required": False, "charges_current": 2, "charges_max": 3, "granted_spells": [{"id": "fireball", "charge_cost": 1}]},
        {"id": "s2", "name": "Unattuned Staff", "equipped": True, "attunement_required": True, "attuned": False, "charges_current": 2, "charges_max": 3, "granted_spells": [{"id": "fireball", "charge_cost": 1}]},
        {"id": "s3", "name": "Empty Staff", "equipped": True, "attunement_required": False, "charges_current": 0, "charges_max": 3, "granted_spells": [{"id": "fireball", "charge_cost": 1}]},
        {"id": "s4", "name": "Mystery Staff", "equipped": True, "attunement_required": False, "charges_current": 1, "charges_max": 3, "granted_spells": [{"id": "not-a-real-spell-xyz", "charge_cost": 1}]},
    ]}

    quick = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")["payload"]["quick_actions"]

    assert quick["hydration_status"] == "missing_runtime"
    assert any(d["code"] == "missing_active_profile" for d in quick["diagnostics"])
    reasons = {c["item_id"]: c["disabled_reason"] for c in quick["item_spell_cards"]}
    assert reasons["s1"] == "Not equipped."
    assert reasons["s2"] == "Not attuned."
    assert reasons["s3"].startswith("No charges")
    assert reasons["s4"] == "Missing spell data."


def test_quick_actions_no_equipped_weapon_diagnostic():
    session = _build_session()
    session.player_inventories = {"bishop::profile::f-bishop": [{"id": "rope", "name": "Rope", "equipped": False}]}

    quick = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")["payload"]["quick_actions"]

    assert any(d["code"] == "no_equipped_weapon" for d in quick["diagnostics"])
