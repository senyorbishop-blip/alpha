import asyncio
import time

from server.handlers import inventory
from server.session import Session, User, set_player_gold_for_user, get_player_gold_for_user


class _CraftDBStub:
    def __init__(self):
        self.shop = {
            "id": "shop-1",
            "prop_id": "prop-1",
            "shop_type": "alchemist",
            "is_open": 1,
            "name": "Copper Kettle",
        }
        self.recipe = {
            "id": "rec_minor_healing_draught",
            "name": "Minor Healing Draught",
            "result_item_json": {"name": "Minor Healing Draught", "notes": "Crafted", "category": "Consumable", "item_type": "potion", "rarity": "common"},
            "requires_professions_json": ["alchemy"],
            "requires_materials_json": [{"name": "Amberglass Vial", "qty": 1}],
            "fee_units": 120,
            "duration_seconds": 60,
            "station_shop_types_json": ["alchemist"],
            "tags_json": ["starter"],
            "rarity": "common",
        }
        self.jobs = {}

    def get_shop_by_id(self, _shop_id):
        return dict(self.shop)

    def get_crafting_recipe(self, _recipe_id):
        return dict(self.recipe)

    def create_craft_job(self, campaign_id, user_id, recipe_id, shop_id, started_at, ready_at, status, inputs_locked, result_json, logs):
        job = {
            "job_id": f"job-{len(self.jobs) + 1}",
            "campaign_id": campaign_id,
            "user_id": user_id,
            "recipe_id": recipe_id,
            "shop_id": shop_id,
            "started_at": started_at,
            "ready_at": ready_at,
            "status": status,
            "inputs_locked_json": list(inputs_locked or []),
            "result_json": dict(result_json or {}),
            "logs_json": list(logs or []),
        }
        self.jobs[job["job_id"]] = job
        return dict(job)

    def list_crafting_recipes(self):
        return [dict(self.recipe)]

    def list_craft_jobs(self, _campaign_id, _user_id, shop_id=None):
        rows = list(self.jobs.values())
        if shop_id:
            rows = [j for j in rows if j.get("shop_id") == shop_id]
        return [dict(j) for j in rows]

    def get_craft_job(self, job_id):
        row = self.jobs.get(job_id)
        return dict(row) if row else None

    def update_craft_job_status(self, job_id, status, logs=None):
        if job_id not in self.jobs:
            return None
        self.jobs[job_id]["status"] = status
        if logs is not None:
            self.jobs[job_id]["logs_json"] = list(logs)
        return dict(self.jobs[job_id])



def _setup_runtime(monkeypatch):
    sent = []

    async def _send_to(_sid, uid, msg):
        sent.append((uid, msg))

    monkeypatch.setattr(inventory.manager, "send_to", _send_to)
    monkeypatch.setattr(inventory.manager, "broadcast", lambda *_args, **_kwargs: asyncio.sleep(0))
    monkeypatch.setattr(inventory, "save_campaign_async", lambda _session: asyncio.sleep(0))
    monkeypatch.setattr(inventory, "_broadcast_inventory_state", lambda _session: asyncio.sleep(0))
    monkeypatch.setattr(inventory, "_build_profession_state", lambda _cid, _uid: {
        "catalog": [{"id": "alchemy", "name": "Alchemy"}],
        "player_profession_ids": ["alchemy"],
        "max_professions": 2,
        "open_slots": 1,
    })
    return sent



def _wire_db(monkeypatch, stub):
    monkeypatch.setattr("server.db.get_shop_by_id", stub.get_shop_by_id)
    monkeypatch.setattr("server.db.get_crafting_recipe", stub.get_crafting_recipe)
    monkeypatch.setattr("server.db.create_craft_job", stub.create_craft_job)
    monkeypatch.setattr("server.db.list_crafting_recipes", stub.list_crafting_recipes)
    monkeypatch.setattr("server.db.list_craft_jobs", stub.list_craft_jobs)
    monkeypatch.setattr("server.db.get_craft_job", stub.get_craft_job)
    monkeypatch.setattr("server.db.update_craft_job_status", stub.update_craft_job_status)



def _find_last(sent, msg_type):
    msgs = [msg for _, msg in sent if isinstance(msg, dict) and msg.get("type") == msg_type]
    return msgs[-1] if msgs else None



def _session_with_player():
    session = Session(id="sess-craft")
    user = User(id="player-1", name="Aria", role="player")
    session.users[user.id] = user
    owner_key = inventory._user_bucket_key(user)
    session.player_inventories = {
        owner_key: [
            {"name": "Amberglass Vial", "qty": 2, "notes": ""},
        ]
    }
    set_player_gold_for_user(session, user.id, 1000)
    session._shop_access_tokens = {f"{user.id}:shop-1": {"expires_at": time.time() + 60, "prop_id": "prop-1"}}
    return session, user



def test_recipe_list_filters_by_profession_and_station(monkeypatch):
    session, user = _session_with_player()
    monkeypatch.setattr(inventory, "_build_profession_state", lambda _cid, _uid: {
        "catalog": [], "player_profession_ids": ["alchemy"], "max_professions": 2, "open_slots": 1
    })
    monkeypatch.setattr("server.db.list_crafting_recipes", lambda: [
        {
            "id": "ok",
            "name": "OK",
            "requires_professions_json": ["alchemy"],
            "requires_materials_json": [],
            "station_shop_types_json": ["alchemist"],
            "result_item_json": {"name": "OK"},
            "fee_units": 0,
        },
        {
            "id": "bad-prof",
            "name": "Bad Profession",
            "requires_professions_json": ["tailoring"],
            "requires_materials_json": [],
            "station_shop_types_json": ["alchemist"],
            "result_item_json": {"name": "X"},
            "fee_units": 0,
        },
        {
            "id": "bad-station",
            "name": "Bad Station",
            "requires_professions_json": ["alchemy"],
            "requires_materials_json": [],
            "station_shop_types_json": ["blacksmith"],
            "result_item_json": {"name": "Y"},
            "fee_units": 0,
        },
    ])
    monkeypatch.setattr("server.db.list_craft_jobs", lambda *_args, **_kwargs: [])
    state = inventory._build_craft_state(session, user, {"id": "shop-1", "shop_type": "alchemist"})
    by_id = {r["id"]: r for r in state["recipes"]}
    assert set(by_id.keys()) == {"ok", "bad-prof", "bad-station"}
    assert by_id["ok"].get("locked_reason", "") == ""
    assert by_id["bad-prof"].get("locked_reason") == "missing_profession"
    assert by_id["bad-station"].get("locked_reason") == "wrong_station"



