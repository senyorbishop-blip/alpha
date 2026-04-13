from fastapi.responses import JSONResponse

from server.http.session_access import get_session_and_user
from server.rules_db import (
    delete_custom_spell,
    get_custom_spells,
    get_official_spells,
    list_review_queue,
    upsert_custom_spell,
    upsert_review_queue,
)
from server.rules_engine import enrich_spellbook


def enrich_spellbook_response(session_id: str, user_id: str, character: dict):
    session, user, error = get_session_and_user(session_id, user_id)
    if error:
        return error
    if user.role == "viewer":
        return JSONResponse({"ok": False, "error": "Viewers cannot enrich character rules"}, status_code=403)
    official_spells = get_official_spells()
    custom_spells = get_custom_spells(session_id)
    enriched = enrich_spellbook(character, official_spells, custom_spells)
    upsert_review_queue(
        session_id,
        user_id,
        str((character or {}).get("name") or (character or {}).get("book", {}).get("name") or "Unknown Hero"),
        enriched.get("review_queue") or [],
    )
    payload = {
        "ok": True,
        "spell_cards": enriched.get("spell_cards") or [],
        "review_queue": enriched.get("review_queue") or [],
        "unmatched": enriched.get("unmatched") or [],
        "spellcasting": enriched.get("spellcasting") or {},
        "total_level": enriched.get("total_level") or 1,
        "official_count": len(official_spells),
    }
    if user.role == "dm":
        payload["custom_spells"] = custom_spells
        payload["dm_review_queue"] = list_review_queue(session_id)
    return JSONResponse(payload)


def review_queue_response(session_id: str, user_id: str):
    session, user, error = get_session_and_user(session_id, user_id)
    if error:
        return error
    if user.role != "dm":
        return JSONResponse({"ok": False, "error": "DM only"}, status_code=403)
    return JSONResponse({"ok": True, "entries": list_review_queue(session_id), "custom_spells": get_custom_spells(session_id)})


def custom_spell_upsert_response(session_id: str, user_id: str, spell: dict):
    session, user, error = get_session_and_user(session_id, user_id)
    if error:
        return error
    if user.role != "dm":
        return JSONResponse({"ok": False, "error": "DM only"}, status_code=403)
    if not str(spell.get("name") or "").strip():
        return JSONResponse({"ok": False, "error": "Spell name is required"}, status_code=400)
    saved = upsert_custom_spell(session_id, user_id, spell)
    return JSONResponse({"ok": True, "spell": saved})


def custom_spell_delete_response(session_id: str, user_id: str, spell_id: str):
    session, user, error = get_session_and_user(session_id, user_id)
    if error:
        return error
    if user.role != "dm":
        return JSONResponse({"ok": False, "error": "DM only"}, status_code=403)
    delete_custom_spell(session_id, spell_id)
    return JSONResponse({"ok": True})
