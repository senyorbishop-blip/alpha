import os
import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from fastapi.responses import JSONResponse

from server.handlers.cartographer import get_image_provider
from server.utils.pdf_parser import parse_character_pdf_data


def _tts_runtime_summary() -> dict:
    try:
        import tts_server as _tts_server  # lazy import; non-fatal if unavailable
    except Exception:
        return {
            "available": False,
            "startup_ok": False,
            "primary_path": "browser_fallback",
            "fallback_path": "browser_fallback",
            "kokoro_ready": False,
            "notes": ["TTS server module not importable; browser fallback path only."],
        }

    kokoro = getattr(_tts_server, "_kokoro", None)
    startup_ok = bool(getattr(_tts_server, "_startup_ok", False))
    stack = getattr(_tts_server, "_stack_summary", {}) or {}
    return {
        "available": True,
        "startup_ok": startup_ok,
        "primary_path": stack.get("primary_path", "browser_fallback"),
        "fallback_path": stack.get("fallback_path", "browser_fallback"),
        "kokoro_ready": bool(getattr(kokoro, "ready", False)),
        "notes": stack.get("notes", []),
    }


def extract_ddb_character_id(value: str) -> str:
    """Extract a D&D Beyond character ID from IDs, character URLs, or sheet PDF URLs."""
    raw = str(value or "").strip()
    if not raw:
        return ""

    # Fast path for the normal UI hint: just the numeric character ID.
    if re.fullmatch(r"\d+", raw):
        return raw

    decoded = unquote(raw)
    candidates = [decoded]

    try:
        parsed = urlparse(decoded if re.match(r"^[a-z][a-z0-9+.-]*://", decoded, re.I) else f"https://{decoded}")
        path = unquote(parsed.path or "")
        candidates.append(path)

        query = parse_qs(parsed.query or "")
        for key in ("characterId", "character_id", "id"):
            for item in query.get(key, []):
                if re.fullmatch(r"\d+", str(item or "").strip()):
                    return str(item).strip()

        # Public character URLs are commonly /characters/123456789 or
        # /profile/<user>/characters/123456789.
        match = re.search(r"/(?:profile/[^/]+/)?characters/(\d+)(?:[/?#]|$)", path, re.I)
        if match:
            return match.group(1)

        # Exported sheet links look like /sheet-pdfs/username_123456789.pdf.
        # Usernames may contain digits, so do not collapse every digit in the URL.
        match = re.search(r"/sheet-pdfs/[^/?#]*_(\d+)\.pdf(?:[?#].*)?$", path, re.I)
        if match:
            return match.group(1)
    except Exception:
        pass

    for candidate in candidates:
        match = re.search(r"(?:^|[^0-9])characters/(\d+)(?:[^0-9]|$)", candidate, re.I)
        if match:
            return match.group(1)
        match = re.search(r"_(\d+)\.pdf(?:[^0-9]|$)", candidate, re.I)
        if match:
            return match.group(1)

    # Last-resort parsing for pasted text. Prefer the last group so
    # `user165_87369199.pdf` resolves to `87369199`, not `16587369199`.
    groups = re.findall(r"\d+", decoded)
    return groups[-1] if groups else ""


async def fetch_ddb_character_response(char_id: str):
    char_id = extract_ddb_character_id(char_id)
    if not char_id:
        return JSONResponse({"error": "Invalid D&D Beyond character ID or URL"}, status_code=400)
    url = f"https://character-service.dndbeyond.com/character/v5/character/{char_id}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
        if response.status_code != 200:
            if response.status_code in {401, 403, 404, 409}:
                return JSONResponse(
                    {"error": "D&D Beyond could not return that character. Make sure the sheet is public and paste the numeric character ID, a /characters/ URL, or the ID from the sheet PDF link."},
                    status_code=502,
                )
            return JSONResponse({"error": f"D&D Beyond returned {response.status_code}"}, status_code=502)
        return JSONResponse(response.json())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)



def parse_character_pdf_response(data: bytes):
    if not data:
        return JSONResponse({"error": "Empty file received."}, status_code=400)
    try:
        result = parse_character_pdf_data(data)
    except ImportError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"ok": True, "character": result})



def get_integrations_status_payload() -> dict:
    image_provider = get_image_provider()
    image_provider_name = getattr(image_provider, "name", image_provider.__class__.__name__).replace("ImageProvider", "").lower()
    gemini_configured = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    elevenlabs_configured = bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())
    openai_configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    replicate_configured = bool(os.environ.get("REPLICATE_API_TOKEN", "").strip())
    stability_configured = bool(os.environ.get("STABILITY_API_KEY", "").strip())
    anthropic_configured = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

    if gemini_configured:
        effective_narration_provider = "gemini_tts"
    elif elevenlabs_configured:
        effective_narration_provider = "elevenlabs"
    elif openai_configured:
        effective_narration_provider = "openai_tts"
    else:
        effective_narration_provider = "browser_fallback"

    return {
        "narration": {
            "gemini_tts_configured": gemini_configured,
            "elevenlabs_configured": elevenlabs_configured,
            "openai_tts_configured": openai_configured,
            "effective_provider": effective_narration_provider,
            "tts_stack": _tts_runtime_summary(),
        },
        "cartographer": {
            "image_provider": image_provider_name,
            "openai_configured": openai_configured,
            "replicate_configured": replicate_configured,
            "stability_configured": stability_configured,
            "stability_deprecated": True,
            "anthropic_configured": anthropic_configured,
        },
    }



def integrations_status_response():
    return JSONResponse(get_integrations_status_payload())
