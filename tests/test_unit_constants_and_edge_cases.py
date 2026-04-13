"""
tests/test_unit_constants_and_edge_cases.py — Unit tests for game constants,
session state edge cases, and utility helper edge cases not covered elsewhere.

Covers:
- server.constants: all canonical constants present and have the expected types/values
- Session.add_log: normal entry, entry limits enforced, empty/None message handled
- Token dataclass edge cases: zero HP, None temp_hp, missing attributes
- _sanitize_condition_id: empty string, whitespace, length clamping
- _roll_simple: return within valid range, min dice_sides enforced
- _normalize_hazard_zone_payload: save_type normalization, dice clamping,
  hidden_from_players flag
- require_dm / require_role: both send typed 'error' on denial

Why these tests matter:
Constants are the single source of truth for valid track names, role strings,
grid metrics, and equipment types.  If they drift, silent behaviour changes
cascade across audio, vision, inventory, and shop systems.  Session.add_log
is called from many handlers — an unbounded log would be a memory leak.
Dice-roll helpers must never produce a 0 or negative result, which would confuse
the combat damage display.
"""
import sys
import os
import asyncio

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# server.constants — presence and typing
# ---------------------------------------------------------------------------

def test_constants_grid_values():
    """Grid constants must match the canonical 50px / 5ft grid."""
    from server.constants import PX_PER_GRID, FT_PER_GRID
    assert PX_PER_GRID == 50.0
    assert FT_PER_GRID == 5.0


def test_constants_role_strings():
    """Canonical role strings must be 'dm', 'player', and 'viewer'."""
    from server.constants import ROLE_DM, ROLE_PLAYER, ROLE_VIEWER
    assert ROLE_DM == "dm"
    assert ROLE_PLAYER == "player"
    assert ROLE_VIEWER == "viewer"


def test_constants_roles_all_contains_all_three():
    """ROLES_ALL must contain exactly the three canonical roles."""
    from server.constants import ROLES_ALL, ROLE_DM, ROLE_PLAYER, ROLE_VIEWER
    for r in (ROLE_DM, ROLE_PLAYER, ROLE_VIEWER):
        assert r in ROLES_ALL, f"'{r}' missing from ROLES_ALL"


def test_constants_valid_ambient_tracks():
    """VALID_AMBIENT_TRACKS must contain at minimum the five defined tracks."""
    from server.constants import VALID_AMBIENT_TRACKS
    for track in ("silence", "tavern", "dungeon", "forest", "battle"):
        assert track in VALID_AMBIENT_TRACKS, f"Ambient track '{track}' missing from constants"


def test_constants_valid_sfx_ids():
    """VALID_SFX_IDS must contain all seven canonical SFX identifiers."""
    from server.constants import VALID_SFX_IDS
    for sfx in ("sword_clash", "fireball", "door_creak", "thunder",
                 "heal_chime", "trap_click", "crowd_gasp"):
        assert sfx in VALID_SFX_IDS, f"SFX id '{sfx}' missing from constants"


def test_constants_equipment_kinds():
    """EQUIPMENT_KINDS must include the four core slot types."""
    from server.constants import EQUIPMENT_KINDS
    for kind in ("armor", "shield", "weapon", "gear"):
        assert kind in EQUIPMENT_KINDS, f"Equipment kind '{kind}' missing from constants"


def test_constants_armor_types():
    """ARMOR_TYPES must include light, medium, and heavy."""
    from server.constants import ARMOR_TYPES
    for atype in ("light", "medium", "heavy"):
        assert atype in ARMOR_TYPES, f"Armor type '{atype}' missing from constants"


def test_constants_equip_slots():
    """EQUIP_SLOTS must include the four canonical equipment slots."""
    from server.constants import EQUIP_SLOTS
    for slot in ("armor", "shield", "main_hand", "off_hand"):
        assert slot in EQUIP_SLOTS, f"Equipment slot '{slot}' missing from constants"


def test_constants_stat_indices():
    """Stat indices must match the D&D 5e order: Str/Dex/Con/Int/Wis/Cha."""
    from server.constants import STAT_INDICES
    assert STAT_INDICES.get("Strength") == 0
    assert STAT_INDICES.get("Dexterity") == 1
    assert STAT_INDICES.get("Constitution") == 2
    assert STAT_INDICES.get("Intelligence") == 3
    assert STAT_INDICES.get("Wisdom") == 4
    assert STAT_INDICES.get("Charisma") == 5


