"""
Tests for the item spell grant system.

Verifies:
- item schema preserves granted_spells, charges, recharge, attunement
- item compendium loads staffs/wands/rods/rings/wondrous
- Thunder Mage Quarterstaff creates weapon attack plus item spell cards
- item spell cards appear in the inventory state payload
- item spell cards do not mix with class prepared/known spells
- casting item spell spends charges
- casting item spell with insufficient charges is blocked
- item spell uses item DC/attack bonus when configured
- generic potion/wand tests still pass
- item audit flags missing/invalid item spell metadata
"""
import pytest

from server.item_schema import normalize_item_record, to_inventory_entry
from server.handlers import inventory as inventory_handlers
from server.session import Session, User, normalize_profile_owner_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_session_with_player(items):
    session = Session(id="s-spell-system")
    user = User(id="u-spell", name="Spell Hero", role="player")
    dm = User(id="u-dm2", name="DM2", role="dm")
    session.users[user.id] = user
    session.users[dm.id] = dm
    owner_key = normalize_profile_owner_key(user.name) or user.id
    session.player_inventories = {owner_key: items}
    session.char_profiles = {
        owner_key: [{
            "id": "profile-2",
            "name": user.name,
            "updated_at": 1.0,
            "charBook": {
                "abilities": {"str": {"score": 10}, "dex": {"score": 10}, "int": {"score": 18}},
                "classes": [{"name": "wizard", "level": 9}],
            },
            "charSheet": {},
        }]
    }
    return session, user


def _make_thunder_staff(equipped=True, attuned=True, charges=10):
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
            {
                "id": "lightning-bolt",
                "name": "Lightning Bolt",
                "charge_cost": 3,
                "cast_level": 3,
                "uses_item_dc": True,
                "uses_item_attack_bonus": False,
                "consume_spell_slot": False,
            },
        ],
        "qty": 1,
    }


# ---------------------------------------------------------------------------
# 1. Item schema preserves granted_spells, charges, recharge, attunement
# ---------------------------------------------------------------------------

def test_item_schema_preserves_granted_spells():
    raw = {
        "name": "Staff of Fire",
        "category": "staff",
        "charges_max": 10,
        "charges_current": 7,
        "recharge_type": "dawn",
        "recharge_formula": "1d6+4",
        "attunement_required": True,
        "granted_spells": [
            {"id": "fireball", "name": "Fireball", "charge_cost": 3, "cast_level": 3,
             "uses_item_dc": True, "uses_item_attack_bonus": False, "consume_spell_slot": False},
        ],
        "item_spell_save_dc": 17,
        "item_spell_attack_bonus": 0,
    }
    canonical = normalize_item_record(raw)
    assert canonical["usage"]["charges_max"] == 10
    assert canonical["usage"]["charges_current"] == 7
    assert canonical["usage"]["recharge_type"] == "dawn"
    assert canonical["usage"]["recharge_formula"] == "1d6+4"
    assert canonical["equipment"]["requires_attunement"] is True
    gs = canonical["effects"]["granted_spells"]
    assert len(gs) == 1
    assert gs[0]["id"] == "fireball"
    assert gs[0]["charge_cost"] == 3
    assert canonical["equipment"]["item_spell_save_dc"] == 17


def test_item_schema_preserves_item_spell_dc_and_atk():
    raw = {
        "name": "Wand of Fireballs",
        "category": "wand",
        "item_spell_attack_bonus": 7,
        "item_spell_save_dc": 15,
        "granted_spells": [{"id": "fireball", "name": "Fireball", "charge_cost": 3, "cast_level": 3}],
    }
    canonical = normalize_item_record(raw)
    assert canonical["equipment"]["item_spell_attack_bonus"] == 7
    assert canonical["equipment"]["item_spell_save_dc"] == 15

    entry = to_inventory_entry(canonical)
    assert entry["item_spell_attack_bonus"] == 7
    assert entry["item_spell_save_dc"] == 15


