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
    core = [
        "/static/js/core/diagnostics.js",
        "/static/js/core/csrf.js",
        "/static/js/state/store.js",
        "/static/js/core/runtime_bridge.js",
        "/static/js/core/boot_shell.js",
        "/static/js/core/ws.js?v=heartbeat-pong-v4",
        "/static/js/core/message_dispatch.js",
    ]
    player = core + [
        "/static/js/render/boot.js",
        "/static/js/render/fog.js",
        "/static/js/render/vision.js",
        "/static/js/ui/player_shell.js",
        "/static/js/ui/tabs.js",
        "/static/js/ui/chat.js",
        "/static/js/ui/chat_log.js",
    ]
    viewer = core + [
        "/static/js/render/boot.js",
        "/static/js/render/fog.js",
        "/static/js/render/vision.js",
        "/static/js/ui/tabs.js",
        "/static/js/ui/chat.js",
        "/static/js/ui/chat_log.js",
    ]
    dm = [
        "/static/js/core/diagnostics.js", "/static/js/core/csrf.js",
        "/static/js/editor/serialization.js", "/static/js/editor/stamp_presets.js",
        "/static/js/editor/terrain_manifest.js", "/static/js/assets/dnd_assets.js",
        "/static/js/editor/asset_initializer.js", "/static/js/editor/asset_renderer.js",
        "/static/js/editor/terrain_renderer.js", "/static/js/editor/placement_controller.js",
        "/static/js/ui/item_image_resolver.js", "/static/js/editor/shop_panel.js",
        "/static/js/editor/shop_view.js", "/static/js/editor/chest_view.js",
        "/static/js/render/combat_fx.js", "/static/js/editor/assets.js",
        "/static/js/ui/asset_library.js", "/static/js/ui/editor_panel.js",
        "/static/js/character/runtime/mapper_to_play.js",
        "/static/js/character/runtime/character_book_runtime.js",
        "/static/js/character/library/character_levelup_modal.js",
        "/static/js/ui/sound_engine.js", "/static/js/ui/narration.js",
        "/static/js/ui/dm_assistant.js", "/static/js/ui/conversation.js",
        "/static/ambient_engine.js", "/static/sfx_engine.js", "/static/tts_client.js",
        "/static/js/map-library.js", "/static/js/map-grid.js", "/static/js/cartographer.js",
        "/static/js/state/store.js", "/static/js/core/runtime_bridge.js",
        "/static/js/core/boot_shell.js", "/static/js/core/ws.js?v=heartbeat-pong-v4",
        "/static/js/core/message_dispatch.js", "/static/js/render/boot.js",
        "/static/js/render/fog.js", "/static/js/render/vision.js",
        "/static/js/ui/token_emotes.js", "/static/js/ui/player_shell.js",
        "/static/js/ui/tabs.js", "/static/js/ui/panel_controls.js",
        "/static/js/ui/character_book.js", "/static/js/character/runtime/character_sheet_runtime.js",
        "/static/js/ui/chat.js", "/static/js/ui/chat_log.js", "/static/js/ui/spotlight.js",
        "/static/js/gameplay/encumbrance.js",
        "/static/js/character/builder/builder_tooltips.js", "/static/js/character/builder/builder_api.js",
        "/static/js/character/builder/builder_validators.js", "/static/js/character/builder/builder_router.js",
        "/static/js/character/builder/builder_state.js",
        "/static/js/character/builder/steps/step_identity.js", "/static/js/character/builder/steps/step_species.js",
        "/static/js/character/builder/steps/step_class.js", "/static/js/character/builder/steps/step_subclass.js",
        "/static/js/character/builder/steps/step_abilities.js", "/static/js/character/builder/steps/step_origins.js",
        "/static/js/character/builder/steps/step_progression.js", "/static/js/character/builder/steps/step_spells.js",
        "/static/js/character/builder/steps/step_equipment.js", "/static/js/character/builder/steps/step_review.js",
        "/static/js/character/builder/builder_shell.js",
    ]
    deferred_dm = [
        "/static/js/ui/onboarding.js?v=20260327", "/static/js/character/spell_runtime.js",
        "/static/js/character/spells_modal.js", "/static/js/character/tabs/actions_tab.js",
        "/static/js/character/tabs/inventory_tab.js", "/static/js/character/tabs/spells_tab.js",
        "/static/js/character/tabs/features_tab.js", "/static/js/character/character_sheet_container.js",
        "/static/js/character/combat_quick_actions.js", "/static/js/character/combat_quick_selectors.js",
        "/static/js/character/combat_quick_bar.js", "/static/js/character/sticky_notes.js",
    ]
    scripts = dm if manifest_role == "dm" else (player if manifest_role == "player" else viewer)
    return {
        "play_role": role,
        "boot_manifest_name": manifest_role,
        "boot_scripts": scripts,
        "deferred_boot_scripts": deferred_dm if manifest_role == "dm" else [],
        "include_camp_rest": manifest_role == "dm",
        "load_dice_module": manifest_role == "dm",
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