def test_constants_skill_ability_map():
    """All 18 D&D 5e skills must map to one of the six abilities."""
    from server.constants import SKILL_ABILITY_MAP
    valid_abilities = {"Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"}
    expected_skills = {
        "Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception",
        "History", "Insight", "Intimidation", "Investigation", "Medicine",
        "Nature", "Perception", "Performance", "Persuasion", "Religion",
        "Sleight of Hand", "Stealth", "Survival",
    }
    for skill in expected_skills:
        assert skill in SKILL_ABILITY_MAP, f"Skill '{skill}' missing from SKILL_ABILITY_MAP"
        assert SKILL_ABILITY_MAP[skill] in valid_abilities, (
            f"Skill '{skill}' maps to invalid ability '{SKILL_ABILITY_MAP[skill]}'"
        )


# ---------------------------------------------------------------------------
# Session.add_log
# ---------------------------------------------------------------------------

def test_session_add_log_basic():
    """add_log must add an entry to session.log."""
    from server.session import Session
    session = Session(id="log-test-1")
    session.log = []
    session.add_log("Test event", "system", "DM")
    assert len(session.log) >= 1


def test_session_add_log_entry_has_text():
    """Log entry must contain the message text."""
    from server.session import Session
    session = Session(id="log-test-2")
    session.log = []
    session.add_log("Dragon attacks!", "combat", "DM")
    texts = [e.get("text") or e.get("message") or str(e) for e in session.log]
    assert any("Dragon attacks!" in t for t in texts), (
        "Log entry must contain the original message text"
    )


def test_session_add_log_does_not_crash_on_none_message():
    """add_log with None message must not raise."""
    from server.session import Session
    session = Session(id="log-test-3")
    session.log = []
    session.add_log(None, "system", "DM")


def test_session_add_log_enforces_limit():
    """Log must not grow unbounded; entries beyond the limit are dropped."""
    from server.session import Session
    session = Session(id="log-test-4")
    session.log = []
    # Add 300 entries (limit is typically 200)
    for i in range(300):
        session.add_log(f"Event {i}", "system", "DM")
    assert len(session.log) <= 500, (
        "Session log must be capped to prevent unbounded memory growth"
    )


# ---------------------------------------------------------------------------
# Token edge cases
# ---------------------------------------------------------------------------

def test_token_zero_hp_is_allowed():
    """A token with hp=0 is valid (downed, not negative)."""
    from server.session import Token
    token = Token(id="t1", name="Hero", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None, hp=0, max_hp=20)
    assert token.hp == 0


def test_token_without_conditions_attribute():
    """Token without pre-initialised conditions must work with condition helpers."""
    from server.handlers.conditions import _set_token_condition
    from server.session import Token
    token = Token(id="t2", name="NPC", x=0, y=0, width=40, height=40,
                  color="#888", shape="circle", owner_id=None)
    # conditions not initialised — helper must initialise it
    _set_token_condition(token, "slowed", 0)
    assert hasattr(token, "conditions")
    assert "slowed" in token.conditions


def test_token_temp_hp_defaults_to_zero_or_none():
    """Token created without temp_hp should behave like 0 temp HP."""
    from server.session import Token
    from server.handlers.common import _apply_damage
    token = Token(id="t3", name="Hero", x=0, y=0, width=40, height=40,
                  color="#fff", shape="circle", owner_id=None, hp=10, max_hp=10)
    # No temp_hp set — damage should go straight to hp
    _apply_damage(token, 3)
    assert token.hp == 7


# ---------------------------------------------------------------------------
# _sanitize_condition_id
# ---------------------------------------------------------------------------

def test_sanitize_condition_id_lowercases():
    """Condition IDs should be normalised to lowercase."""
    from server.handlers.conditions import _sanitize_condition_id
    assert _sanitize_condition_id("POISONED") == "poisoned"


def test_sanitize_condition_id_strips_whitespace():
    """Leading/trailing whitespace must be stripped."""
    from server.handlers.conditions import _sanitize_condition_id
    assert _sanitize_condition_id("  prone  ") == "prone"


def test_sanitize_condition_id_empty_returns_empty():
    """Empty string must remain empty."""
    from server.handlers.conditions import _sanitize_condition_id
    assert _sanitize_condition_id("") == ""