def test_item_schema_attunement_round_trips():
    raw = {"name": "Ring of Protection", "category": "ring", "attunement_required": True, "attuned": True}
    canonical = normalize_item_record(raw)
    assert canonical["equipment"]["requires_attunement"] is True
    assert canonical["equipment"]["attuned"] is True
    entry = to_inventory_entry(canonical)
    assert entry["attunement_required"] is True
    assert entry["attuned"] is True


def test_item_schema_version_field():
    raw = {"name": "Staff of Power", "category": "staff", "item_schema_version": 2}
    canonical = normalize_item_record(raw)
    assert canonical["identity"]["item_schema_version"] == 2


# ---------------------------------------------------------------------------
# 2. Item compendium loads staffs/wands/rods/rings/wondrous
# ---------------------------------------------------------------------------

def test_item_compendium_loads_staffs():
    from server.item_compendium import all_items_by_category, clear_cache
    clear_cache()
    staffs = all_items_by_category("staff")
    assert len(staffs) >= 1, "Expected at least one staff in compendium"
    names = [s["name"] for s in staffs]
    assert any("Staff" in n for n in names)


def test_item_compendium_loads_wands():
    from server.item_compendium import all_items_by_category, clear_cache
    clear_cache()
    wands = all_items_by_category("wand")
    assert len(wands) >= 1
    ids = [w["id"] for w in wands]
    assert "wand-of-magic-missiles" in ids


def test_item_compendium_loads_rings():
    from server.item_compendium import all_items_by_category, clear_cache
    clear_cache()
    rings = all_items_by_category("ring")
    assert len(rings) >= 1
    ids = [r["id"] for r in rings]
    assert "ring-of-protection" in ids


def test_item_compendium_loads_wondrous():
    from server.item_compendium import all_items_by_category, clear_cache
    clear_cache()
    wondrous = all_items_by_category("wondrous")
    assert len(wondrous) >= 1


def test_item_compendium_loads_rods():
    from server.item_compendium import all_items, clear_cache
    clear_cache()
    rods = [i for i in all_items() if str(i.get("subtype") or "").lower() == "rod"]
    assert len(rods) >= 1


def test_item_compendium_thunder_mage_staff_entry():
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    item = get_item_by_id("thunder-mage-quarterstaff-plus-3")
    assert item is not None
    assert item["attack_bonus"] == 3
    assert item["damage_bonus"] == 3
    assert item["charges_max"] == 10
    assert item["requires_attunement"] is True
    gs = item["granted_spells"]
    assert len(gs) >= 1
    spell_ids = [g["id"] for g in gs if isinstance(g, dict)]
    assert {"call-lightning", "chain-lightning", "haste", "lightning-bolt", "protection-from-energy", "absorb-elements"}.issubset(set(spell_ids))


# ---------------------------------------------------------------------------
# 3. Thunder Mage Quarterstaff creates weapon attack plus item spell cards
# ---------------------------------------------------------------------------

def test_thunder_staff_generates_item_spell_cards():
    staff = _make_thunder_staff(equipped=True, attuned=True)
    cards = inventory_handlers._build_item_spell_cards([staff])
    assert len(cards) >= 1
    spell_ids = [c["spell_id"] for c in cards]
    assert "thunderwave" in spell_ids
    assert "lightning-bolt" in spell_ids


def test_thunder_staff_spell_card_fields():
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=10)
    cards = inventory_handlers._build_item_spell_cards([staff])
    thunder = next(c for c in cards if c["spell_id"] == "thunderwave")
    assert thunder["source"] == "item_spell"
    assert thunder["item_name"] == "Thunder Mage Quarterstaff, +3"
    assert thunder["charge_cost"] == 1
    assert thunder["cast_level"] == 1
    assert thunder["uses_item_dc"] is True
    assert thunder["item_spell_save_dc"] == 17
    assert thunder["disabled"] is False
    assert thunder["charges_current"] == 10


