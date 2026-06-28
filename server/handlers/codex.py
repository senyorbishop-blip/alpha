"""
server/handlers/codex.py — Codex WebSocket handlers.

Codex is the unified home for Notes, Session Logs, and Lore. It stores
entries in codex_entries with three-tier visibility:
  private  → author + DM only
  party    → all players/viewers + DM
  dm       → DM (and assistant_dm) only

Quest entries are read-only projections managed by PR3; in PR1 they are
stored as ordinary entries if created directly.
"""
from __future__ import annotations

import secrets
import time

from server.session import Session, User
from server.handlers.common import manager
from server.db import save_campaign_async


def _codex_visible_for_role(entries: list, role: str, user_id: str | None) -> list:
    """Return entries visible to the given role/user."""
    if role in ("dm", "assistant_dm"):
        return list(entries)
    result = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        vis = e.get("visibility", "party")
        if vis == "party":
            result.append(e)
        elif vis == "private" and e.get("author_id") == user_id:
            result.append(e)
    return result


async def _broadcast_codex_state(session: Session) -> None:
    all_entries = list(getattr(session, "codex_entries", []) or [])
    all_links = list(getattr(session, "codex_links", []) or [])
    for uid, u in session.users.items():
        visible = _codex_visible_for_role(all_entries, u.role, uid)
        await manager.send_to(session.id, uid, {
            "type": "codex_sync",
            "payload": {
                "entries": visible,
                "links": all_links,
            },
        })


async def handle_codex_upsert(payload: dict, session: Session, user: User) -> None:
    """Create or update a codex entry.

    DM/assistant_dm may set any visibility. Players may only author
    private/party entries and cannot reassign authorship away from themselves.
    """
    entries = list(getattr(session, "codex_entries", []) or [])
    entry_id = str(payload.get("id") or "").strip()[:64] or secrets.token_hex(6)
    now = time.time()

    # Find existing entry (for ownership check)
    existing = next((e for e in entries if isinstance(e, dict) and e.get("id") == entry_id), None)

    if user.role == "player":
        # Players can only edit entries they authored (or create new ones)
        if existing and existing.get("author_id") != user.id:
            await manager.send_to(session.id, user.id, {
                "type": "error",
                "payload": {"message": "You can only edit your own Codex entries."},
            })
            return
        # Players cannot create dm-visibility entries
        raw_vis = str(payload.get("visibility") or "party").strip().lower()
        visibility = raw_vis if raw_vis in ("private", "party") else "party"
    else:
        raw_vis = str(payload.get("visibility") or "party").strip().lower()
        visibility = raw_vis if raw_vis in ("private", "party", "dm") else "party"

    entry_type = str(payload.get("type") or "note").strip().lower()[:32]
    if entry_type not in {"note", "log", "lore", "quest"}:
        entry_type = "note"
    # Players cannot create quest-type entries
    if user.role == "player" and entry_type == "quest":
        entry_type = "note"

    title = str(payload.get("title") or "").strip()[:240] or "Untitled"
    content_md = str(payload.get("content_md") or "")[:16000]
    tags = [str(t)[:64] for t in (payload.get("tags") or []) if isinstance(t, str)][:32]
    poi_id = str(payload.get("poi_id") or "").strip()[:64] or None

    author_id = (existing or {}).get("author_id") or user.id
    created_at = (existing or {}).get("created_at") or now

    entry = {
        "id": entry_id,
        "type": entry_type,
        "visibility": visibility,
        "author_id": author_id,
        "title": title,
        "content_md": content_md,
        "created_at": created_at,
        "updated_at": now,
        "tags": tags,
        "poi_id": poi_id,
    }

    entries = [e for e in entries if not (isinstance(e, dict) and e.get("id") == entry_id)]
    entries.append(entry)
    session.codex_entries = entries

    await _broadcast_codex_state(session)
    await save_campaign_async(session)


async def handle_codex_delete(payload: dict, session: Session, user: User) -> None:
    """Delete a codex entry. Players may only delete entries they authored."""
    entry_id = str(payload.get("id") or "").strip()[:64]
    if not entry_id:
        return

    entries = list(getattr(session, "codex_entries", []) or [])
    target = next((e for e in entries if isinstance(e, dict) and e.get("id") == entry_id), None)

    if target is None:
        return

    if user.role == "player" and target.get("author_id") != user.id:
        await manager.send_to(session.id, user.id, {
            "type": "error",
            "payload": {"message": "You can only delete your own Codex entries."},
        })
        return

    session.codex_entries = [e for e in entries if not (isinstance(e, dict) and e.get("id") == entry_id)]

    # Cascade: remove any links referencing this entry
    links = list(getattr(session, "codex_links", []) or [])
    session.codex_links = [
        lnk for lnk in links
        if isinstance(lnk, dict) and not (
            (lnk.get("from_type") == "entry" and lnk.get("from_id") == entry_id)
            or (lnk.get("to_type") == "entry" and lnk.get("to_id") == entry_id)
        )
    ]

    await _broadcast_codex_state(session)
    await save_campaign_async(session)


async def handle_codex_link_set(payload: dict, session: Session, user: User) -> None:
    """Create, update, or delete a codex link.

    Pass `delete: true` to remove a link by id.
    """
    link_id = str(payload.get("id") or "").strip()[:64] or secrets.token_hex(6)
    links = list(getattr(session, "codex_links", []) or [])

    if payload.get("delete"):
        session.codex_links = [
            lnk for lnk in links
            if not (isinstance(lnk, dict) and lnk.get("id") == link_id)
        ]
        await _broadcast_codex_state(session)
        await save_campaign_async(session)
        return

    from_type = str(payload.get("from_type") or "").strip()[:32]
    from_id = str(payload.get("from_id") or "").strip()[:64]
    to_type = str(payload.get("to_type") or "").strip()[:32]
    to_id = str(payload.get("to_id") or "").strip()[:64]

    if not (from_type and from_id and to_type and to_id):
        await manager.send_to(session.id, user.id, {
            "type": "error",
            "payload": {"message": "codex_link_set requires from_type, from_id, to_type, to_id."},
        })
        return

    existing = next((lnk for lnk in links if isinstance(lnk, dict) and lnk.get("id") == link_id), None)
    created_at = (existing or {}).get("created_at") or time.time()

    link = {
        "id": link_id,
        "from_type": from_type,
        "from_id": from_id,
        "to_type": to_type,
        "to_id": to_id,
        "label": str(payload.get("label") or "").strip()[:120],
        "author_id": user.id,
        "created_at": created_at,
    }

    links = [lnk for lnk in links if not (isinstance(lnk, dict) and lnk.get("id") == link_id)]
    links.append(link)
    session.codex_links = links

    await _broadcast_codex_state(session)
    await save_campaign_async(session)


async def handle_codex_link_query(payload: dict, session: Session, user: User) -> None:
    """Return links matching the given entity type/id filter."""
    entity_type = str(payload.get("entity_type") or "").strip()[:32]
    entity_id = str(payload.get("entity_id") or "").strip()[:64]

    all_links = list(getattr(session, "codex_links", []) or [])

    if entity_type and entity_id:
        matched = [
            lnk for lnk in all_links
            if isinstance(lnk, dict) and (
                (lnk.get("from_type") == entity_type and lnk.get("from_id") == entity_id)
                or (lnk.get("to_type") == entity_type and lnk.get("to_id") == entity_id)
            )
        ]
    else:
        matched = all_links

    await manager.send_to(session.id, user.id, {
        "type": "codex_link_query_result",
        "payload": {"links": matched},
    })
