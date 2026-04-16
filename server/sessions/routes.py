from fastapi import APIRouter, File, Request, UploadFile

from server.paths import MAPS_DIR
from server.sessions.service import (
    create_session_response,
    delete_session_token_response,
    join_session_response,
    lobby_response,
    session_authority_response,
    session_info_response,
    session_invites_response,
    upload_token_image_response,
)

router = APIRouter()


@router.post("/api/session/create")
async def api_create_session(request: Request):
    return await create_session_response(request, await request.json())


@router.post("/api/session/join")
async def api_join_session(request: Request):
    return await join_session_response(request, await request.json())


@router.get("/api/session/{session_id}/invites")
async def api_session_invites(session_id: str, user_id: str = ""):
    return session_invites_response(session_id, user_id)


@router.get("/api/session/{session_id}/info")
async def api_session_info(session_id: str):
    return session_info_response(session_id)


@router.get("/api/session/{session_id}/lobby")
async def api_lobby(request: Request, session_id: str, role: str = "", player_key: str = "", user_name: str = ""):
    return lobby_response(request, session_id, role=role, player_key=player_key, user_name=user_name)


@router.post("/api/session/{session_id}/token/{token_id}/image")
async def upload_token_image(session_id: str, token_id: str, user_id: str, file: UploadFile = File(...)):
    return await upload_token_image_response(session_id, token_id, user_id, file, MAPS_DIR)


@router.delete("/api/session/{session_id}/token/{token_id}")
async def api_delete_session_token(request: Request, session_id: str, token_id: str):
    return await delete_session_token_response(request, session_id, token_id)


@router.get("/api/session/{session_id}/authority")
async def api_session_authority(request: Request, session_id: str, user_id: str = ""):
    return session_authority_response(request, session_id, user_id)