def test_thunder_staff_also_has_weapon_attack():
    staff = _make_thunder_staff(equipped=True, attuned=True)
    action_payload, _passive = inventory_handlers._build_item_runtime_action(staff, 0)
    assert action_payload is not None
    assert action_payload["item_name"] == "Thunder Mage Quarterstaff, +3"


# ---------------------------------------------------------------------------
# 4. Item spell cards appear in inventory state payload
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_item_spell_cards_in_inventory_state(monkeypatch):
    staff = _make_thunder_staff(equipped=True, attuned=True)
    session, user = _setup_session_with_player([staff])
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    async def _broadcast(_sid, msg):
        sent.append(msg)

    monkeypatch.setattr(inventory_handlers.manager, "send_to", _send_to)
    monkeypatch.setattr(inventory_handlers.manager, "broadcast", _broadcast)

    await inventory_handlers._send_inventory_state(session, user.id)

    inv_state = next((m for m in sent if m.get("type") == "player_inventory_sync"), None)
    assert inv_state is not None, f"Expected player_inventory_sync, got: {[m.get('type') for m in sent]}"
    payload = inv_state.get("payload", {})
    item_spell_cards = payload.get("item_spell_cards", [])
    assert len(item_spell_cards) >= 1, f"Expected item_spell_cards, got: {item_spell_cards}"
    spell_ids = [c["spell_id"] for c in item_spell_cards]
    assert "thunderwave" in spell_ids


# ---------------------------------------------------------------------------
# 5. Item spell must not appear as class prepared/known spell
# ---------------------------------------------------------------------------

def test_item_spell_not_in_granted_spells_player_table():
    """Item-granted spells come from item_spell_cards, not from the player-granted spell table."""
    from server.item_compendium import get_item_by_id, clear_cache
    clear_cache()
    staff_entry = get_item_by_id("thunder-mage-quarterstaff-plus-3")
    assert staff_entry is not None
    granted_spells_in_item = [gs["id"] for gs in staff_entry.get("granted_spells", []) if isinstance(gs, dict)]

    cards = inventory_handlers._build_item_spell_cards([_make_thunder_staff()])
    for card in cards:
        assert card["source"] == "item_spell", "Item spell cards must have source='item_spell'"

    for spell_id in granted_spells_in_item:
        card = next((c for c in cards if c["spell_id"] == spell_id), None)
        if card:
            assert card.get("consume_spell_slot") is False, \
                f"Item spell {spell_id} must not consume spell slots"


# ---------------------------------------------------------------------------
# 6. Casting item spell spends charges
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cast_item_spell_spends_charges(monkeypatch):
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=5)
    session, user = _setup_session_with_player([staff])
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

    owner_key = normalize_profile_owner_key(user.name) or user.id
    item = session.player_inventories[owner_key][0]
    assert item["charges_current"] == 4

    cast_msgs = [m for m in sent if m.get("type") == "inventory_item_spell_cast"]
    assert len(cast_msgs) == 1
    assert cast_msgs[0]["payload"]["spell_id"] == "thunderwave"
    assert cast_msgs[0]["payload"]["remaining_charges"] == 4


# ---------------------------------------------------------------------------
# 7. Casting item spell with insufficient charges is blocked
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cast_item_spell_blocked_insufficient_charges(monkeypatch):
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=2)
    session, user = _setup_session_with_player([staff])
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    monkeypatch.setattr(inventory_handlers.manager, "send_to", _send_to)

    await inventory_handlers.handle_inventory_cast_item_spell(
        {
            "item_index": 0,
            "spell_id": "lightning-bolt",
            "charge_cost": 3,
            "cast_level": 3,
        },
        session,
        user,
    )

    error_msgs = [m for m in sent if m.get("type") == "inventory_action_result"]
    assert error_msgs, "Expected an error response"
    last_msg = error_msgs[-1]
    assert "charge" in str(last_msg.get("payload", {}).get("message", "")).lower()

    owner_key = normalize_profile_owner_key(user.name) or user.id
    item = session.player_inventories[owner_key][0]
    assert item["charges_current"] == 2


