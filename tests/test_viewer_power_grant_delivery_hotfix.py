import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _make_session():
    from server.session import Session, User

    session = Session(id="viewer-power-delivery-hotfix")
    dm = User(id="dm1", name="DM", role="dm")
    viewer = User(id="viewer1", name="Spectator", role="viewer")
    viewer.player_key = "viewer-profile-key"
    session.users[dm.id] = dm
    session.users[viewer.id] = viewer
    session.dm_id = dm.id
    return session, dm, viewer


def _patch_manager(monkeypatch):
    from server.handlers import viewer_powers as vp

    sent = []

    async def _send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _broadcast(session_id, message, exclude_user=None):
        sent.append((session_id, "broadcast", message))

    monkeypatch.setattr(vp.manager, "send_to", _send_to)
    monkeypatch.setattr(vp.manager, "broadcast", _broadcast)
    return sent


def _patch_save(monkeypatch):
    from server.handlers import viewer_powers as vp

    async def _save(_session):
        return True

    monkeypatch.setattr(vp, "save_campaign_async", _save)


def _apply_hotfix():
    import sitecustomize

    assert sitecustomize.patch_viewer_power_delivery_now()


def test_dm_grant_resolves_viewer_key_and_notifies_viewer(monkeypatch):
    _apply_hotfix()
    from server.handlers import viewer_powers as vp

    session, dm, viewer = _make_session()
    sent = _patch_manager(monkeypatch)
    _patch_save(monkeypatch)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_key": "viewer-profile-key", "power_id": "pebble_toss"},
        session,
        dm,
    ))

    profile_key = vp._viewer_key_for_user(viewer)
    powers = (session.viewer_profiles.get(profile_key) or {}).get("powers") or {}
    assert "pebble_toss" in powers

    viewer_statuses = [
        message for _sid, uid, message in sent
        if uid == viewer.id and message.get("type") == "viewer_power_status"
    ]
    assert viewer_statuses, "Viewer should get visible feedback when the DM sends a power"
    assert "Pebble Toss" in viewer_statuses[-1]["payload"]["message"]

    dm_statuses = [
        message for _sid, uid, message in sent
        if uid == dm.id and message.get("type") == "viewer_power_status"
    ]
    assert dm_statuses, "DM should get confirmation instead of a silent no-op"


def test_dm_grant_preset_resolves_profile_key_and_notifies_viewer(monkeypatch):
    _apply_hotfix()
    from server.handlers import viewer_powers as vp

    session, dm, viewer = _make_session()
    sent = _patch_manager(monkeypatch)
    _patch_save(monkeypatch)

    asyncio.run(vp.handle_viewer_power_grant_preset(
        {"profile_key": "viewer-profile-key", "preset_id": "support_pack"},
        session,
        dm,
    ))

    profile_key = vp._viewer_key_for_user(viewer)
    powers = (session.viewer_profiles.get(profile_key) or {}).get("powers") or {}
    assert {"healing_spark", "battle_blessing"}.issubset(set(powers))

    viewer_statuses = [
        message for _sid, uid, message in sent
        if uid == viewer.id and message.get("type") == "viewer_power_status"
    ]
    assert viewer_statuses
    assert "Support Pack" in viewer_statuses[-1]["payload"]["message"]


def test_dm_grant_resolves_viewer_by_privacy_handle(monkeypatch):
    """A viewer who joins after the DM loaded is keyed in the DM client by the
    ``user_joined`` privacy handle, so the grant arrives addressed by handle
    rather than raw user id. Resolution must still find the viewer."""
    _apply_hotfix()
    from server.handlers import viewer_powers as vp
    from server.session import display_user_handle

    session, dm, viewer = _make_session()
    sent = _patch_manager(monkeypatch)
    _patch_save(monkeypatch)

    handle = display_user_handle(session.id, viewer.id)
    assert handle != viewer.id

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": handle, "power_id": "fireball"},
        session,
        dm,
    ))

    profile_key = vp._viewer_key_for_user(viewer)
    powers = (session.viewer_profiles.get(profile_key) or {}).get("powers") or {}
    assert "fireball" in powers, "Grant addressed by privacy handle should reach the viewer"

    dm_statuses = [
        message for _sid, uid, message in sent
        if uid == dm.id and message.get("type") == "viewer_power_status"
    ]
    assert dm_statuses and dm_statuses[-1]["payload"]["kind"] == "granted"

    # And the matching revoke (also addressed by handle) should clear it.
    asyncio.run(vp.handle_viewer_power_revoke(
        {"viewer_user_id": handle, "power_id": "fireball"},
        session,
        dm,
    ))
    powers_after = (session.viewer_profiles.get(profile_key) or {}).get("powers") or {}
    assert "fireball" not in powers_after, "Revoke addressed by privacy handle should remove the power"


def test_dm_grant_resolves_viewer_by_display_name_when_id_drifts(monkeypatch):
    """If the dropdown carries a stale id but the display name is sent, the
    server should still resolve the connected viewer by name."""
    _apply_hotfix()
    from server.handlers import viewer_powers as vp

    session, dm, viewer = _make_session()
    sent = _patch_manager(monkeypatch)
    _patch_save(monkeypatch)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_user_id": "stale-or-old-id", "name": viewer.name, "power_id": "pebble_toss"},
        session,
        dm,
    ))

    profile_key = vp._viewer_key_for_user(viewer)
    powers = (session.viewer_profiles.get(profile_key) or {}).get("powers") or {}
    assert "pebble_toss" in powers


def test_failed_dm_grant_reports_to_dm_instead_of_silent_noop(monkeypatch):
    _apply_hotfix()
    from server.handlers import viewer_powers as vp

    session, dm, _viewer = _make_session()
    sent = _patch_manager(monkeypatch)
    _patch_save(monkeypatch)

    asyncio.run(vp.handle_viewer_power_grant(
        {"viewer_key": "missing-viewer", "power_id": "pebble_toss"},
        session,
        dm,
    ))

    dm_statuses = [
        message for _sid, uid, message in sent
        if uid == dm.id and message.get("type") == "viewer_power_status"
    ]
    assert dm_statuses
    assert dm_statuses[-1]["payload"]["kind"] == "grant_failed"
