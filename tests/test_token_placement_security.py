"""Regression checks for secure staged-token placement."""

from __future__ import annotations

import inspect

from server.handlers import handle_message
from server.handlers import token_placement_secure


def test_token_placed_dispatch_uses_secure_handler():
    source = inspect.getsource(handle_message)

    assert '"token_placed":     handle_token_placed_secure' in source


def test_secure_token_placement_uses_filtered_token_event_broadcast():
    source = inspect.getsource(token_placement_secure.handle_token_placed_secure)

    assert "_broadcast_token_event" in source
    assert "token_placed" in source
    assert "manager.broadcast(session.id" not in source
