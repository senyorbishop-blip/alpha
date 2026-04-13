from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from server.character.rules_catalog import load_rules_catalog
from server.rules.service import (
    custom_spell_delete_response,
    custom_spell_upsert_response,
    enrich_spellbook_response,
    review_queue_response,
)
from server.rules_db import get_srd_item_count

router = APIRouter()


@router.post("/api/rules/spellbook/enrich")
async def api_rules_spellbook_enrich(request: Request):
    body = await request.json()
    return enrich_spellbook_response(
        session_id=str(body.get("session_id") or "").strip(),
        user_id=str(body.get("user_id") or "").strip(),
        character=body.get("character") or {},
    )


@router.get("/api/rules/review-queue")
async def api_rules_review_queue(session_id: str, user_id: str):
    return review_queue_response(session_id, user_id)


@router.post("/api/rules/custom-spells")
async def api_rules_custom_spell(request: Request):
    body = await request.json()
    return custom_spell_upsert_response(
        session_id=str(body.get("session_id") or "").strip(),
        user_id=str(body.get("user_id") or "").strip(),
        spell=body.get("spell") or {},
    )


@router.delete("/api/rules/custom-spells/{spell_id}")
async def api_rules_custom_spell_delete(spell_id: str, session_id: str, user_id: str):
    return custom_spell_delete_response(session_id, user_id, spell_id)


@router.get("/api/srd_items/count")
async def api_srd_item_count():
    return JSONResponse({"count": get_srd_item_count()})


@router.get("/api/rules/catalog/species")
async def api_rules_species_catalog():
    catalog = load_rules_catalog()
    species_rows = catalog.get("species") if isinstance(catalog.get("species"), list) else []
    return JSONResponse({"ok": True, "rulesetId": str(catalog.get("rulesetId") or ""), "species": species_rows})


@router.get("/api/rules/feats")
async def api_rules_feats():
    catalog = load_rules_catalog()
    return JSONResponse(
        {
            "ok": True,
            "rulesetId": str(catalog.get("rulesetId") or ""),
            "origin": catalog.get("featsOrigin") if isinstance(catalog.get("featsOrigin"), list) else [],
            "general": catalog.get("featsGeneral") if isinstance(catalog.get("featsGeneral"), list) else [],
        }
    )


@router.get("/api/rules/backgrounds")
async def api_rules_backgrounds():
    catalog = load_rules_catalog()
    rows = catalog.get("backgrounds") if isinstance(catalog.get("backgrounds"), list) else []
    return JSONResponse({"ok": True, "rulesetId": str(catalog.get("rulesetId") or ""), "backgrounds": rows})


@router.get("/api/rules/spells")
async def api_rules_spells(level: int | None = Query(default=None), class_name: str | None = Query(default=None, alias="class")):
    catalog = load_rules_catalog()
    rows = catalog.get("spells") if isinstance(catalog.get("spells"), list) else []
    if level is not None:
        rows = [row for row in rows if int(row.get("level", -1)) == level]
    if class_name:
        class_key = class_name.strip().lower()
        rows = [
            row
            for row in rows
            if any(str(name).strip().lower() == class_key for name in (row.get("classes") or []))
        ]
    return JSONResponse(
        {"ok": True, "rulesetId": str(catalog.get("rulesetId") or ""), "count": len(rows), "spells": rows}
    )
