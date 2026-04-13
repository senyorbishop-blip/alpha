import asyncio
import importlib
import sys
import types

from server.integrations import service as integrations_service
from tts_router import TTSRouter


class _StubEngine:
    def __init__(self, ready=True, queue=0):
        self.ready = ready
        self._queue_depth = queue

    async def generate(self, *_args, **_kwargs):
        return b"wav"


def test_tts_router_diagnostics_marks_kokoro_path_without_fallback():
    router = TTSRouter(
        chatterbox=_StubEngine(ready=False),
        dia=_StubEngine(ready=False),
        kokoro=_StubEngine(ready=True),
    )
    audio, engine = asyncio.run(router.route("hello", "system_voice", 1.0, "neutral"))
    assert audio == b"wav"
    assert engine == "kokoro"
    diag = router.diagnostics()
    assert diag["target_engine"] == "kokoro"
    assert diag["engine_used"] == "kokoro"
    assert diag["fallback_active"] is False


def test_kokoro_engine_uses_env_override_paths(monkeypatch):
    class _FakeKokoro:
        def __init__(self, onnx_path, voices_path):
            self.paths = (onnx_path, voices_path)

        def create(self, text, voice, speed, lang):
            return [0.0, 0.0], 24000

    fake_module = types.SimpleNamespace(Kokoro=_FakeKokoro)
    monkeypatch.setitem(sys.modules, "kokoro_onnx", fake_module)
    monkeypatch.setenv("KOKORO_ONNX_PATH", "/tmp/custom-kokoro.onnx")
    monkeypatch.setenv("KOKORO_VOICES_PATH", "/tmp/custom-voices.bin")

    tts_engines = importlib.import_module("tts_engines")
    importlib.reload(tts_engines)
    engine = tts_engines.KokoroEngine()
    engine.load()
    status = engine.status()

    assert engine.ready is True
    assert status["model_path"] == "/tmp/custom-kokoro.onnx"
    assert status["voices_path"] == "/tmp/custom-voices.bin"


def test_integrations_status_includes_tts_stack():
    payload = integrations_service.get_integrations_status_payload()
    narration = payload["narration"]
    assert "tts_stack" in narration
    assert "primary_path" in narration["tts_stack"]
    assert "fallback_path" in narration["tts_stack"]
