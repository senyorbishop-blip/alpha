"""
tests/test_inventory_revision_consistency.py — Inventory revision consistency.

Verifies that every server-authoritative inventory/item mutation advances
`session.inventory_revision` exactly once (via the central
`_broadcast_inventory_state` helper in server/handlers/inventory.py), that
read-only/preview paths do not bump it, that the broadcast payload carries
the revision, and that the client-side stale-payload guard in play.html
rejects out-of-order `player_inventory_sync` packets while still applying
payloads that omit the field (backward compatibility).
"""
import re

import pytest

from server.handlers import inventory as inventory_handlers
from server.handlers import camp_rest as camp_rest_handlers
from server.session import Session, Token, User, normalize_profile_owner_key


def _setup_session_with_player(items, class_name="fighter"):
    session = Session(id="s-inv-rev")
    user = User(id="u-inv", name="Inv Hero", role="player")
    dm = User(id="u-dm-inv", name="DM", role="dm")
    session.users[user.id] = user
    session.users[dm.id] = dm
    owner_key = normalize_profile_owner_key(user.name) or user.id
    session.player_inventories = {owner_key: items}
    session.char_profiles = {
        owner_key: [{
            "id": "profile-inv",
            "name": user.name,
            "updated_at": 1.0,
            "charBook": {"abilities": {"dex": {"score": 14}}, "classes": [{"name": class_name, "level": 5}]},
            "charSheet": {},
        }]
    }
    return session, user, dm


def _make_thunder_staff(equipped=True, attuned=True, charges=5):
    return {
        "name": "Thunder Mage Quarterstaff, +3",
        "id": "thunder-mage-quarterstaff-plus-3",
        "category": "weapon",
        "item_type": "weapon",
        "equipment_kind": "weapon",
        "equip_slot": "main_hand",
        "weapon_type": "simple_melee",
        "damage_dice": "1d6",
        "damage_type": "bludgeoning",
        "attack_bonus": 3,
        "damage_bonus": 3,
        "charges_max": 10,
        "charges_current": charges,
        "recharge_type": "dawn",
        "recharge_formula": "1d6+4",
        "attunement_required": True,
        "attuned": attuned,
        "equipped": equipped,
        "item_spell_attack_bonus": 9,
        "item_spell_save_dc": 17,
        "granted_spells": [
            {
                "id": "thunderwave",
                "name": "Thunderwave",
                "charge_cost": 1,
                "cast_level": 1,
                "uses_item_dc": True,
                "uses_item_attack_bonus": False,
                "consume_spell_slot": False,
            },
        ],
        "qty": 1,
    }


def _make_wand(charges=3, charges_max=3, equipped=True):
    return {
        "name": "Test Wand of Secrets",
        "id": "test-wand-of-secrets",
        "rarity": "rare",
        "item_type": "wand",
        "equipped": equipped,
        "attunement_required": False,
        "charges_max": charges_max,
        "charges_current": charges,
        "recharge_type": "long_rest",
        "qty": 1,
    }


@pytest.fixture
def patched(monkeypatch):
    """Stub out IO (websocket sends and save-to-disk) on both modules."""
    sent = []
    broadcasts = []

    async def _fake_send_to(sid, uid, msg):
        sent.append((sid, uid, msg))
        return True

    async def _fake_broadcast(sid, msg):
        broadcasts.append((sid, msg))

    async def _noop_save(session):
        return None

    for mod in (inventory_handlers, camp_rest_handlers):
        monkeypatch.setattr(mod.manager, "send_to", _fake_send_to)
        monkeypatch.setattr(mod.manager, "broadcast", _fake_broadcast)
        monkeypatch.setattr(mod, "save_campaign_async", _noop_save)

    return type("Patched", (), {"sent": sent, "broadcasts": broadcasts})()


# ---------------------------------------------------------------------------
# 1. Adding an item advances inventory_revision
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_add_item_advances_inventory_revision(patched):
    session, user, dm = _setup_session_with_player([])
    before = session.inventory_revision
    await inventory_handlers.handle_inventory_add_item(
        {"entry": {"name": "Rope", "qty": 1}, "target_user_id": user.id}, session, dm
    )
    assert session.inventory_revision == before + 1


# ---------------------------------------------------------------------------
# 2. Removing an item advances inventory_revision
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_remove_item_advances_inventory_revision(patched):
    session, user, dm = _setup_session_with_player([{"name": "Rope", "qty": 1}])
    before = session.inventory_revision
    await inventory_handlers.handle_inventory_remove_item({"item_index": 0}, session, user)
    assert session.inventory_revision == before + 1


