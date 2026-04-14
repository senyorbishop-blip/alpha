import pytest

from server.handlers import inventory as inventory_handlers
from server.session import Session, User, normalize_profile_owner_key


def _setup_session_with_player(items):
    session = Session(id="s-item-actions")
    user = User(id="u-item", name="Item Hero", role="player")
    dm = User(id="u-dm", name="DM", role="dm")
    session.users[user.id] = user
    session.users[dm.id] = dm
    owner_key = normalize_profile_owner_key(user.name) or user.id
    session.player_inventories = {owner_key: items}
    session.char_profiles = {
        owner_key: [{
            "id": "profile-1",
            "name": user.name,
            "updated_at": 1.0,
            "charBook": {"abilities": {"dex": {"score": 14}}, "classes": [{"name": "wizard", "level": 5}]},
            "charSheet": {},
        }]
    }
    return session, user


def test_derives_potion_and_scroll_actions_from_legacy_items():
    items = [
        {"name": "Potion of Healing", "item_type": "potion", "qty": 2, "effect": "Regain 2d4+2 hit points when you drink this potion."},
        {"name": "Spell Scroll (2nd Level)", "item_type": "scroll", "qty": 1, "effect": "Cast the inscribed 2nd-level spell without spending a spell slot."},
    ]
    actions, passives = inventory_handlers._derive_item_actions_and_passives(items)
    assert len(actions) == 2
    assert not passives
    potion = next(row for row in actions if row["item_name"] == "Potion of Healing")
    assert potion["consumable"] is True
    assert potion["healing_formula"] == "2d4+2"
    scroll = next(row for row in actions if row["item_name"].startswith("Spell Scroll"))
    assert scroll["consumed_on_use"] is True


def test_ring_of_protection_passive_bonus_applies_once_to_ac():
    session, user = _setup_session_with_player([
        {"name": "Ring of Protection", "item_type": "ring", "attunement_required": True, "attuned": True, "equipped": True, "qty": 1},
    ])
    ac = inventory_handlers._calculate_ac_for_user(session, user, session.player_inventories[next(iter(session.player_inventories))])
    assert ac == 13  # base 10 + dex 2 + ring passive 1


@pytest.mark.anyio
async def test_use_potion_consumes_and_removes_when_empty(monkeypatch):
    session, user = _setup_session_with_player([
        {"name": "Potion of Healing", "item_type": "potion", "qty": 1, "effect": "Regain 2d4+2 hit points when you drink this potion."},
    ])
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    async def _broadcast(_sid, msg):
        sent.append(msg)

    async def _save(_session):
        return None

    monkeypatch.setattr(inventory_handlers.manager, "send_to", _send_to)
    monkeypatch.setattr(inventory_handlers.manager, "broadcast", _broadcast)
    monkeypatch.setattr(inventory_handlers, "save_campaign_async", _save)

    await inventory_handlers.handle_inventory_use_item_action({"item_index": 0}, session, user)

    owner_key = normalize_profile_owner_key(user.name) or user.id
    assert session.player_inventories[owner_key] == []
    assert any(msg.get("type") == "inventory_item_used" for msg in sent)


@pytest.mark.anyio
async def test_wand_with_zero_charges_is_blocked(monkeypatch):
    session, user = _setup_session_with_player([
        {
            "name": "Wand of Magic Missiles",
            "item_type": "wand",
            "qty": 1,
            "charges_max": 7,
            "charges_current": 0,
            "grants_action": True,
            "usage_cost": 1,
            "effect": "Has 7 charges. Expend 1–3 charges to cast magic missile at 1st–3rd level.",
        },
    ])
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    monkeypatch.setattr(inventory_handlers.manager, "send_to", _send_to)

    await inventory_handlers.handle_inventory_use_item_action({"item_index": 0}, session, user)

    last = sent[-1]
    assert last["type"] == "inventory_action_result"
    assert "charge" in str(last["payload"].get("message", "")).lower()


def test_long_rest_recharges_wand_charges():
    session, user = _setup_session_with_player([
        {
            "name": "Wand of Web",
            "item_type": "wand",
            "qty": 1,
            "charges_max": 7,
            "charges_current": 1,
            "recharge_type": "dawn",
            "recharge_formula": "1d6+1",
        },
    ])
    updates = inventory_handlers.refresh_item_charges_for_rest(session, user, "long")
    owner_key = normalize_profile_owner_key(user.name) or user.id
    item = session.player_inventories[owner_key][0]
    assert updates
    assert item["charges_current"] >= 2
    assert item["charges_current"] <= 7


def test_non_structured_item_still_normalizes_without_breaking():
    item = inventory_handlers._normalize_player_inventory_entry({"name": "Old Rope", "qty": 2, "notes": "legacy"})
    assert item is not None
    assert item["name"] == "Old Rope"
    assert item["qty"] == 2
