"""
tests/test_unit_utility_functions.py — Unit tests for all shared utility
functions in server/handlers/common.py.

Tests cover:
- _safe_int / _safe_float: null inputs, empty string, NaN, min/max clamps
- _apply_damage / _apply_heal: zero HP, temp HP absorption, overflow heal
- _sanitize_save_bonuses: null, empty, invalid types, correct abbreviations
- _token_center: zero-size tokens, fractional positions
- _sanitize_token_vision_payload: disabled vision, darkvision, camelCase keys,
  player-owned default radius, existing-token fallback values
- _is_dm_token / _can_user_see_token: role checks, hidden flag
- _get_combatant_by_token_id: missing combat, empty combatants
- _sync_combatant_token_state: death-save initialization, NPC pruning
- send_error: typed error message delivery
- require_dm: DM guard, custom message, non-DM roles rejected
- require_role: allowed/blocked roles, custom message
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# _safe_int
# ---------------------------------------------------------------------------

def test_safe_int_converts_string_to_int():
    """Normal numeric string should coerce to int."""
    from server.handlers.common import _safe_int
    assert _safe_int("42") == 42


def test_safe_int_returns_default_for_none():
    """None input should fall back to the supplied default."""
    from server.handlers.common import _safe_int
    assert _safe_int(None, 7) == 7


def test_safe_int_returns_default_for_empty_string():
    """Empty string is non-numeric and should return default."""
    from server.handlers.common import _safe_int
    assert _safe_int("", 3) == 3


def test_safe_int_returns_default_for_invalid_string():
    """Non-numeric string should return default."""
    from server.handlers.common import _safe_int
    assert _safe_int("abc", 0) == 0


def test_safe_int_clamps_to_minimum():
    """Value below minimum should be clamped."""
    from server.handlers.common import _safe_int
    assert _safe_int(-5, 0, minimum=0) == 0


def test_safe_int_clamps_to_maximum():
    """Value above maximum should be clamped."""
    from server.handlers.common import _safe_int
    assert _safe_int(1500, 0, maximum=1000) == 1000


def test_safe_int_respects_min_max_together():
    """Both bounds should be applied simultaneously."""
    from server.handlers.common import _safe_int
    assert _safe_int(50, 0, minimum=10, maximum=20) == 20
    assert _safe_int(5, 0, minimum=10, maximum=20) == 10


def test_safe_int_float_string_returns_default():
    """'3.9' is not a valid int literal in Python; should return default."""
    from server.handlers.common import _safe_int
    # Python's int("3.9") raises ValueError — the function returns the default.
    assert _safe_int("3.9", 0) == 0


def test_safe_int_negative_values_pass_through_without_bound():
    """Negative values without bounds should be preserved."""
    from server.handlers.common import _safe_int
    assert _safe_int("-10", 0) == -10


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

def test_safe_float_converts_string():
    from server.handlers.common import _safe_float
    assert _safe_float("1.5") == 1.5


def test_safe_float_returns_default_for_none():
    from server.handlers.common import _safe_float
    assert _safe_float(None, 0.7) == 0.7


def test_safe_float_clamps_minimum():
    from server.handlers.common import _safe_float
    assert _safe_float(-0.5, 0.0, minimum=0.0) == 0.0


def test_safe_float_clamps_maximum():
    from server.handlers.common import _safe_float
    assert _safe_float(1.5, 0.7, maximum=1.0) == 1.0


def test_safe_float_invalid_string_returns_default():
    from server.handlers.common import _safe_float
    assert _safe_float("not-a-number", 0.5) == 0.5


# ---------------------------------------------------------------------------
# _apply_damage
# ---------------------------------------------------------------------------

def test_apply_damage_reduces_hp():
    """Normal damage should subtract from hp."""
    from server.handlers.common import _apply_damage
    from server.session import Token
    token = Token(id="t1", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=20, max_hp=20)
    _apply_damage(token, 5)
    assert token.hp == 15


def test_apply_damage_absorbed_by_temp_hp():
    """Temp HP should absorb damage before real HP."""
    from server.handlers.common import _apply_damage
    from server.session import Token
    token = Token(id="t2", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=20, max_hp=20)
    token.temp_hp = 10
    _apply_damage(token, 8)
    assert token.temp_hp == 2
    assert token.hp == 20  # no real HP removed


def test_apply_damage_overflow_beyond_temp_hp():
    """Damage exceeding temp HP should spill into real HP."""
    from server.handlers.common import _apply_damage
    from server.session import Token
    token = Token(id="t3", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=20, max_hp=20)
    token.temp_hp = 3
    _apply_damage(token, 10)
    assert token.temp_hp == 0
    assert token.hp == 13  # 20 - (10 - 3)


def test_apply_damage_cannot_go_below_zero():
    """HP must never go below 0."""
    from server.handlers.common import _apply_damage
    from server.session import Token
    token = Token(id="t4", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=5, max_hp=20)
    _apply_damage(token, 100)
    assert token.hp == 0


def test_apply_damage_noop_when_no_hp_attribute():
    """Token without hp should not raise; should return 0."""
    from server.handlers.common import _apply_damage
    from server.session import Token
    token = Token(id="t5", name="Prop", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle")
    # hp is None on this token
    token.hp = None
    result = _apply_damage(token, 10)
    assert result == 0


def test_apply_damage_zero_damage_is_noop():
    """Zero damage should leave HP unchanged."""
    from server.handlers.common import _apply_damage
    from server.session import Token
    token = Token(id="t6", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=20, max_hp=20)
    _apply_damage(token, 0)
    assert token.hp == 20


# ---------------------------------------------------------------------------
# _apply_heal
# ---------------------------------------------------------------------------

def test_apply_heal_restores_hp():
    """Normal healing should add to HP."""
    from server.handlers.common import _apply_heal
    from server.session import Token
    token = Token(id="h1", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=5, max_hp=20)
    _apply_heal(token, 10)
    assert token.hp == 15


def test_apply_heal_does_not_exceed_max_hp():
    """Healing beyond max_hp should cap at max_hp."""
    from server.handlers.common import _apply_heal
    from server.session import Token
    token = Token(id="h2", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=18, max_hp=20)
    _apply_heal(token, 10)
    assert token.hp == 20


def test_apply_heal_overflow_becomes_temp_hp():
    """Excess healing beyond max_hp should become temporary HP."""
    from server.handlers.common import _apply_heal
    from server.session import Token
    token = Token(id="h3", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=18, max_hp=20)
    token.temp_hp = 0
    _apply_heal(token, 15)
    assert token.hp == 20
    assert token.temp_hp == 13  # 15 - 2 headroom


def test_apply_heal_noop_when_hp_is_none():
    """Token without HP attribute should not raise; should return 0."""
    from server.handlers.common import _apply_heal
    from server.session import Token
    token = Token(id="h4", name="Prop", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle")
    token.hp = None
    result = _apply_heal(token, 10)
    assert result == 0


def test_apply_heal_zero_heal_is_noop():
    """Zero healing should leave HP unchanged."""
    from server.handlers.common import _apply_heal
    from server.session import Token
    token = Token(id="h5", name="Hero", x=0, y=0, width=40, height=40, owner_id=None,
                  color="#fff", shape="circle", hp=10, max_hp=20)
    _apply_heal(token, 0)
    assert token.hp == 10


# ---------------------------------------------------------------------------
# _sanitize_save_bonuses
# ---------------------------------------------------------------------------

def test_sanitize_save_bonuses_valid_input():
    """Standard dictionary with all six abilities should round-trip."""
    from server.handlers.common import _sanitize_save_bonuses
    result = _sanitize_save_bonuses({"str": 2, "dex": 4, "con": 1, "int": 0, "wis": -1, "cha": 3})
    assert result == {"str": 2, "dex": 4, "con": 1, "int": 0, "wis": -1, "cha": 3}


def test_sanitize_save_bonuses_none_returns_empty():
    """None input should produce an empty dict."""
    from server.handlers.common import _sanitize_save_bonuses
    assert _sanitize_save_bonuses(None) == {}


def test_sanitize_save_bonuses_empty_dict():
    """Empty dict should produce an empty dict."""
    from server.handlers.common import _sanitize_save_bonuses
    assert _sanitize_save_bonuses({}) == {}


def test_sanitize_save_bonuses_invalid_type():
    """Non-dict input should produce an empty dict."""
    from server.handlers.common import _sanitize_save_bonuses
    assert _sanitize_save_bonuses("not-a-dict") == {}
    assert _sanitize_save_bonuses(42) == {}
    assert _sanitize_save_bonuses([1, 2]) == {}


def test_sanitize_save_bonuses_string_values_coerced():
    """String numbers should be coerced to int."""
    from server.handlers.common import _sanitize_save_bonuses
    result = _sanitize_save_bonuses({"str": "3", "dex": "1"})
    assert result.get("str") == 3
    assert result.get("dex") == 1


def test_sanitize_save_bonuses_non_numeric_strings_dropped():
    """Non-numeric strings should be silently dropped."""
    from server.handlers.common import _sanitize_save_bonuses
    result = _sanitize_save_bonuses({"str": "abc", "dex": 2})
    assert "str" not in result
    assert result.get("dex") == 2


def test_sanitize_save_bonuses_only_valid_keys_kept():
    """Unknown keys should be silently dropped."""
    from server.handlers.common import _sanitize_save_bonuses
    result = _sanitize_save_bonuses({"str": 1, "luck": 5, "fortitude": 3})
    assert "luck" not in result
    assert "fortitude" not in result
    assert result.get("str") == 1


def test_sanitize_save_bonuses_empty_string_values_dropped():
    """Empty string values should be omitted."""
    from server.handlers.common import _sanitize_save_bonuses
    result = _sanitize_save_bonuses({"str": "", "dex": 2})
    assert "str" not in result


# ---------------------------------------------------------------------------
# _token_center
# ---------------------------------------------------------------------------

def test_token_center_basic():
    """Center should be position + half-size."""
    from server.handlers.common import _token_center
    from server.session import Token
    token = Token(id="c1", name="A", x=10.0, y=20.0, width=40.0, height=60.0,
                  color="#fff", shape="circle", owner_id=None)
    cx, cy = _token_center(token)
    assert cx == 30.0
    assert cy == 50.0


def test_token_center_zero_size():
    """Zero-size token center equals its position."""
    from server.handlers.common import _token_center
    from server.session import Token
    token = Token(id="c2", name="A", x=5.0, y=5.0, width=0.0, height=0.0,
                  color="#fff", shape="circle", owner_id=None)
    cx, cy = _token_center(token)
    assert cx == 5.0
    assert cy == 5.0


def test_token_center_at_origin():
    """Token at (0,0) with no size should return (0,0)."""
    from server.handlers.common import _token_center
    from server.session import Token
    token = Token(id="c3", name="A", x=0, y=0, width=0, height=0,
                  color="#fff", shape="circle", owner_id=None)
    assert _token_center(token) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# _sanitize_token_vision_payload
# ---------------------------------------------------------------------------

def test_sanitize_vision_defaults_enabled_for_player_owned():
    """Player-owned tokens should have vision enabled by default."""
    from server.handlers.common import _sanitize_token_vision_payload
    result = _sanitize_token_vision_payload({}, owner_id="player-1")
    assert result["vision_enabled"] is True
    assert result["vision_radius"] > 0


def test_sanitize_vision_disabled_for_npc_token():
    """NPC tokens with no owner should default to vision disabled."""
    from server.handlers.common import _sanitize_token_vision_payload
    result = _sanitize_token_vision_payload({}, owner_id=None, token_type="monster")
    assert result["vision_enabled"] is False
    assert result["vision_radius"] == 0


def test_sanitize_vision_camelcase_keys_accepted():
    """camelCase payload keys (from JS) should be accepted."""
    from server.handlers.common import _sanitize_token_vision_payload
    result = _sanitize_token_vision_payload(
        {"visionEnabled": True, "visionRadius": 120},
        owner_id="p1"
    )
    assert result["vision_enabled"] is True
    assert result["vision_radius"] == 120


def test_sanitize_vision_disabled_zeros_out_radii():
    """When vision is disabled, all vision radii should be zeroed."""
    from server.handlers.common import _sanitize_token_vision_payload
    result = _sanitize_token_vision_payload(
        {"visionEnabled": False, "visionRadius": 60, "brightRadius": 30, "dimRadius": 60},
        owner_id="p1"
    )
    assert result["vision_enabled"] is False
    assert result["vision_radius"] == 0
    assert result["bright_radius"] == 0
    assert result["dim_radius"] == 0


def test_sanitize_vision_radius_clamped_to_max():
    """Vision radius must be clamped to the maximum allowed (1000)."""
    from server.handlers.common import _sanitize_token_vision_payload
    result = _sanitize_token_vision_payload(
        {"visionEnabled": True, "visionRadius": 99999},
        owner_id="p1"
    )
    assert result["vision_radius"] <= 1000


def test_sanitize_vision_darkvision_no_radius_when_disabled():
    """Darkvision radius should be 0 when hasDarkvision is False."""
    from server.handlers.common import _sanitize_token_vision_payload
    result = _sanitize_token_vision_payload(
        {"hasDarkvision": False, "darkvisionRadius": 60},
        owner_id="p1"
    )
    assert result["darkvision_radius"] == 0


def test_sanitize_vision_darkvision_radius_preserved():
    """Darkvision radius should be preserved when hasDarkvision is True."""
    from server.handlers.common import _sanitize_token_vision_payload
    result = _sanitize_token_vision_payload(
        {"visionEnabled": True, "hasDarkvision": True, "darkvisionRadius": 60},
        owner_id="p1"
    )
    assert result["has_darkvision"] is True
    assert result["darkvision_radius"] == 60


def test_sanitize_vision_uses_existing_when_raw_is_empty():
    """When raw payload is empty, existing token values should be preserved."""
    from server.handlers.common import _sanitize_token_vision_payload
    from server.session import Token
    existing = Token(id="e1", name="A", x=0, y=0, width=40, height=40,
                     color="#fff", shape="circle", owner_id="p1")
    existing.vision_enabled = True
    existing.vision_radius = 90
    existing.bright_radius = 30
    existing.dim_radius = 90
    existing.has_darkvision = False
    existing.darkvision_radius = 0
    result = _sanitize_token_vision_payload({}, owner_id="p1", existing=existing)
    assert result["vision_enabled"] is True
    assert result["vision_radius"] == 90


# ---------------------------------------------------------------------------
# _is_dm_token / _can_user_see_token
# ---------------------------------------------------------------------------

def test_is_dm_token_no_owner():
    """Token without owner is a DM token."""
    from server.handlers.common import _is_dm_token
    from server.session import Token
    token = Token(id="dm1", name="A", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    assert _is_dm_token(token) is True


def test_is_dm_token_with_owner():
    """Token with owner is a player token."""
    from server.handlers.common import _is_dm_token
    from server.session import Token
    token = Token(id="pl1", name="A", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id="player-1")
    assert _is_dm_token(token) is False


def test_can_user_see_token_dm_always_sees():
    """DM should always see every token."""
    from server.handlers.common import _can_user_see_token
    from server.session import Session, Token, User
    session = Session(id="s")
    dm = User(id="dm", name="DM", role="dm")
    hidden_token = Token(id="h1", name="A", x=0, y=0, width=40, height=40,
                         color="#fff", shape="circle", owner_id=None)
    hidden_token.hidden = True
    assert _can_user_see_token(session, hidden_token, dm) is True


def test_can_user_see_token_player_cannot_see_hidden():
    """Players should not see hidden tokens."""
    from server.handlers.common import _can_user_see_token
    from server.session import Session, Token, User
    session = Session(id="s")
    player = User(id="p1", name="Alice", role="player")
    hidden_token = Token(id="h2", name="A", x=0, y=0, width=40, height=40,
                         color="#fff", shape="circle", owner_id=None)
    hidden_token.hidden = True
    assert _can_user_see_token(session, hidden_token, player) is False


def test_can_user_see_token_player_sees_visible():
    """Players should see non-hidden tokens."""
    from server.handlers.common import _can_user_see_token
    from server.session import Session, Token, User
    session = Session(id="s")
    player = User(id="p2", name="Bob", role="player")
    visible_token = Token(id="v1", name="A", x=0, y=0, width=40, height=40,
                          color="#fff", shape="circle", owner_id=None)
    visible_token.hidden = False
    assert _can_user_see_token(session, visible_token, player) is True


def test_can_user_see_token_none_user_returns_false():
    """None user should always return False."""
    from server.handlers.common import _can_user_see_token
    from server.session import Session, Token
    session = Session(id="s")
    token = Token(id="v2", name="A", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None)
    assert _can_user_see_token(session, token, None) is False


# ---------------------------------------------------------------------------
# _get_combatant_by_token_id
# ---------------------------------------------------------------------------

def test_get_combatant_by_token_id_found():
    """Matching combatant should be returned."""
    from server.handlers.common import _get_combatant_by_token_id
    from server.session import Session
    session = Session(id="combat-unit-1")
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{"token_id": "tok1", "name": "Hero", "initiative": 15}],
    }
    result = _get_combatant_by_token_id(session, "tok1")
    assert result is not None
    assert result["name"] == "Hero"


def test_get_combatant_by_token_id_not_found():
    """Missing token_id should return None."""
    from server.handlers.common import _get_combatant_by_token_id
    from server.session import Session
    session = Session(id="combat-unit-2")
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{"token_id": "tok1", "name": "Hero"}],
    }
    assert _get_combatant_by_token_id(session, "tok-nonexistent") is None


def test_get_combatant_by_token_id_no_combat():
    """When there is no combat, should return None."""
    from server.handlers.common import _get_combatant_by_token_id
    from server.session import Session
    session = Session(id="combat-unit-3")
    assert _get_combatant_by_token_id(session, "tok1") is None


def test_get_combatant_by_token_id_empty_combatants():
    """Empty combatants list should return None."""
    from server.handlers.common import _get_combatant_by_token_id
    from server.session import Session
    session = Session(id="combat-unit-4")
    session.combat = {"active": True, "turn": 0, "combatants": []}
    assert _get_combatant_by_token_id(session, "tok1") is None


# ---------------------------------------------------------------------------
# _sync_combatant_token_state
# ---------------------------------------------------------------------------

def test_sync_combatant_death_saves_initialised_on_player_hp_zero():
    """Death saves should be initialised when a player combatant drops to 0 HP."""
    from server.handlers.common import _sync_combatant_token_state
    from server.session import Session, Token
    session = Session(id="ds-test-1")
    token = Token(id="tok1", name="Hero", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id="player-1", hp=0, max_hp=20)
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{"token_id": "tok1", "is_player": True, "hp": 5, "max_hp": 20}],
    }
    changed = _sync_combatant_token_state(session, token, previous_hp=5)
    assert changed is True
    combatant = session.combat["combatants"][0]
    assert "death_saves" in combatant
    assert combatant["death_saves"]["successes"] == 0
    assert combatant["death_saves"]["fails"] == 0


def test_sync_combatant_death_saves_removed_on_heal():
    """Death saves should be removed when a player is healed above 0."""
    from server.handlers.common import _sync_combatant_token_state
    from server.session import Session, Token
    session = Session(id="ds-test-2")
    token = Token(id="tok1", name="Hero", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id="player-1", hp=5, max_hp=20)
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{
            "token_id": "tok1",
            "is_player": True,
            "hp": 5,
            "max_hp": 20,
            "death_saves": {"successes": 2, "fails": 1, "stable": False, "dead": False},
        }],
    }
    changed = _sync_combatant_token_state(session, token, previous_hp=0)
    assert changed is True
    combatant = session.combat["combatants"][0]
    assert "death_saves" not in combatant


def test_sync_combatant_npc_death_saves_pruned():
    """NPC combatants should never get death saves."""
    from server.handlers.common import _sync_combatant_token_state
    from server.session import Session, Token
    session = Session(id="ds-test-3")
    token = Token(id="tok1", name="Wolf", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None, hp=0, max_hp=12)
    session.combat = {
        "active": True,
        "turn": 0,
        "combatants": [{
            "token_id": "tok1",
            "is_player": False,
            "hp": 0,
            "max_hp": 12,
            "death_saves": {"successes": 0, "fails": 0, "stable": False, "dead": False},
        }],
    }
    changed = _sync_combatant_token_state(session, token)
    combatant = session.combat["combatants"][0]
    assert "death_saves" not in combatant


# ---------------------------------------------------------------------------
# send_error
# ---------------------------------------------------------------------------

def _make_minimal_session_and_user(session_id="s1", user_id="u1", role="player"):
    from server.session import Session, User
    session = Session(id=session_id)
    user = User(id=user_id, name="TestUser", role=role)
    session.users[user.id] = user
    return session, user


def test_send_error_delivers_error_typed_message(monkeypatch):
    """send_error must send a message with type 'error' to the target user."""
    import asyncio
    from server.handlers.common import send_error
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user()
    asyncio.run(send_error(session, user.id, "test error"))

    assert len(sent) == 1
    sid, uid, msg = sent[0]
    assert sid == session.id
    assert uid == user.id
    assert msg["type"] == "error"
    assert msg["payload"]["message"] == "test error"


def test_send_error_uses_provided_message_text(monkeypatch):
    """send_error must pass through the exact message string."""
    import asyncio
    from server.handlers.common import send_error
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user()
    asyncio.run(send_error(session, user.id, "You cannot do that here."))

    assert sent[0]["payload"]["message"] == "You cannot do that here."


# ---------------------------------------------------------------------------
# require_dm
# ---------------------------------------------------------------------------

def test_require_dm_returns_true_for_dm(monkeypatch):
    """require_dm must return True and send nothing when user is DM."""
    import asyncio
    from server.handlers.common import require_dm
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user(role="dm")
    result = asyncio.run(require_dm(session, user))

    assert result is True
    assert sent == []


def test_require_dm_returns_false_for_player(monkeypatch):
    """require_dm must return False and send an error when user is a player."""
    import asyncio
    from server.handlers.common import require_dm
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user(role="player")
    result = asyncio.run(require_dm(session, user))

    assert result is False
    assert len(sent) == 1
    assert sent[0]["type"] == "error"


def test_require_dm_returns_false_for_viewer(monkeypatch):
    """require_dm must return False and send an error when user is a viewer."""
    import asyncio
    from server.handlers.common import require_dm
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user(role="viewer")
    result = asyncio.run(require_dm(session, user))

    assert result is False
    assert len(sent) == 1


def test_require_dm_custom_message(monkeypatch):
    """require_dm must use the custom message when supplied."""
    import asyncio
    from server.handlers.common import require_dm
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user(role="player")
    asyncio.run(require_dm(session, user, message="DM only!"))

    assert sent[0]["payload"]["message"] == "DM only!"


# ---------------------------------------------------------------------------
# require_role
# ---------------------------------------------------------------------------

def test_require_role_returns_true_when_role_matches(monkeypatch):
    """require_role must return True and send nothing for an allowed role."""
    import asyncio
    from server.handlers.common import require_role
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user(role="player")
    result = asyncio.run(require_role(session, user, "dm", "player"))

    assert result is True
    assert sent == []


def test_require_role_returns_false_for_blocked_role(monkeypatch):
    """require_role must return False and send an error when role is not allowed."""
    import asyncio
    from server.handlers.common import require_role
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user(role="viewer")
    result = asyncio.run(require_role(session, user, "dm", "player"))

    assert result is False
    assert len(sent) == 1
    assert sent[0]["type"] == "error"


def test_require_role_dm_always_passes_when_included(monkeypatch):
    """DM role must pass require_role when 'dm' is in the allowed set."""
    import asyncio
    from server.handlers.common import require_role
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user(role="dm")
    result = asyncio.run(require_role(session, user, "dm"))

    assert result is True
    assert sent == []


def test_require_role_custom_message_on_failure(monkeypatch):
    """require_role must use the custom message when supplied."""
    import asyncio
    from server.handlers.common import require_role
    import server.handlers.common as common_mod

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append(message)

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    session, user = _make_minimal_session_and_user(role="viewer")
    asyncio.run(require_role(session, user, "dm", message="Restricted area."))

    assert sent[0]["payload"]["message"] == "Restricted area."


# ---------------------------------------------------------------------------
# Treasury carry logic (update_party_treasury / set_party_treasury)
# ---------------------------------------------------------------------------

def _make_treasury_db(tmp_path):
    """Return a rules_db module wired to a fresh in-memory SQLite database."""
    import server.rules_db as rules_db

    db_path = str(tmp_path / "test_treasury.db")
    original_get_conn = rules_db.get_conn

    import contextlib
    import sqlite3

    @contextlib.contextmanager
    def patched_get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    rules_db.get_conn = patched_get_conn
    # Initialise the party_treasury table
    with patched_get_conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS party_treasury "
            "(campaign_id TEXT PRIMARY KEY, gold INTEGER DEFAULT 0, "
            "silver INTEGER DEFAULT 0, copper INTEGER DEFAULT 0, "
            "gems TEXT DEFAULT '[]', art_objects TEXT DEFAULT '[]', updated_at REAL)"
        )
        conn.commit()

    return rules_db, patched_get_conn, original_get_conn


def test_treasury_adding_15_copper_to_zero_carries_to_silver(tmp_path):
    """Adding 15cp to an empty treasury should yield copper=5, silver=1, gold=0."""
    rules_db, patched_conn, original_conn = _make_treasury_db(tmp_path)
    try:
        result = rules_db.update_party_treasury("camp1", gold=0, silver=0, copper=15)
        assert result["copper"] == 5
        assert result["silver"] == 1
        assert result["gold"] == 0
    finally:
        rules_db.get_conn = original_conn


def test_treasury_adding_25_silver_to_zero_carries_to_gold(tmp_path):
    """Adding 25sp to an empty treasury should yield silver=5, gold=2, copper=0."""
    rules_db, patched_conn, original_conn = _make_treasury_db(tmp_path)
    try:
        result = rules_db.update_party_treasury("camp2", gold=0, silver=25, copper=0)
        assert result["copper"] == 0
        assert result["silver"] == 5
        assert result["gold"] == 2
    finally:
        rules_db.get_conn = original_conn


def test_treasury_negative_gold_delta_clamped_to_zero(tmp_path):
    """A negative gold delta that would make gold negative is clamped at 0."""
    rules_db, patched_conn, original_conn = _make_treasury_db(tmp_path)
    try:
        # Start empty (gold=0), subtract 5 gold — result should be 0, not negative.
        result = rules_db.update_party_treasury("camp3", gold=-5, silver=0, copper=0)
        assert result["gold"] >= 0
    finally:
        rules_db.get_conn = original_conn


def test_set_treasury_normalises_carry(tmp_path):
    """set_party_treasury should normalise carry: 15cp→copper=5,silver=1; 12sp→silver=3,gold=1."""
    rules_db, patched_conn, original_conn = _make_treasury_db(tmp_path)
    try:
        # 0 gold, 12 silver, 15 copper → carry: 15cp = 1sp+5cp, 13sp = 1gp+3sp
        result = rules_db.set_party_treasury("camp4", gold=0, silver=12, copper=15)
        assert result["copper"] == 5
        assert result["silver"] == 3
        assert result["gold"] == 1
    finally:
        rules_db.get_conn = original_conn