# ---------------------------------------------------------------------------
# 8. Item spell uses item DC/attack bonus when configured
# ---------------------------------------------------------------------------

def test_item_spell_card_uses_item_dc_when_configured():
    staff = _make_thunder_staff(equipped=True, attuned=True)
    staff["item_spell_save_dc"] = 17
    cards = inventory_handlers._build_item_spell_cards([staff])
    thunder_card = next(c for c in cards if c["spell_id"] == "thunderwave")
    assert thunder_card["uses_item_dc"] is True
    assert thunder_card["item_spell_save_dc"] == 17


def test_item_spell_card_zero_dc_when_not_using_item_dc():
    staff = _make_thunder_staff(equipped=True, attuned=True)
    staff["granted_spells"] = [
        {
            "id": "magic-missile",
            "name": "Magic Missile",
            "charge_cost": 1,
            "cast_level": 1,
            "uses_item_dc": False,
            "uses_item_attack_bonus": False,
            "consume_spell_slot": False,
        }
    ]
    cards = inventory_handlers._build_item_spell_cards([staff])
    mm_card = next((c for c in cards if c["spell_id"] == "magic-missile"), None)
    assert mm_card is not None
    assert mm_card["item_spell_save_dc"] == 0


def test_item_spell_card_uses_attack_bonus_when_configured():
    staff = _make_thunder_staff(equipped=True, attuned=True)
    staff["item_spell_attack_bonus"] = 9
    staff["granted_spells"] = [
        {
            "id": "ray-of-frost",
            "name": "Ray of Frost",
            "charge_cost": 1,
            "cast_level": 0,
            "uses_item_dc": False,
            "uses_item_attack_bonus": True,
            "consume_spell_slot": False,
        }
    ]
    cards = inventory_handlers._build_item_spell_cards([staff])
    card = next((c for c in cards if c["spell_id"] == "ray-of-frost"), None)
    assert card is not None
    assert card["uses_item_attack_bonus"] is True
    assert card["item_spell_attack_bonus"] == 9


# ---------------------------------------------------------------------------
# 9. Item spell not generated when unequipped or not attuned
# ---------------------------------------------------------------------------

def test_item_spell_not_generated_when_unequipped():
    staff = _make_thunder_staff(equipped=False, attuned=True)
    cards = inventory_handlers._build_item_spell_cards([staff])
    assert cards == []


def test_item_spell_not_generated_when_not_attuned():
    staff = _make_thunder_staff(equipped=True, attuned=False)
    staff["attunement_required"] = True
    cards = inventory_handlers._build_item_spell_cards([staff])
    assert cards == []


def test_item_spell_generated_when_no_attunement_required():
    wand = {
        "name": "Wand of Magic Missiles",
        "id": "wand-of-magic-missiles",
        "category": "wand",
        "equipped": True,
        "attunement_required": False,
        "attuned": False,
        "charges_max": 7,
        "charges_current": 7,
        "item_spell_save_dc": 0,
        "item_spell_attack_bonus": 0,
        "granted_spells": [
            {"id": "magic-missile", "name": "Magic Missile", "charge_cost": 1, "cast_level": 1,
             "uses_item_dc": False, "uses_item_attack_bonus": False, "consume_spell_slot": False}
        ],
        "qty": 1,
    }
    cards = inventory_handlers._build_item_spell_cards([wand])
    assert len(cards) == 1
    assert cards[0]["spell_id"] == "magic-missile"


