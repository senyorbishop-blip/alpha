"""PDF import safety limits."""

from __future__ import annotations

import concurrent.futures
import json

from server.integrations import service


def _payload(response) -> dict:
    return json.loads((response.body or b"{}").decode("utf-8"))


def test_pdf_import_rejects_empty_file():
    response = service.parse_character_pdf_response(b"")

    assert response.status_code == 400
    assert "Empty file" in _payload(response)["error"]


def test_pdf_import_rejects_oversized_file(monkeypatch):
    monkeypatch.setenv("CHARACTER_PDF_MAX_BYTES", "8")

    response = service.parse_character_pdf_response(b"%PDF-1.7\n" + b"x" * 32)

    assert response.status_code == 413
    assert "too large" in _payload(response)["error"]


def test_pdf_import_rejects_non_pdf_header(monkeypatch):
    monkeypatch.setenv("CHARACTER_PDF_MAX_BYTES", str(1024 * 1024))

    response = service.parse_character_pdf_response(b"not a pdf")

    assert response.status_code == 400
    assert "does not look like a PDF" in _payload(response)["error"]


def test_pdf_import_times_out_before_returning_parser_result(monkeypatch):
    class FakeFuture:
        def __init__(self):
            self.cancelled = False

        def result(self, timeout=None):
            raise concurrent.futures.TimeoutError()

        def cancel(self):
            self.cancelled = True
            return True

    class FakeExecutor:
        def submit(self, fn, data):
            return FakeFuture()

    monkeypatch.setattr(service, "_PDF_PARSE_EXECUTOR", FakeExecutor())
    monkeypatch.setenv("CHARACTER_PDF_PARSE_TIMEOUT_SECONDS", "1")

    response = service.parse_character_pdf_response(b"%PDF-1.7\nfillable sheet")

    assert response.status_code == 408
    assert "timed out" in _payload(response)["error"]


def test_pdf_import_accepts_valid_pdf_after_parser(monkeypatch):
    monkeypatch.setattr(service, "parse_character_pdf_data", lambda data: {"name": "Test Hero"})

    response = service.parse_character_pdf_response(b"%PDF-1.7\nfillable sheet")
    payload = _payload(response)

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["character"]["name"] == "Test Hero"
