from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from server.http.auth import get_request_user
from server.http.session_access import get_or_restore_session, resolve_session_authority


def _default_post_auth_target(role: str) -> str:
    role_norm = str(role or "").strip().lower()
    if role_norm == "dm":
        return "/campaigns"
    if role_norm == "viewer":
        return "/viewer/watch"
    return "/player/characters"


def _play_boot_context(request: Request) -> dict:
    role = str(request.query_params.get("role") or "viewer").strip().lower()
    if role not in {"dm", "player", "viewer", "assistant_dm"}:
        role = "viewer"
    manifest_role = "dm" if role in {"dm", "assistant_dm"} else role
    # All interactive roles (DM, assistant DM, player, viewer) share the single
    # live play.html runtime. The full runtime (and its core boot scripts) is
    # loaded by the role-gated block inside play.html itself, so boot_scripts is
    # intentionally empty here to avoid double-loading the core modules. Earlier
    # builds shipped a separate "minimal" player/viewer boot shell that stubbed
    # out initUI/initCanvas/_setWsStatus and left players with no map, tabs,
    # tokens, character sheet, or quick actions — see player live-sync regression.
    deferred = [
        "/static/js/ui/onboarding.js?v=20260327",
    ]
    return {
        "play_role": role,
        "boot_manifest_name": manifest_role,
        "boot_scripts": [],
        "deferred_boot_scripts": deferred,
        "include_camp_rest": True,
        "load_dice_module": True,
        "session_id": str(request.query_params.get("session_id") or ""),
        "user_id": str(request.query_params.get("user_id") or ""),
    }


def _reconnect_redirect_for_member(request: Request, ctx: dict):
    """Self-bootstrap a returning, already-authenticated session member on /play.

    When an authenticated player/viewer/DM reloads /play but the URL's user_id/role is
    missing or stale (e.g. after a server restart restored their session under a
    different in-memory slot, or the address bar carries a partial link), resolve their
    real session identity from the auth cookie and redirect to /play with the correct
    user_id/role. This lets the live runtime connect the WebSocket directly instead of
    bouncing the member through /join -> character picker -> POST /api/session/join.

    Returns a RedirectResponse when a correction is needed, otherwise None (render /play
    as-is so the client connects the WebSocket).
    """
    session_id = str(ctx.get("session_id") or "").strip().upper()
    if not session_id:
        return None
    # Only returning members carry a valid auth cookie; strangers fall through to the
    # normal (unchanged) join flow.
    if not get_request_user(request):
        return None
    session = get_or_restore_session(session_id)
    if not session:
        return None

    url_user_id = str(ctx.get("user_id") or "").strip()
    authority = resolve_session_authority(request, session, fallback_user_id=url_user_id)
    resolved_user_id = str(authority.get("resolved_session_user_id") or "").strip()
    # Only redirect when the request resolves to an actual participant in this session.
    if not resolved_user_id or authority.get("matched_via") in (None, "none"):
        return None

    resolved_role = (
        "dm" if authority.get("is_session_dm")
        else (authority.get("participant_role") or str(ctx.get("play_role") or "") or "player")
    )
    url_role = str(ctx.get("play_role") or "").strip().lower()
    # Identity already matches — render directly so the client connects the WebSocket
    # without an extra navigation. This also guarantees no redirect loop.
    if resolved_user_id == url_user_id and resolved_role == url_role:
        return None

    member = session.users.get(resolved_user_id)
    params = dict(request.query_params)
    params["session_id"] = session_id
    params["user_id"] = resolved_user_id
    params["role"] = resolved_role
    if not str(params.get("name") or "").strip() and member is not None:
        params["name"] = getattr(member, "name", "") or ""
    params["returning"] = "1"
    return RedirectResponse("/play?" + urlencode(params), status_code=302)


def build_router(templates, public_domain: str, port: int) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        return templates.TemplateResponse(
            "casual-dnd-login.html",
            {
                "request": request,
                "route_role": "",
                "post_auth_target": "/campaigns",
            },
        )

    @router.get("/play", response_class=HTMLResponse)
    async def play_page(request: Request):
        ctx = {"request": request}
        ctx.update(_play_boot_context(request))
        redirect = _reconnect_redirect_for_member(request, ctx)
        if redirect is not None:
            return redirect
        return templates.TemplateResponse("play.html", ctx)

    @router.get("/campaigns", response_class=HTMLResponse)
    async def campaigns_page(request: Request):
        return templates.TemplateResponse("campaigns.html", {"request": request})

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        return templates.TemplateResponse(
            "casual-dnd-login.html",
            {
                "request": request,
                "route_role": "",
                "post_auth_target": "/campaigns",
            },
        )

    @router.get("/dm", response_class=HTMLResponse)
    async def dm_login(request: Request):
        return templates.TemplateResponse(
            "casual-dnd-login.html",
            {
                "request": request,
                "route_role": "dm",
                "post_auth_target": _default_post_auth_target("dm"),
            },
        )

    @router.get("/player", response_class=HTMLResponse)
    async def player_login(request: Request):
        return templates.TemplateResponse(
            "casual-dnd-login.html",
            {
                "request": request,
                "route_role": "player",
                "post_auth_target": _default_post_auth_target("player"),
            },
        )

    @router.get("/viewer", response_class=HTMLResponse)
    async def viewer_login(request: Request):
        return templates.TemplateResponse(
            "casual-dnd-login.html",
            {
                "request": request,
                "route_role": "viewer",
                "post_auth_target": _default_post_auth_target("viewer"),
            },
        )

    @router.get("/player/characters", response_class=HTMLResponse)
    async def player_character_page(request: Request):
        return templates.TemplateResponse("player-characters.html", {"request": request})

    @router.get("/player/characters/create", response_class=HTMLResponse)
    async def player_character_create_page(request: Request):
        return templates.TemplateResponse("character-creation.html", {"request": request})

    @router.get("/viewer/watch", response_class=HTMLResponse)
    async def viewer_watch_page(request: Request):
        return templates.TemplateResponse("viewer-entry.html", {"request": request})

    @router.get("/join/create")
    async def join_create_page(request: Request):
        query = request.url.query
        target = "/player/characters/create"
        if query:
            target += f"?{query}"
        return RedirectResponse(target, status_code=307)

    @router.get("/join")
    async def join_page(request: Request):
        role = str(request.query_params.get("role") or "player").strip().lower()
        target = "/viewer/watch" if role == "viewer" else "/player/characters"
        query = request.url.query
        if query:
            target += f"?{query}"
        return RedirectResponse(target, status_code=307)

    @router.get("/api/config")
    async def api_config():
        return JSONResponse({"public_domain": public_domain, "port": port})

    return router