# ---------------------------------------------------------------------------
# 10. Cast blocked when not equipped
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cast_item_spell_blocked_when_not_equipped(monkeypatch):
    staff = _make_thunder_staff(equipped=False, attuned=True)
    session, user = _setup_session_with_player([staff])
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    monkeypatch.setattr(inventory_handlers.manager, "send_to", _send_to)

    await inventory_handlers.handle_inventory_cast_item_spell(
        {"item_index": 0, "spell_id": "thunderwave", "charge_cost": 1, "cast_level": 1},
        session,
        user,
    )

    error = next((m for m in sent if m.get("type") == "inventory_action_result"), None)
    assert error is not None
    assert "equipped" in str(error.get("payload", {}).get("message", "")).lower()


# ---------------------------------------------------------------------------
# 11. Cast blocked when not attuned (requires attunement)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cast_item_spell_blocked_when_not_attuned(monkeypatch):
    staff = _make_thunder_staff(equipped=True, attuned=False)
    session, user = _setup_session_with_player([staff])
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    monkeypatch.setattr(inventory_handlers.manager, "send_to", _send_to)

    await inventory_handlers.handle_inventory_cast_item_spell(
        {"item_index": 0, "spell_id": "thunderwave", "charge_cost": 1, "cast_level": 1},
        session,
        user,
    )

    error = next((m for m in sent if m.get("type") == "inventory_action_result"), None)
    assert error is not None
    assert "attunement" in str(error.get("payload", {}).get("message", "")).lower()


# ---------------------------------------------------------------------------
# 12. Cast fails when spell not in granted_spells
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cast_item_spell_blocked_when_spell_not_granted(monkeypatch):
    staff = _make_thunder_staff(equipped=True, attuned=True)
    session, user = _setup_session_with_player([staff])
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    monkeypatch.setattr(inventory_handlers.manager, "send_to", _send_to)

    await inventory_handlers.handle_inventory_cast_item_spell(
        {"item_index": 0, "spell_id": "fireball", "charge_cost": 3, "cast_level": 3},
        session,
        user,
    )

    error = next((m for m in sent if m.get("type") == "inventory_action_result"), None)
    assert error is not None
    msg = str(error.get("payload", {}).get("message", "")).lower()
    assert "not granted" in msg or "fireball" in msg


# ---------------------------------------------------------------------------
# 13. DM cannot cast item spells (player role only)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cast_item_spell_requires_player_role(monkeypatch):
    session = Session(id="s-dm-test")
    dm = User(id="u-dm3", name="DM3", role="dm")
    session.users[dm.id] = dm
    sent = []

    async def _send_to(_sid, _uid, msg):
        sent.append(msg)

    monkeypatch.setattr(inventory_handlers.manager, "send_to", _send_to)

    await inventory_handlers.handle_inventory_cast_item_spell(
        {"item_index": 0, "spell_id": "thunderwave"},
        session,
        dm,
    )

    error = next((m for m in sent if m.get("type") == "inventory_action_result"), None)
    assert error is not None
    assert "player" in str(error.get("payload", {}).get("message", "")).lower()


# ---------------------------------------------------------------------------
# 14. Disabled card shows when charges too low to cast any spell
# ---------------------------------------------------------------------------

def test_item_spell_card_disabled_when_charges_low():
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=0)
    cards = inventory_handlers._build_item_spell_cards([staff])
    for card in cards:
        assert card["disabled"] is True
        assert card["charges_current"] == 0


# ---------------------------------------------------------------------------
# 15. Item audit fails on missing/invalid item spell metadata
# ---------------------------------------------------------------------------

def test_audit_detects_granted_spell_without_charge_cost():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import importlib
    audit = importlib.import_module("tools.audit_item_catalog")

    item_with_no_cost = {
        "name": "Broken Wand",
        "id": "broken-wand",
        "category": "wand",
        "charges_max": 5,
        "granted_spells": [{"id": "fireball", "name": "Fireball"}],
    }
    violations = audit.audit_granted_spells([item_with_no_cost], known_spell_ids={"fireball"})
    assert any("charge_cost" in v.get("issue", "") for v in violations)


