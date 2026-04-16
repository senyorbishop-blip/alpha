import asyncio

from server.character.summon_runtime import build_summon_runtime_payload
from server.handlers import summons as summon_handlers
from server.session import Session, Token, User


def _seed_ranger_profile(session: Session, player: User):
    session.users[player.id] = player
    owner_key = player.name.lower()
    session.char_profiles = {
        owner_key: [
            {
                "id": "profile-ranger",
                "nativeCharacter": {
                    "classes": [{"classId": "ranger", "level": 5, "subclassId": "beast-master"}],
                    "abilities": {"scores": {"wis": 14, "con": 12}},
                    "summons": {
                        "unlockedTemplates": ["ranger-primal-beast-land"],
                        "selectedVariants": {"ranger-primal-beast": "ranger-primal-beast-land"},
                        "activeSummons": [],
                    },
                },
            }
        ]
    }
    session.active_char_profiles = {player.id: "profile-ranger"}


def test_runtime_payload_reports_structured_failure_for_missing_unlock():
    session = Session(id="SUMMON-L1")
    player = User(id="p1", name="Ayla", role="player")
    _seed_ranger_profile(session, player)

    result = build_summon_runtime_payload(
        session=session,
        user=player,
        payload={
            "profile_id": "profile-ranger",
            "summon_group_id": "ranger-primal-beast",
            "summon_template_id": "ranger-primal-beast-sky",
            "selected_variant": "ranger-primal-beast-sky",
        },
    )

    assert result.get("ok") is False
    assert result.get("error") in {"invalid_variant", "summon_not_unlocked"}
    failure = result.get("failure") or {}
    assert failure.get("category") in {"illegal_variant_selection", "missing_summon_unlock"}
    assert isinstance(failure.get("context"), dict)


def test_request_rolls_back_when_register_active_fails(monkeypatch):
    session = Session(id="SUMMON-L2")
    player = User(id="p1", name="Ayla", role="player")
    _seed_ranger_profile(session, player)

    sent = []

    async def _send_to(*args, **kwargs):
        sent.append((args, kwargs))

    async def _broadcast(*args, **kwargs):
        return None

    async def _noop(*args, **kwargs):
        return None

    def _boom(*args, **kwargs):
        raise RuntimeError("register failed")

    monkeypatch.setattr(summon_handlers.manager, "send_to", _send_to)
    monkeypatch.setattr(summon_handlers.manager, "broadcast", _broadcast)
    monkeypatch.setattr(summon_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(summon_handlers, "register_active_summon", _boom)

    asyncio.run(
        summon_handlers.handle_summon_runtime_request(
            {
                "profile_id": "profile-ranger",
                "summon_group_id": "ranger-primal-beast",
                "summon_template_id": "ranger-primal-beast-land",
                "selected_variant": "ranger-primal-beast-land",
            },
            session,
            player,
        )
    )

    assert not any(tok.owner_id == player.id and tok.token_type == "companion" for tok in (session.tokens or {}).values())
    payloads = [call[0][2].get("payload") for call in sent if call and call[0] and len(call[0]) > 2]
    failure_rows = [p for p in payloads if isinstance(p, dict) and p.get("error") == "register_active_failed"]
    assert failure_rows
    assert isinstance((failure_rows[0].get("failure") or {}).get("category"), str)


def test_admin_cleanup_stale_quarantines_entry_and_metrics(monkeypatch):
    session = Session(id="SUMMON-L3")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Ayla", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player

    owner_key = player.name.lower()
    session.char_profiles = {
        owner_key: [
            {
                "id": "profile-ranger",
                "nativeCharacter": {
                    "summons": {
                        "activeSummons": [
                            {
                                "id": "active-1",
                                "templateId": "ranger-primal-beast-land",
                                "summonGroupId": "ranger-primal-beast",
                                "ownerProfileId": "profile-ranger",
                                "ownerUserId": player.id,
                                "tokenId": "missing-token",
                                "status": "active",
                                "actor": {"name": "Primal Beast"},
                            }
                        ]
                    }
                },
            }
        ]
    }

    sent = []

    async def _send_to(*args, **kwargs):
        sent.append((args, kwargs))

    async def _broadcast(*args, **kwargs):
        return None

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(summon_handlers.manager, "send_to", _send_to)
    monkeypatch.setattr(summon_handlers.manager, "broadcast", _broadcast)
    monkeypatch.setattr(summon_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(summon_handlers, "_broadcast_token_state_sync", _noop)
    monkeypatch.setattr(summon_handlers, "_send_char_profiles", _noop)

    asyncio.run(summon_handlers.handle_summon_runtime_admin({"action": "cleanup_stale"}, session, dm))
    asyncio.run(summon_handlers.handle_summon_runtime_admin({"action": "list"}, session, dm))

    list_payloads = [call[0][2].get("payload") for call in sent if call and call[0] and len(call[0]) > 2 and call[0][2].get("type") == "summon_runtime_admin_result"]
    assert list_payloads
    last = list_payloads[-1]
    summons = last.get("summons") or []
    assert summons and summons[0].get("status") == "quarantined"
    assert "retry_rebind" in (summons[0].get("recovery_suggestions") or [])
    assert (last.get("metrics") or {}).get("quarantined_count", 0) >= 1


def test_admin_retry_rebind_restores_active_when_token_exists(monkeypatch):
    session = Session(id="SUMMON-L4")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Ayla", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.tokens["tok-1"] = Token(id="tok-1", name="🐾 Beast", x=0, y=0, width=40, height=40, color="#fff", shape="circle", owner_id=player.id, token_type="companion")

    owner_key = player.name.lower()
    session.char_profiles = {
        owner_key: [
            {
                "id": "profile-ranger",
                "nativeCharacter": {
                    "summons": {
                        "activeSummons": [
                            {
                                "id": "active-1",
                                "templateId": "ranger-primal-beast-land",
                                "summonGroupId": "ranger-primal-beast",
                                "ownerProfileId": "profile-ranger",
                                "ownerUserId": player.id,
                                "tokenId": "tok-1",
                                "status": "quarantined",
                            }
                        ]
                    }
                },
            }
        ]
    }

    async def _noop(*args, **kwargs):
        return None

    sent = []

    async def _send_to(*args, **kwargs):
        sent.append((args, kwargs))

    monkeypatch.setattr(summon_handlers.manager, "send_to", _send_to)
    monkeypatch.setattr(summon_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(summon_handlers, "_broadcast_token_state_sync", _noop)

    asyncio.run(summon_handlers.handle_summon_runtime_admin({"action": "retry_rebind", "active_id": "active-1"}, session, dm))

    payload = sent[-1][0][2].get("payload")
    assert payload.get("ok") is True
    assert payload.get("action") == "retry_rebind"
    assert (payload.get("results") or [{}])[0].get("status") == "active"
