import base64

from fastapi.responses import JSONResponse

from server.handlers.narration import _audio_duration_ms, _generate_tts, _resolve_voice_config


async def narrate_response(body: dict):
    text = str(body.get("text") or "").strip()[:2000]
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    voice_preset = str(body.get("voice_preset") or body.get("voice_id") or "").strip()
    config = _resolve_voice_config(voice_preset)
    audio_bytes, tts_meta = await _generate_tts(
        text=text,
        preset=config["preset"],
        voice_id=config["voice_id"],
        model_id=config["model_id"],
        settings=config["settings"],
    )
    if audio_bytes is None:
        return JSONResponse({
            "tts_provider": tts_meta.get("provider", "browser_fallback"),
            "tts_cache_hit": bool(tts_meta.get("cache_hit")),
            "tts_fallback_reason": tts_meta.get("reason") or "premium_unavailable",
            "fallback_voice": config.get("fallback"),
        })

    mime_type = tts_meta.get("mime_type") or "audio/mpeg"
    audio_duration_ms = _audio_duration_ms(audio_bytes, mime_type)
    return JSONResponse({
        "audio_data_uri": f"data:{mime_type};base64,{base64.b64encode(audio_bytes).decode('ascii')}",
        "audio_duration_ms": audio_duration_ms,
        "tts_provider": tts_meta.get("provider", "browser_fallback"),
        "tts_cache_hit": bool(tts_meta.get("cache_hit")),
        "fallback_voice": config.get("fallback"),
    })
