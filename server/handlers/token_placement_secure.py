"""Secure token placement handler.

The legacy token placement path used a raw session broadcast after moving a
staged token onto the map. Raw broadcasts are unsafe for hidden/staged NPCs
because every connected client receives the full token payload before per-user
visibility filtering can remove it.
"""
from __future__ import annotations

from server.handlers.common import (
    Session,
    User,
    manager,
    save_campaign_async,
    _broadcast_token_event,
    _broadcast_token_state_sync,
    _stamp_token_revision,
)
from server.session import build_token_runtime_payload, normalize_map_context
from server.handlers.tokens import (
    _deny_player_single_token_limit,
    _owner_matches_user,
    _player_active_owned_tokens,
)


async def handle_token_placed_secure(payload: dict, session: Session, user: User):
    """Move a staged token to the map using per-user token visibility filtering."""
    session.enforce_single_active_player_token_rule()
    token_id = payload.get("token_id")
    token = session.tokens.get(token_id)
    if not token:
        return

    if user.role == "player" and not _owner_matches_user(getattr(token, "owner_id", ""), user):
        await manager.send_to(session.id, user.id, {
            "type": "error",
            "payload": {"message": "You can only place your own token from staging."},
        })
        return

    owner_id = str(getattr(token, "owner_id", "") or "").strip()
    if owner_id and _player_active_owned_tokens(session, owner_id, exclude_token_id=token.id):
        msg = "That player already has an active token on the field."
        if user.role == "player" and _owner_matches_user(owner_id, user):
            await _deny_player_single_token_limit(session, user, token_name="token")
        else:
            await manager.send_to(session.id, user.id, {
                "type": "error",
                "payload": {"message": msg},
            })
        return

    token.x = payload.get("x", token.x)
    token.y = payload.get("y", token.y)
    token.map_context = payload.get("map_context", token.map_context)
    token.staged = False
    token_rev = _stamp_token_revision(session, token)

    placed_payload = {
        **payload,
        "token": build_token_runtime_payload(session, token),
        "token_id": token.id,
        "map_context": normalize_map_context(getattr(token, "map_context", "world")),
        "token_state_revision": token_rev,
        "visibility_revision": int(getattr(session, "visibility_revision", 0) or 0),
    }

    await _broadcast_token_event(
        manager,
        session,
        "token_placed",
        placed_payload,
        token,
    )
    await _broadcast_token_state_sync(session)
    await save_campaign_async(session)
