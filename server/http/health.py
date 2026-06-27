"""
server/http/health.py — liveness & readiness endpoints.

  GET /health   liveness  — process is up. Never touches the DB. Always 200.
  GET /healthz  alias of /health (k8s convention).
  GET /ready    readiness — verifies the SQLite DB is reachable. 200 or 503.

Wire into the app in main.py:

    from server.http.health import router as health_router
    app.include_router(health_router)
"""
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

router = APIRouter()

_STARTED_AT = time.time()


def _read_version() -> str:
    try:
        from server.paths import REPO_ROOT
        vf = REPO_ROOT / "VERSION"
        if vf.exists():
            return vf.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "unknown"


_VERSION = _read_version()


@router.get("/health")
@router.get("/healthz")
async def health() -> JSONResponse:
    """Liveness: the process is running. Cheap, dependency-free."""
    return JSONResponse(
        {
            "status": "ok",
            "version": _VERSION,
            "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        }
    )


def _probe_db() -> None:
    # Imported lazily so a DB import error can't break liveness.
    from server.db import get_conn

    conn = get_conn()
    try:
        conn.execute("SELECT 1").fetchone()
    finally:
        conn.close()


@router.get("/ready")
async def ready() -> JSONResponse:
    """Readiness: can the app serve traffic (DB reachable)?"""
    try:
        # SQLite calls are blocking — keep them off the event loop.
        await run_in_threadpool(_probe_db)
    except Exception as exc:  # noqa: BLE001 — readiness must report, not raise
        return JSONResponse(
            {"status": "not_ready", "db": "unavailable", "error": str(exc)[:200]},
            status_code=503,
        )
    return JSONResponse({"status": "ready", "db": "ok", "version": _VERSION})