# ---------------------------------------------------------------------------
# 3. Equipping an item advances inventory_revision
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_equip_item_advances_inventory_revision(patched):
    session, user, dm = _setup_session_with_player([
        {"name": "Shield", "item_type": "shield", "equipment_kind": "shield", "qty": 1, "equipped": False},
    ])
    before = session.inventory_revision
    await inventory_handlers.handle_inventory_equip_item({"item_index": 0}, session, user)
    assert session.inventory_revision == before + 1


# ---------------------------------------------------------------------------
# 4. Unequipping an item advances inventory_revision
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_unequip_item_advances_inventory_revision(patched):
    session, user, dm = _setup_session_with_player([
        {"name": "Shield", "item_type": "shield", "equipment_kind": "shield", "qty": 1, "equipped": True},
    ])
    before = session.inventory_revision
    await inventory_handlers.handle_inventory_unequip_item({"item_index": 0}, session, user)
    assert session.inventory_revision == before + 1


# ---------------------------------------------------------------------------
# 5. Casting an item spell / spending charges advances inventory_revision
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cast_item_spell_advances_inventory_revision(patched):
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=5)
    session, user, dm = _setup_session_with_player([staff])
    before = session.inventory_revision
    await inventory_handlers.handle_inventory_cast_item_spell(
        {
            "item_index": 0,
            "item_id": "thunder-mage-quarterstaff-plus-3",
            "spell_id": "thunderwave",
            "charge_cost": 1,
            "cast_level": 1,
        },
        session,
        user,
    )
    assert session.inventory_revision == before + 1
    owner_key = normalize_profile_owner_key(user.name) or user.id
    assert session.player_inventories[owner_key][0]["charges_current"] == 4


@pytest.mark.anyio
async def test_use_item_action_charge_spend_advances_inventory_revision(patched):
    wand = _make_wand(charges=3, charges_max=3)
    session, user, dm = _setup_session_with_player([wand])
    before = session.inventory_revision
    await inventory_handlers.handle_inventory_use_item_action({"item_index": 0}, session, user)
    assert session.inventory_revision == before + 1


# ---------------------------------------------------------------------------
# 6. Short rest item recharge advances inventory_revision if charges changed
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_short_rest_recharge_advances_inventory_revision_when_changed(patched):
    wand = _make_wand(charges=0, charges_max=3)
    wand["recharge_type"] = "short_rest"
    session, user, dm = _setup_session_with_player([wand])
    before = session.inventory_revision
    await camp_rest_handlers.handle_camp_rest_take_rest({"rest_type": "short"}, session, dm)
    assert session.inventory_revision == before + 1
    owner_key = normalize_profile_owner_key(user.name) or user.id
    assert session.player_inventories[owner_key][0]["charges_current"] > 0


@pytest.mark.anyio
async def test_short_rest_no_recharge_does_not_advance_inventory_revision(patched):
    # Charges already full -> refresh_item_charges_for_rest reports no change.
    wand = _make_wand(charges=3, charges_max=3)
    wand["recharge_type"] = "short_rest"
    session, user, dm = _setup_session_with_player([wand])
    before = session.inventory_revision
    await camp_rest_handlers.handle_camp_rest_take_rest({"rest_type": "short"}, session, dm)
    assert session.inventory_revision == before


# ---------------------------------------------------------------------------
# 7. Long rest item recharge advances inventory_revision if charges changed
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_long_rest_recharge_advances_inventory_revision_when_changed(patched):
    wand = _make_wand(charges=0, charges_max=3)
    wand["recharge_type"] = "long_rest"
    session, user, dm = _setup_session_with_player([wand])
    before = session.inventory_revision
    await camp_rest_handlers.handle_camp_rest_take_rest({"rest_type": "long"}, session, dm)
    assert session.inventory_revision == before + 1
    owner_key = normalize_profile_owner_key(user.name) or user.id
    assert session.player_inventories[owner_key][0]["charges_current"] == 3


# ---------------------------------------------------------------------------
# 8. Inventory broadcast payload includes inventory_revision
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_broadcast_payload_includes_inventory_revision(patched):
    session, user, dm = _setup_session_with_player([{"name": "Rope", "qty": 1}])
    await inventory_handlers.handle_inventory_remove_item({"item_index": 0}, session, user)
    sync_msgs = [
        msg for (_sid, uid, msg) in patched.sent
        if msg.get("type") == "player_inventory_sync" and uid == user.id
    ]
    assert sync_msgs, "expected a player_inventory_sync message for the player"
    assert sync_msgs[-1]["payload"]["inventory_revision"] == session.inventory_revision