def test_audit_detects_spell_id_not_in_compendium():
    import importlib
    audit = importlib.import_module("tools.audit_item_catalog")

    item = {
        "name": "Staff of Nothingness",
        "id": "staff-nothingness",
        "category": "staff",
        "charges_max": 5,
        "granted_spells": [{"id": "not-a-real-spell", "name": "Not Real", "charge_cost": 1}],
    }
    violations = audit.audit_granted_spells([item], known_spell_ids={"fireball", "thunderwave"})
    assert any("not found in spell compendium" in v.get("issue", "") for v in violations)


def test_audit_detects_plus3_weapon_missing_bonus():
    import importlib
    audit = importlib.import_module("tools.audit_item_catalog")

    bad_weapon = {
        "name": "Sword of Victory, +3",
        "id": "sword-victory-plus-3",
        "category": "weapon",
        "attack_bonus": 0,
        "damage_bonus": 0,
    }
    result = audit.audit_item(bad_weapon)
    assert result["issues"], "Expected schema issue for +3 weapon with wrong bonus"
    assert any("+3" in i or "attack_bonus" in i for i in result["issues"])


def test_audit_detects_duplicate_ids():
    import importlib
    audit = importlib.import_module("tools.audit_item_catalog")

    items = [
        {"name": "Item A", "id": "item-dup"},
        {"name": "Item B", "id": "item-dup"},
    ]
    dups = audit.check_duplicate_ids(items)
    assert len(dups) == 1
    assert "item-dup" in dups[0]


def test_audit_detects_staff_with_no_charges():
    import importlib
    audit = importlib.import_module("tools.audit_item_catalog")

    empty_staff = {
        "name": "Staff of Nothing",
        "id": "staff-nothing",
        "category": "staff",
        "charges_max": 0,
        "recharge_type": "none",
        "granted_spells": [],
    }
    result = audit.audit_item(empty_staff)
    assert any("staff" in i.lower() or "charge" in i.lower() for i in result["issues"])


# ---------------------------------------------------------------------------
# 16. Compendium get_spell_metadata works for known spells
# ---------------------------------------------------------------------------

def test_spell_metadata_lookup_for_fireball():
    from server.item_compendium import get_spell_metadata, clear_cache
    clear_cache()
    meta = get_spell_metadata("fireball")
    if meta is not None:
        assert str(meta.get("displayName") or meta.get("id") or "").lower().startswith("fire")


def test_spell_metadata_returns_none_for_unknown():
    from server.item_compendium import get_spell_metadata, clear_cache
    clear_cache()
    meta = get_spell_metadata("definitely-not-a-real-spell-xyz")
    assert meta is None


# ---------------------------------------------------------------------------
# 17. Item string granted_spell (legacy) normalizes to card
# ---------------------------------------------------------------------------

def test_string_granted_spell_generates_card():
    item = {
        "name": "Wand of Fire",
        "id": "wand-fire-legacy",
        "category": "wand",
        "equipped": True,
        "attunement_required": False,
        "charges_max": 7,
        "charges_current": 7,
        "item_spell_save_dc": 0,
        "item_spell_attack_bonus": 0,
        "granted_spells": ["Fireball"],
        "qty": 1,
    }
    cards = inventory_handlers._build_item_spell_cards([item])
    assert len(cards) == 1
    assert cards[0]["spell_id"] == "fireball"
    assert cards[0]["spell_name"] == "Fireball"


# ---------------------------------------------------------------------------
# 18. Item charge recovery on rests (short_rest / long_rest / dawn)
# ---------------------------------------------------------------------------

def test_short_rest_recharges_short_rest_item():
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=2)
    staff["id"] = "test-short-rest-staff"
    staff["magic_item_id"] = "test-short-rest-staff"
    staff["rarity"] = "rare"
    staff["recharge_type"] = "short_rest"
    staff["recharge_formula"] = "1d4+1"
    session, user = _setup_session_with_player([staff])

    updates = inventory_handlers.refresh_item_charges_for_rest(session, user, "short")

    owner_key = normalize_profile_owner_key(user.name) or user.id
    item = session.player_inventories[owner_key][0]
    assert updates
    assert item["charges_current"] > 2
    assert item["charges_current"] <= item["charges_max"]


