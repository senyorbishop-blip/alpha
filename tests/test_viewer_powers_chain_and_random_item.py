"""
tests/test_viewer_powers_chain_and_random_item.py — Tests for two new viewer
powers: Chain Lightning (chain_damage) and Give Random Item (grant_random_item).

Chain Lightning starts on one chosen token then arcs to the nearest not-yet-hit
tokens within range, bouncing between 4 and 6 in all.  Each struck token rolls a
DEX save (DC 17); on a save it takes half of a fresh 4d6 roll, otherwise full.

Give Random Item draws a random row from the shared item library and adds it to
the targeted player token owner's inventory.
"""
import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _patch_manager(monkeypatch):
    import server.handlers.common as common_mod
    broadcasts = []

    async def _broadcast(session_id, message, exclude_user=None):
        broadcasts.append((session_id, message, exclude_user))

    async def _send_to(session_id, user_id, message):
        broadcasts.append((session_id, message, user_id))

    monkeypatch.setattr(common_mod.manager, "broadcast", _broadcast)
    monkeypatch.setattr(common_mod.manager, "send_to", _send_to)
    return broadcasts


def _make_session():
    from server.session import Session, User, Token
    session = Session(id="vp-chain-1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="player1", name="Alice", role="player")
    viewer = User(id="viewer1", name="Spectator", role="viewer")
    for u in (dm, player, viewer):
        session.users[u.id] = u
    session.dm_id = dm.id
    session.dm_map_context = "world"
    return session, dm, player, viewer


def _add_token(session, tid, x, y, owner_id=""):
    from server.session import Token
    token = Token(id=tid, name=tid, x=x, y=y, width=40, height=40,
                  color="#f00", shape="circle", owner_id=owner_id, hp=60, max_hp=60)
    session.tokens[token.id] = token
    return token


# ---------------------------------------------------------------------------
# Chain Lightning
# ---------------------------------------------------------------------------

def test_chain_lightning_bounces_between_four_and_six(monkeypatch):
    """With plenty of tokens packed in range, the bolt hits 4-6 of them."""
    from server.handlers import viewer_powers as vp
    _patch_manager(monkeypatch)
    session, dm, player, viewer = _make_session()
    # Eight tokens, each one grid square (50px) from the previous, well within
    # the 30 ft (300px) bounce radius of their neighbours.
    for i in range(8):
        _add_token(session, f"t{i}", x=i * 50, y=0)

    affected, msg = asyncio.run(
        vp._resolve_viewer_power(session, "Spectator", "chain_lightning", {"token_id": "t0"})
    )

    assert affected is not None, msg
    assert 4 <= len(affected) <= 6, f"expected 4-6 targets, got {len(affected)}: {msg}"
    # The chosen token is always the first link in the chain.
    assert affected[0].id == "t0"
    # Every struck token took at least the half-damage minimum of 4d6 (=2).
    for tok in affected:
        assert tok.hp < 60, f"{tok.id} should have taken damage"


def test_chain_lightning_requires_visible_target(monkeypatch):
    from server.handlers import viewer_powers as vp
    _patch_manager(monkeypatch)
    session, dm, player, viewer = _make_session()
    affected, msg = asyncio.run(
        vp._resolve_viewer_power(session, "Spectator", "chain_lightning", {"token_id": "nope"})
    )
    assert affected is None
    assert "target token" in msg.lower()


def test_chain_lightning_stops_when_no_token_in_range(monkeypatch):
    """A lone token with no neighbours in range is the only one struck."""
    from server.handlers import viewer_powers as vp
    _patch_manager(monkeypatch)
    session, dm, player, viewer = _make_session()
    _add_token(session, "lonely", x=0, y=0)
    _add_token(session, "faraway", x=5000, y=5000)  # well outside 300px bounce
    affected, msg = asyncio.run(
        vp._resolve_viewer_power(session, "Spectator", "chain_lightning", {"token_id": "lonely"})
    )
    assert affected is not None, msg
    assert [t.id for t in affected] == ["lonely"]


# ---------------------------------------------------------------------------
# Give Random Item
# ---------------------------------------------------------------------------

def test_give_random_item_adds_library_item_to_player(monkeypatch):
    from server.handlers import viewer_powers as vp
    import server.rules_db as rules_db
    _patch_manager(monkeypatch)
    session, dm, player, viewer = _make_session()
    _add_token(session, "atok", x=0, y=0, owner_id="player1")

    fake_library = [
        {"name": "Wand of Wonder", "description": "Chaos in a stick", "default_price": "500 gp", "default_qty": 1},
    ]
    monkeypatch.setattr(rules_db, "get_all_srd_items", lambda: fake_library)

    affected, msg = asyncio.run(
        vp._resolve_viewer_power(session, "Spectator", "give_random_item", {"token_id": "atok"})
    )

    assert affected is not None, msg
    assert "Wand of Wonder" in msg
    inv = (getattr(session, "player_inventories", {}) or {})
    names = [str(e.get("name")) for entries in inv.values() for e in entries]
    assert "Wand of Wonder" in names


def test_give_random_item_rejects_non_player_token(monkeypatch):
    from server.handlers import viewer_powers as vp
    _patch_manager(monkeypatch)
    session, dm, player, viewer = _make_session()
    _add_token(session, "npc", x=0, y=0, owner_id="")  # no owner
    affected, msg = asyncio.run(
        vp._resolve_viewer_power(session, "Spectator", "give_random_item", {"token_id": "npc"})
    )
    assert affected is None
    assert "player" in msg.lower()


def test_give_random_item_falls_back_when_library_empty(monkeypatch):
    from server.handlers import viewer_powers as vp
    import server.rules_db as rules_db
    _patch_manager(monkeypatch)
    session, dm, player, viewer = _make_session()
    _add_token(session, "atok", x=0, y=0, owner_id="player1")
    monkeypatch.setattr(rules_db, "get_all_srd_items", lambda: [])

    affected, msg = asyncio.run(
        vp._resolve_viewer_power(session, "Spectator", "give_random_item", {"token_id": "atok"})
    )
    assert affected is not None, msg
    inv = (getattr(session, "player_inventories", {}) or {})
    names = [str(e.get("name")) for entries in inv.values() for e in entries]
    assert names, "a fallback item should have been granted"