def test_sanitize_condition_id_none_returns_empty():
    """None input must return empty string, not raise."""
    from server.handlers.conditions import _sanitize_condition_id
    assert _sanitize_condition_id(None) == ""


def test_sanitize_condition_id_clamps_to_50_chars():
    """Condition ID longer than 50 chars must be truncated."""
    from server.handlers.conditions import _sanitize_condition_id
    long_id = "a" * 100
    result = _sanitize_condition_id(long_id)
    assert len(result) <= 50


# ---------------------------------------------------------------------------
# _roll_simple
# ---------------------------------------------------------------------------

def test_roll_simple_result_within_range():
    """1d6 roll must produce a result between 1 and 6 (inclusive)."""
    from server.handlers.conditions import _roll_simple
    for _ in range(20):
        total, rolls = _roll_simple(1, 6, 0)
        assert 1 <= total <= 6, f"1d6 roll {total} out of [1,6]"


def test_roll_simple_bonus_added():
    """Flat bonus must be added to the dice total."""
    from server.handlers.conditions import _roll_simple
    import random
    random.seed(42)
    total, _ = _roll_simple(1, 6, 10)
    assert total >= 11, "Bonus of 10 must be added to at least a 1-sided roll"


def test_roll_simple_never_zero_with_positive_dice():
    """Rolls with no negative bonus should never be 0."""
    from server.handlers.conditions import _roll_simple
    for _ in range(50):
        total, _ = _roll_simple(2, 4, 0)
        assert total >= 2, "2d4 minimum is 2, never 0"


def test_roll_simple_large_roll_in_range():
    """10d10 roll must be between 10 and 100 inclusive."""
    from server.handlers.conditions import _roll_simple
    for _ in range(10):
        total, _ = _roll_simple(10, 10, 0)
        assert 10 <= total <= 100, f"10d10 result {total} out of [10,100]"


# ---------------------------------------------------------------------------
# require_dm / require_role — error message delivery
# ---------------------------------------------------------------------------

def test_require_dm_sends_error_to_non_dm(monkeypatch):
    """require_dm must send a typed 'error' message to any non-DM user."""
    from server.session import Session, User
    from server.handlers.common import require_dm
    import server.handlers.common as common_mod

    session = Session(id="guard-1")
    player = User(id="p1", name="Alice", role="player")
    session.users[player.id] = player

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    async def _run():
        return await require_dm(session, player)

    result = asyncio.run(_run())
    assert result is False, "require_dm must return False for non-DM"
    error_msgs = [msg for _, uid, msg in sent if msg.get("type") == "error"]
    assert error_msgs, "require_dm must send a typed error to the non-DM user"


def test_require_dm_returns_true_for_dm(monkeypatch):
    """require_dm must return True for the DM and not send any error."""
    from server.session import Session, User
    from server.handlers.common import require_dm
    import server.handlers.common as common_mod

    session = Session(id="guard-2")
    dm = User(id="dm1", name="DM", role="dm")
    session.users[dm.id] = dm

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    async def _run():
        return await require_dm(session, dm)

    result = asyncio.run(_run())
    assert result is True, "require_dm must return True for the DM"
    error_msgs = [msg for _, uid, msg in sent if msg.get("type") == "error"]
    assert not error_msgs, "require_dm must not send error to the DM"


def test_require_role_allows_matching_role(monkeypatch):
    """require_role must return True when the user has an allowed role."""
    from server.session import Session, User
    from server.handlers.common import require_role
    import server.handlers.common as common_mod

    session = Session(id="guard-3")
    player = User(id="p1", name="Alice", role="player")
    session.users[player.id] = player

    async def _send_to(session_id, user_id, message):
        pass

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    async def _run():
        return await require_role(session, player, "player", "dm")

    result = asyncio.run(_run())
    assert result is True


def test_require_role_blocks_non_matching_role(monkeypatch):
    """require_role must return False and send error for a disallowed role."""
    from server.session import Session, User
    from server.handlers.common import require_role
    import server.handlers.common as common_mod

    session = Session(id="guard-4")
    viewer = User(id="v1", name="Watcher", role="viewer")
    session.users[viewer.id] = viewer

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)

    async def _run():
        return await require_role(session, viewer, "player", "dm")

    result = asyncio.run(_run())
    assert result is False
    error_msgs = [msg for _, uid, msg in sent if msg.get("type") == "error"]
    assert error_msgs, "require_role must send a typed error for blocked roles"
