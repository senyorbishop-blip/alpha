from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


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
