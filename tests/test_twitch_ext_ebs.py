"""
Tests for the Twitch Extension EBS (server/twitch_ext/).

Covers: SKU->power compliance, JWT verification, bind/catalog/transaction flow,
replay + unknown-SKU rejection, approval-gate preservation, offline-viewer grant,
and graceful handling when the extension env is not configured.
"""
import os
import base64
import secrets
import tempfile
import time

# Isolate persistence to a temp data dir BEFORE importing server modules so
# paths.py resolves DB_PATH / DATA_DIR there (outside the repo tree).
_TMP = tempfile.mkdtemp(prefix="twitch_ext_test_")
os.environ.setdefault("DND_DATA_DIR", _TMP)
os.environ.setdefault("DND_DB_PATH", os.path.join(_TMP, "campaigns.db"))

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

import main
from server.session import create_session, get_session, User
from server.auth.models import init_auth_db, create_user, set_user_twitch_id
from server.http.auth import auth_player_key
from server.twitch_ext.granting import SKU_TO_POWER
from server.handlers.viewer_powers import VIEWER_POWER_DEFS, _get_viewer_profiles


_RAW_SECRET = secrets.token_bytes(32)
_B64_SECRET = base64.b64encode(_RAW_SECRET).decode()


@pytest.fixture(autouse=True)
def _configure_ext(monkeypatch):
    monkeypatch.setenv("TWITCH_EXT_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("TWITCH_EXT_SECRET", _B64_SECRET)
    monkeypatch.setenv("TWITCH_EXT_OWNER_ID", "999999")
    monkeypatch.setenv("TWITCH_EXT_SUB_POWERS", "healing_spark")
    init_auth_db()
    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def _ext_jwt(channel_id, *, role="viewer", user_id=None, exp_delta=600):
    claims = {
        "channel_id": str(channel_id),
        "role": role,
        "opaque_user_id": "U12345",
        "exp": int(time.time()) + exp_delta,
    }
    if user_id is not None:
        claims["user_id"] = str(user_id)
    return pyjwt.encode(claims, _RAW_SECRET, algorithm="HS256")


def _bits_receipt(transaction_id, sku, twitch_user_id):
    claims = {
        "topic": "bits_transaction_receipt",
        "exp": int(time.time()) + 600,
        "data": {
            "transactionId": transaction_id,
            "time": "2026-06-27T00:00:00Z",
            "userId": str(twitch_user_id),
            "product": {"sku": sku, "displayName": sku, "cost": {"amount": 100, "type": "bits"}, "inDevelopment": False},
        },
    }
    return pyjwt.encode(claims, _RAW_SECRET, algorithm="HS256")


def _make_linked_user(twitch_id):
    suffix = secrets.token_hex(4)
    rec = create_user(f"viewer_{suffix}", f"{suffix}@example.com", "x", "player")
    set_user_twitch_id(rec["id"], twitch_id)
    return rec["id"]


def _bind(client, channel_id, session_id, role="broadcaster", **body):
    token = _ext_jwt(channel_id, role=role)
    payload = {"session_id": session_id, **body}
    return client.post("/api/twitch/ext/bind-session", json=payload, headers={"Authorization": f"Bearer {token}"})


# ── compliance ───────────────────────────────────────────────────────────────

def test_sku_map_only_targets_known_powers():
    assert SKU_TO_POWER, "SKU map must not be empty"
    for sku, power_id in SKU_TO_POWER.items():
        assert power_id in VIEWER_POWER_DEFS, f"{sku} -> {power_id} is not a known power"
    # No random-outcome SKU: every SKU resolves to exactly one specific power.
    assert len(set(SKU_TO_POWER.values())) == len(SKU_TO_POWER.values())


# ── auth / config ────────────────────────────────────────────────────────────

def test_unconfigured_returns_503(client, monkeypatch):
    monkeypatch.delenv("TWITCH_EXT_CLIENT_ID", raising=False)
    r = client.get("/api/twitch/ext/catalog?channel=1", headers={"Authorization": "Bearer x"})
    assert r.status_code == 503
    assert r.json()["error"] == "extension_not_configured"


def test_bad_jwt_rejected(client):
    r = client.get("/api/twitch/ext/catalog?channel=1", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_bind_requires_broadcaster_role(client):
    session, _dm = create_session("DM")
    r = _bind(client, "chan_role", session.id, role="viewer")
    assert r.status_code == 403


# ── full flow ────────────────────────────────────────────────────────────────

def test_bind_catalog_and_transaction_grants_power(client):
    session, _dm = create_session("DM")
    channel_id = "chan_flow"
    twitch_id = "tw_" + secrets.token_hex(3)
    local_id = _make_linked_user(twitch_id)

    # connected viewer mapped via auth player_key
    viewer = User(id=local_id, name="Streamer Fan", role="viewer")
    viewer.player_key = auth_player_key(local_id)
    session.users[viewer.id] = viewer

    assert _bind(client, channel_id, session.id).status_code == 200

    # catalog
    cat = client.get(f"/api/twitch/ext/catalog?channel={channel_id}",
                     headers={"Authorization": f"Bearer {_ext_jwt(channel_id, user_id=twitch_id)}"})
    assert cat.status_code == 200
    body = cat.json()
    assert body["bound"] is True
    skus = {p["sku"] for p in body["powers"]}
    assert "power_pebble_toss" in skus

    # transaction: buy a non-approval power -> immediately usable
    txid = "txn_" + secrets.token_hex(6)
    receipt = _bits_receipt(txid, "power_pebble_toss", twitch_id)
    r = client.post("/api/twitch/ext/transaction", json={"transactionReceipt": receipt},
                    headers={"Authorization": f"Bearer {_ext_jwt(channel_id, user_id=twitch_id)}"})
    assert r.status_code == 200, r.text
    grant = r.json()["grant"]
    assert grant["power_id"] == "pebble_toss"
    assert grant["requires_approval"] is False

    # profile updated in the live session
    profiles = _get_viewer_profiles(get_session(session.id))
    vkey = auth_player_key(local_id)
    assert "pebble_toss" in profiles[vkey]["powers"]
    assert profiles[vkey]["powers"]["pebble_toss"]["charges"] == 1

    # replay rejected (idempotent duplicate)
    r2 = client.post("/api/twitch/ext/transaction", json={"transactionReceipt": receipt},
                     headers={"Authorization": f"Bearer {_ext_jwt(channel_id, user_id=twitch_id)}"})
    assert r2.status_code == 200
    assert r2.json().get("duplicate") is True
    # still exactly one charge, not two
    profiles = _get_viewer_profiles(get_session(session.id))
    assert profiles[vkey]["powers"]["pebble_toss"]["charges"] == 1


def test_unknown_sku_rejected(client):
    session, _dm = create_session("DM")
    channel_id = "chan_unknown"
    twitch_id = "tw_" + secrets.token_hex(3)
    _make_linked_user(twitch_id)
    _bind(client, channel_id, session.id)
    receipt = _bits_receipt("txn_" + secrets.token_hex(6), "power_does_not_exist", twitch_id)
    r = client.post("/api/twitch/ext/transaction", json={"transactionReceipt": receipt},
                    headers={"Authorization": f"Bearer {_ext_jwt(channel_id, user_id=twitch_id)}"})
    assert r.status_code == 400
    assert r.json()["error"] == "unknown_sku"


def test_approval_power_keeps_requires_approval(client):
    session, _dm = create_session("DM")
    channel_id = "chan_approval"
    twitch_id = "tw_" + secrets.token_hex(3)
    local_id = _make_linked_user(twitch_id)
    _bind(client, channel_id, session.id)
    receipt = _bits_receipt("txn_" + secrets.token_hex(6), "power_fireball", twitch_id)
    r = client.post("/api/twitch/ext/transaction", json={"transactionReceipt": receipt},
                    headers={"Authorization": f"Bearer {_ext_jwt(channel_id, user_id=twitch_id)}"})
    assert r.status_code == 200, r.text
    assert r.json()["grant"]["requires_approval"] is True  # fireball stays DM-gated


def test_offline_viewer_still_granted(client):
    session, _dm = create_session("DM")
    channel_id = "chan_offline"
    twitch_id = "tw_" + secrets.token_hex(3)
    local_id = _make_linked_user(twitch_id)
    # NOTE: no viewer added to session.users -> account is linked but offline
    _bind(client, channel_id, session.id)
    receipt = _bits_receipt("txn_" + secrets.token_hex(6), "power_healing_spark", twitch_id)
    r = client.post("/api/twitch/ext/transaction", json={"transactionReceipt": receipt},
                    headers={"Authorization": f"Bearer {_ext_jwt(channel_id, user_id=twitch_id)}"})
    assert r.status_code == 200, r.text
    profiles = _get_viewer_profiles(get_session(session.id))
    assert auth_player_key(local_id) in profiles  # waiting for them when they join


def test_transaction_without_identity_rejected(client):
    session, _dm = create_session("DM")
    channel_id = "chan_noid"
    _bind(client, channel_id, session.id)
    # receipt with empty buyer id + JWT without user_id => no identity
    receipt = _bits_receipt("txn_" + secrets.token_hex(6), "power_pebble_toss", "")
    r = client.post("/api/twitch/ext/transaction", json={"transactionReceipt": receipt},
                    headers={"Authorization": f"Bearer {_ext_jwt(channel_id)}"})
    assert r.status_code == 403
    assert r.json()["error"] == "no_identity"