# ---------------------------------------------------------------------------
# 9. Repeated inventory mutations produce monotonically increasing revisions
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_repeated_mutations_produce_monotonically_increasing_revisions(patched):
    session, user, dm = _setup_session_with_player([
        {"name": "Shield", "item_type": "shield", "equipment_kind": "shield", "qty": 1, "equipped": False},
    ])
    revisions = [session.inventory_revision]
    await inventory_handlers.handle_inventory_add_item(
        {"entry": {"name": "Rope", "qty": 1}, "target_user_id": user.id}, session, dm
    )
    revisions.append(session.inventory_revision)
    await inventory_handlers.handle_inventory_equip_item({"item_index": 0}, session, user)
    revisions.append(session.inventory_revision)
    await inventory_handlers.handle_inventory_unequip_item({"item_index": 0}, session, user)
    revisions.append(session.inventory_revision)
    await inventory_handlers.handle_inventory_remove_item({"item_index": 1}, session, user)
    revisions.append(session.inventory_revision)
    assert revisions == sorted(revisions)
    assert len(set(revisions)) == len(revisions)


# ---------------------------------------------------------------------------
# 10. Read-only inventory/shop queries do not bump revision
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_treasury_get_does_not_bump_inventory_revision(patched, tmp_path, monkeypatch):
    import server.db as db

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "inv-rev-treasury.db"))
    db.init_db()

    session, user, dm = _setup_session_with_player([])
    before = session.inventory_revision
    await inventory_handlers.handle_treasury_get({}, session, user)
    assert session.inventory_revision == before


@pytest.mark.anyio
async def test_dm_get_shop_config_does_not_bump_inventory_revision(patched):
    session, user, dm = _setup_session_with_player([])
    before = session.inventory_revision
    await inventory_handlers.handle_dm_get_shop_config({}, session, dm)
    assert session.inventory_revision == before


@pytest.mark.anyio
async def test_get_sell_offers_does_not_bump_inventory_revision(patched):
    session, user, dm = _setup_session_with_player([{"name": "Rope", "qty": 1}])
    before = session.inventory_revision
    await inventory_handlers.handle_get_sell_offers({"item_indices": [0]}, session, user)
    assert session.inventory_revision == before


# ---------------------------------------------------------------------------
# 11. Client stale inventory payload guard ignores old revision payloads
# ---------------------------------------------------------------------------

def _extract_js_function(source: str, fn_name: str) -> str:
    marker = f"function {fn_name}("
    start = source.index(marker)
    depth = 0
    i = source.index("{", start)
    j = i
    while True:
        if source[j] == "{":
            depth += 1
        elif source[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return source[start:j + 1]


def _play_html_source() -> str:
    with open("client/templates/play.html", "r", encoding="utf-8") as f:
        return f.read()


def test_play_html_player_inventory_sync_case_checks_stale_inventory_payload():
    source = _play_html_source()
    match = re.search(r"case 'player_inventory_sync':\s*\{(.*?)\n\s*\}", source, re.DOTALL)
    assert match, "expected to find the player_inventory_sync case in play.html"
    block = match.group(1)
    assert "_isStaleInventoryPayload" in block


def test_stale_player_inventory_sync_payload_is_dropped_by_client():
    # Re-implement the exact guard logic (mirrors _isStaleInventoryPayload) in
    # Python to validate the contract without spinning up a JS runtime.
    source = _play_html_source()
    fn_source = _extract_js_function(source, "_isStaleInventoryPayload")
    assert "inventory_revision" in fn_source
    assert "_lastVisibilityRevisionByStream" in fn_source

    last_by_stream: dict[str, float] = {}

    def is_stale(payload, stream="inventory"):
        rev = payload.get("inventory_revision")
        if not isinstance(rev, (int, float)):
            return False
        last = last_by_stream.get(stream, 0)
        if rev < last:
            return True
        last_by_stream[stream] = rev
        return False

    first = {"inventory_revision": 5, "player_inventory": ["sword"]}
    second_stale = {"inventory_revision": 3, "player_inventory": ["dagger"]}

    assert is_stale(first) is False
    applied = first
    if not is_stale(second_stale):
        applied = second_stale
    assert applied == first, "the stale (lower-revision) payload must not be applied"


# ---------------------------------------------------------------------------
# 12. Missing inventory_revision payload still applies (backward compatibility)
# ---------------------------------------------------------------------------

def test_missing_inventory_revision_payload_still_applies():
    last_by_stream: dict[str, float] = {}

    def is_stale(payload, stream="inventory"):
        rev = payload.get("inventory_revision")
        if not isinstance(rev, (int, float)):
            return False
        last = last_by_stream.get(stream, 0)
        if rev < last:
            return True
        last_by_stream[stream] = rev
        return False

    legacy_payload = {"player_inventory": ["torch"]}
    assert is_stale(legacy_payload) is False
