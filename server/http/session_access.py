from fastapi.responses import JSONResponse
import logging

from server.db import load_campaign
from server.restore import restore_session_from_db
from server.session import get_session
from server.http.auth import auth_player_key, get_request_user


restore_session = restore_session_from_db

logger = logging.getLogger(__name__)


def resolve_session_authority(request, session, fallback_user_id: str = "") -> dict:
    """Resolve authenticated/session-backed authority separately from UI mode hints."""
    auth_user = get_request_user(request)
    auth_user_id = str((auth_user or {}).get("id") or "").strip()
    auth_player_key_id = auth_player_key(auth_user_id) if auth_user_id else ""
    fallback_user_id = str(fallback_user_id or "").strip()
    candidate_ids = []
    if auth_user_id:
        candidate_ids.append(auth_user_id)
        if auth_player_key_id and auth_player_key_id not in candidate_ids:
            candidate_ids.append(auth_player_key_id)

    # Restrict fallback identity when an authenticated principal exists:
    # - fallback can only mirror the auth id/player-key
    # - or map to a session participant that is explicitly linked to that auth player-key.
    fallback_allowed = False
    fallback_via = "none"
    if fallback_user_id:
        if not auth_user_id:
            fallback_allowed = True
            fallback_via = "legacy_unauthenticated"
        elif fallback_user_id in {auth_user_id, auth_player_key_id}:
            fallback_allowed = True
            fallback_via = "auth_exact_match"
        else:
            session_user = (getattr(session, "users", {}) or {}).get(fallback_user_id)
            session_user_key = str(getattr(session_user, "player_key", "") or "").strip()
            if session_user and auth_player_key_id and session_user_key == auth_player_key_id:
                fallback_allowed = True
                fallback_via = "auth_player_key_match"
    if fallback_allowed and fallback_user_id not in candidate_ids:
        candidate_ids.append(fallback_user_id)

    matched_user = None
    matched_user_id = ""
    matched_via = "none"
    for candidate in candidate_ids:
        session_user = session.users.get(candidate)
        if session_user:
            matched_user = session_user
            matched_user_id = candidate
            matched_via = "session_user"
            break
        if getattr(session, 'dm_id', None) == candidate:
            matched_user_id = candidate
            matched_via = "session_dm_id"
            break
    # Secondary: find session users by stored player_key (handles auth DM whose session
    # user is keyed by internal dm_id, not auth user id)
    if not matched_user_id and auth_player_key_id:
        for uid, u in session.users.items():
            if str(getattr(u, 'player_key', '') or '').strip() == auth_player_key_id:
                matched_user = u
                matched_user_id = uid
                matched_via = "player_key"
                break

    participant_role = str(getattr(matched_user, 'role', '') or '').strip().lower() or None
    is_session_dm = bool(matched_user_id and str(getattr(session, 'dm_id', '') or '') == matched_user_id) or participant_role == 'dm'
    resolved_user_id = matched_user_id or fallback_user_id or auth_user_id or None
    authority = {
        'auth_user_id': auth_user_id or None,
        'auth_player_key': auth_player_key_id or None,
        'fallback_user_id': fallback_user_id or None,
        'fallback_allowed': bool(fallback_allowed),
        'fallback_allowed_via': fallback_via,
        'resolved_user_id': resolved_user_id,
        'resolved_session_user_id': matched_user_id or None,
        'participant_role': participant_role,
        'session_dm_id': str(getattr(session, 'dm_id', '') or '') or None,
        'is_session_dm': bool(is_session_dm),
        'matched_via': matched_via,
    }
    logger.info('[Authority] session_id=%s auth_user_id=%s auth_player_key=%s fallback_user_id=%s fallback_allowed=%s fallback_allowed_via=%s resolved_user_id=%s participant_role=%s session_dm_id=%s is_session_dm=%s matched_via=%s',
        str(getattr(session, 'id', '') or ''),
        authority['auth_user_id'], authority['auth_player_key'], authority['fallback_user_id'], authority['fallback_allowed'], authority['fallback_allowed_via'], authority['resolved_user_id'], authority['participant_role'], authority['session_dm_id'], authority['is_session_dm'], authority['matched_via'])
    return authority


def can_user_place_creatures(session, user=None, connection=None, mode=None, request=None, fallback_user_id: str = "") -> dict:
    authority = resolve_session_authority(request, session, fallback_user_id=fallback_user_id) if request is not None else {}
    authenticated_user_id = str(getattr(user, 'id', '') or authority.get('resolved_user_id') or '').strip() or None
    participant_role = str(getattr(user, 'role', '') or authority.get('participant_role') or '').strip().lower() or None
    session_dm_id = str(getattr(session, 'dm_id', '') or authority.get('session_dm_id') or '').strip() or None
    preview_mode = bool(mode in {'player_preview', 'player-view', 'player_view', 'preview'})
    is_session_dm = bool(authority.get('is_session_dm')) or (authenticated_user_id and session_dm_id == authenticated_user_id) or participant_role == 'dm'
    allowed = bool(is_session_dm)
    reason = 'allowed_session_dm' if allowed else 'not_session_dm'
    return {
        'allowed': allowed,
        'reason': reason,
        'authenticated_user_id': authenticated_user_id,
        'participant_role': participant_role,
        'session_dm_id': session_dm_id,
        'connection_user_id': str(connection.get('user_id') or '').strip() or None if isinstance(connection, dict) else None,
        'ui_mode': mode,
        'preview_mode': preview_mode,
        'authority': authority,
    }



def get_or_restore_session(session_id: str):
    """Return an in-memory session, restoring it from the DB when available."""
    session = get_session(session_id)
    if not session:
        db_data = load_campaign(session_id)
        if db_data:
            restore_session(db_data)
            session = get_session(session_id)
    return session


def get_session_and_user(session_id: str, user_id: str):
    session = get_or_restore_session(session_id)
    if not session:
        return None, None, JSONResponse({"ok": False, "error": "Session not found"}, status_code=404)
    user = session.users.get(user_id)
    if not user:
        return session, None, JSONResponse({"ok": False, "error": "User not found in session"}, status_code=403)
    return session, user, None


def request_has_dm_access(request, session, fallback_user_id: str = "") -> bool:
    """Return True when the request is authorized as the DM for the session."""
    return bool(resolve_session_authority(request, session, fallback_user_id=fallback_user_id).get("is_session_dm"))