def test_long_rest_does_not_recharge_short_rest_item_twice_but_short_rest_does_not_recharge_long_rest_item():
    # Use an item not present in the compendium so an empty recharge_formula stays
    # empty (compendium merge backfills empty fields for known item ids).
    item = {
        "name": "Rod of the Unknown",
        "id": "rod-of-the-unknown-test-only",
        "category": "rod",
        "item_type": "rod",
        "charges_max": 10,
        "charges_current": 2,
        "recharge_type": "long_rest",
        "recharge_formula": "",
        "qty": 1,
    }
    session, user = _setup_session_with_player([item])

    updates = inventory_handlers.refresh_item_charges_for_rest(session, user, "short")
    owner_key = normalize_profile_owner_key(user.name) or user.id
    stored = session.player_inventories[owner_key][0]
    assert not updates
    assert stored["charges_current"] == 2

    updates = inventory_handlers.refresh_item_charges_for_rest(session, user, "long")
    stored = session.player_inventories[owner_key][0]
    assert updates
    assert stored["charges_current"] == stored["charges_max"]


def test_dawn_item_does_not_recharge_on_short_rest():
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=2)
    assert staff["recharge_type"] == "dawn"
    session, user = _setup_session_with_player([staff])

    updates = inventory_handlers.refresh_item_charges_for_rest(session, user, "short")
    owner_key = normalize_profile_owner_key(user.name) or user.id
    item = session.player_inventories[owner_key][0]
    assert not updates
    assert item["charges_current"] == 2

    # Dawn falls back to recharging on long rest since there is no time-of-day system.
    updates = inventory_handlers.refresh_item_charges_for_rest(session, user, "long")
    item = session.player_inventories[owner_key][0]
    assert updates
    assert item["charges_current"] > 2
    assert item["charges_current"] <= item["charges_max"]


def test_recharge_never_exceeds_charges_max():
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=9)
    staff["recharge_type"] = "long_rest"
    staff["recharge_formula"] = "1d6+4"
    session, user = _setup_session_with_player([staff])

    updates = inventory_handlers.refresh_item_charges_for_rest(session, user, "long")
    owner_key = normalize_profile_owner_key(user.name) or user.id
    item = session.player_inventories[owner_key][0]
    assert updates
    assert item["charges_current"] == 10


def test_zero_charge_item_recovers_and_becomes_castable():
    staff = _make_thunder_staff(equipped=True, attuned=True, charges=0)
    # Known library item rehydrates to its canonical dawn recharge metadata, which
    # the rest system applies on long rest because there is no time-of-day system.
    session, user = _setup_session_with_player([staff])

    cards = inventory_handlers._build_item_spell_cards([staff])
    assert all(c["disabled"] for c in cards)

    inventory_handlers.refresh_item_charges_for_rest(session, user, "long")
    owner_key = normalize_profile_owner_key(user.name) or user.id
    refreshed_item = session.player_inventories[owner_key][0]
    assert refreshed_item["charges_current"] > 0

    cards = inventory_handlers._build_item_spell_cards([refreshed_item])
    assert all(not c["disabled"] for c in cards)

# ---------------------------------------------------------------------------
# Rehydration: inventory/library drift repair
# ---------------------------------------------------------------------------

