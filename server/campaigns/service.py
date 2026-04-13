import asyncio

from fastapi.responses import JSONResponse

from server.db import delete_campaign, list_campaigns, load_campaign, save_campaign_async
from server.http.session_access import restore_session
from server.session import get_session


def list_campaigns_response():
    return JSONResponse(list_campaigns())


async def save_campaign_response(campaign_id: str, body: dict):
    user_id = body.get("user_id", "")
    session = get_session(campaign_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    user = session.users.get(user_id)
    if not user or user.role != "dm":
        return JSONResponse({"error": "Only DM can save"}, status_code=403)
    if "name" in body:
        session.name = body["name"]
    ok = await save_campaign_async(session)
    return JSONResponse({"ok": ok})


async def resume_campaign_response(campaign_id: str):
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, load_campaign, campaign_id)
    if not data:
        return JSONResponse({"error": "Campaign not found"}, status_code=404)
    existing = get_session(campaign_id)
    if existing:
        dm = next((u for u in existing.users.values() if u.role == "dm"), None)
        dm_id = dm.id if dm else ""
        return JSONResponse({
            "session_id": existing.id,
            "user_id": dm_id,
            "player_invite": existing.player_invite,
            "viewer_invite": existing.viewer_invite,
            "dm_name": data["dm_name"],
        })
    session, dm_id = restore_session(data)
    if not data.get("dm_id"):
        await save_campaign_async(session)
    return JSONResponse({
        "session_id": session.id,
        "user_id": dm_id,
        "player_invite": session.player_invite,
        "viewer_invite": session.viewer_invite,
        "dm_name": data["dm_name"],
    })


def delete_campaign_response(campaign_id: str, body: dict):
    session = get_session(campaign_id)
    if session:
        user = session.users.get(body.get("user_id", ""))
        if user and user.role != "dm":
            return JSONResponse({"error": "Forbidden"}, status_code=403)
    delete_campaign(campaign_id)
    return JSONResponse({"ok": True})