def test_craft_start_fails_when_materials_missing(monkeypatch):
    sent = _setup_runtime(monkeypatch)
    stub = _CraftDBStub()
    _wire_db(monkeypatch, stub)
    session, user = _session_with_player()
    session.player_inventories = {inventory._user_bucket_key(user): []}

    asyncio.run(inventory.handle_start_craft_job({"shop_id": "shop-1", "recipe_id": "rec_minor_healing_draught"}, session, user))
    result = _find_last(sent, "craft_job_result")
    assert result is not None
    assert result["payload"]["success"] is False
    assert "missing materials" in result["payload"]["message"].lower()



def test_craft_start_fails_when_fee_missing(monkeypatch):
    sent = _setup_runtime(monkeypatch)
    stub = _CraftDBStub()
    _wire_db(monkeypatch, stub)
    session, user = _session_with_player()
    set_player_gold_for_user(session, user.id, 0)

    asyncio.run(inventory.handle_start_craft_job({"shop_id": "shop-1", "recipe_id": "rec_minor_healing_draught"}, session, user))
    result = _find_last(sent, "craft_job_result")
    assert result is not None
    assert result["payload"]["success"] is False
    assert "not enough gold" in result["payload"]["message"].lower()



def test_craft_start_removes_materials_and_creates_job(monkeypatch):
    sent = _setup_runtime(monkeypatch)
    stub = _CraftDBStub()
    _wire_db(monkeypatch, stub)
    session, user = _session_with_player()

    asyncio.run(inventory.handle_start_craft_job({"shop_id": "shop-1", "recipe_id": "rec_minor_healing_draught"}, session, user))
    result = _find_last(sent, "craft_job_result")
    assert result and result["payload"]["success"] is True
    inv = session.player_inventories[inventory._user_bucket_key(user)]
    assert inv[0]["qty"] == 1
    assert len(stub.jobs) == 1
    job = list(stub.jobs.values())[0]
    assert job["inputs_locked_json"][0]["name"] == "Amberglass Vial"
    assert get_player_gold_for_user(session, user.id) == 880



def test_collect_before_ready_fails(monkeypatch):
    sent = _setup_runtime(monkeypatch)
    stub = _CraftDBStub()
    _wire_db(monkeypatch, stub)
    session, user = _session_with_player()
    now = time.time()
    stub.jobs["job-1"] = {
        "job_id": "job-1", "campaign_id": session.id, "user_id": user.id, "recipe_id": "rec_minor_healing_draught",
        "shop_id": "shop-1", "started_at": now, "ready_at": now + 999, "status": "crafting",
        "inputs_locked_json": [], "result_json": {"name": "Minor Healing Draught"}, "logs_json": []
    }

    asyncio.run(inventory.handle_collect_craft_job({"shop_id": "shop-1", "job_id": "job-1"}, session, user))
    result = _find_last(sent, "craft_collect_result")
    assert result and result["payload"]["success"] is False



def test_collect_after_ready_succeeds_and_duplicate_blocked(monkeypatch):
    sent = _setup_runtime(monkeypatch)
    stub = _CraftDBStub()
    _wire_db(monkeypatch, stub)
    session, user = _session_with_player()
    now = time.time()
    stub.jobs["job-1"] = {
        "job_id": "job-1", "campaign_id": session.id, "user_id": user.id, "recipe_id": "rec_minor_healing_draught",
        "shop_id": "shop-1", "started_at": now - 120, "ready_at": now - 1, "status": "crafting",
        "inputs_locked_json": [], "result_json": {"name": "Minor Healing Draught", "notes": "Crafted"}, "logs_json": []
    }

    asyncio.run(inventory.handle_collect_craft_job({"shop_id": "shop-1", "job_id": "job-1"}, session, user))
    ok = _find_last(sent, "craft_collect_result")
    assert ok and ok["payload"]["success"] is True
    inv = session.player_inventories[inventory._user_bucket_key(user)]
    assert any(i.get("name") == "Minor Healing Draught" for i in inv)

    asyncio.run(inventory.handle_collect_craft_job({"shop_id": "shop-1", "job_id": "job-1"}, session, user))
    dup = _find_last(sent, "craft_collect_result")
    assert dup and dup["payload"]["success"] is False
    assert "already collected" in dup["payload"]["message"].lower()



def test_reconnect_persists_craft_jobs_db_roundtrip():
    from server import db

    db.init_db()
    created = db.create_craft_job(
        "camp-reconnect", "user-reconnect", "rec_minor_healing_draught", "shop-reconnect",
        time.time(), time.time() + 10, "crafting", [{"name": "Amberglass Vial", "qty": 1}],
        {"name": "Minor Healing Draught"}, [{"event": "started"}],
    )
    assert created is not None
    jobs = db.list_craft_jobs("camp-reconnect", "user-reconnect", shop_id="shop-reconnect")
    assert any(j.get("job_id") == created.get("job_id") for j in jobs)