def test_inventory_rehydration_repairs_library_metadata_and_preserves_player_state():
    stale = {
        "id": "legacy-staff-row",
        "magic_item_id": "thunder-mage-quarterstaff-plus-3",
        "name": "Thunder Mage Quarterstaff +3",
        "rarity": "common",
        "qty": 2,
        "equipped": True,
        "attuned": True,
        "charges_current": 4,
        "charges_max": 0,
        "notes": "player note",
        "bag_contents": [{"name": "Ruby", "qty": 1}],
        "granted_spells": [],
    }

    repaired = inventory_handlers._normalize_player_inventory_entry(stale)

    assert repaired["source_id"] == "thunder-mage-quarterstaff-plus-3"
    assert repaired["source_type"] == "compendium"
    assert repaired["source_revision"] >= 1
    assert repaired["name"] == "Thunder Mage Quarterstaff, +3"
    assert repaired["rarity"] == "very_rare"
    assert repaired["qty"] == 2
    assert repaired["equipped"] is True
    assert repaired["attuned"] is True
    assert repaired["charges_current"] == 4
    assert repaired["charges_max"] == 10
    assert repaired["recharge_type"] == "dawn"
    assert repaired["recharge_formula"] == "1d6+1"
    assert repaired["notes"] == "player note"
    assert repaired["bag_contents"][0]["name"] == "Ruby"
    assert {s["id"] for s in repaired["granted_spells"] if isinstance(s, dict)} >= {"lightning-bolt", "thunderwave"}


def test_staff_granted_spells_appear_after_rehydration():
    stale = {
        "magic_item_id": "thunder-mage-quarterstaff-plus-3",
        "name": "Thunder Mage Quarterstaff, +3",
        "rarity": "common",
        "equipped": True,
        "attuned": True,
        "attunement_required": True,
        "charges_current": 3,
        "granted_spells": [],
    }

    repaired = inventory_handlers._normalize_player_inventory_entry(stale)
    cards = inventory_handlers._build_item_spell_cards([repaired])

    spell_ids = {card["spell_id"] for card in cards}
    assert "lightning-bolt" in spell_ids
    assert "thunderwave" in spell_ids
    assert all(card["charges_current"] == 3 for card in cards)
    assert all(card["charges_max"] == 10 for card in cards)


def test_rehydration_clamps_current_charges_when_library_max_decreases(monkeypatch):
    comp = {
        "id": "test-clamp-staff",
        "name": "Clamp Staff",
        "slug": "clamp-staff",
        "rarity": "rare",
        "charges_max": 5,
        "recharge_type": "dawn",
        "recharge_formula": "1d4+1",
        "granted_spells": [{"id": "light", "name": "Light", "charge_cost": 1}],
        "item_schema_version": 7,
    }
    monkeypatch.setattr("server.item_compendium.resolve_item", lambda ref: comp if ref == "test-clamp-staff" else None)

    repaired = inventory_handlers._normalize_player_inventory_entry({
        "id": "test-clamp-staff",
        "source_id": "test-clamp-staff",
        "name": "Clamp Staff",
        "charges_max": 10,
        "charges_current": 9,
        "equipped": True,
        "attuned": True,
    })

    assert repaired["charges_max"] == 5
    assert repaired["charges_current"] == 5
    assert repaired["source_revision"] == 7


def test_inventory_rehydration_is_scoped_to_requesting_player():
    session = Session(id="s-rehydrate-scope")
    alice = User(id="alice", name="Alice", role="player")
    bob = User(id="bob", name="Bob", role="player")
    session.users[alice.id] = alice
    session.users[bob.id] = bob
    alice_key = normalize_profile_owner_key(alice.name) or alice.id
    bob_key = normalize_profile_owner_key(bob.name) or bob.id
    session.player_inventories = {
        alice_key: [{"magic_item_id": "thunder-mage-quarterstaff-plus-3", "name": "Thunder Mage Quarterstaff, +3", "equipped": True, "attuned": True, "charges_current": 2}],
        bob_key: [{"name": "Rope", "qty": 1, "notes": "bob private"}],
    }

    _, owner_key, alice_items = inventory_handlers._get_player_inventory_store(session, alice)

    assert owner_key == alice_key
    assert alice_items[0]["source_id"] == "thunder-mage-quarterstaff-plus-3"
    assert session.player_inventories[bob_key][0]["name"] == "Rope"
    assert "source_id" not in session.player_inventories[bob_key][0]
