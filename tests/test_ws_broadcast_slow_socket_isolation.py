"""Regression tests for live-sync stability under half-open / wedged sockets.

A half-open TCP socket (sleeping laptop, dropped wifi, backgrounded phone, NAT
idle-timeout) does not fail fast: ``send_text`` blocks once the transport buffer
fills. The broadcaster must not let one such recipient stall live sync for the
rest of the session — sends fan out concurrently and a wedged socket is bounded
by a per-send timeout and reaped.
"""
import asyncio
import os

import pytest

from server.connections import ConnectionManager


class HealthyWebSocket:
    def __init__(self):
        self.sent = []

    async def accept(self):
        return None

    async def close(self, code=1000, reason=""):
        return None

    async def send_text(self, payload):
        self.sent.append(payload)


class WedgedWebSocket:
    """Simulates a half-open socket whose send never completes."""

    def __init__(self):
        self.send_started = asyncio.Event()

    async def accept(self):
        return None

    async def close(self, code=1000, reason=""):
        return None

    async def send_text(self, payload):
        self.send_started.set()
        # Block far longer than any test timeout — mimics a drain that never
        # resolves because the peer is gone.
        await asyncio.sleep(3600)


def test_wedged_socket_does_not_block_healthy_recipients(monkeypatch):
    monkeypatch.setenv("WS_SEND_TIMEOUT_SECONDS", "1")

    async def run_case():
        manager = ConnectionManager()
        healthy = HealthyWebSocket()
        wedged = WedgedWebSocket()
        await manager.connect("sess", "wedged-user", wedged, role="player")
        await manager.connect("sess", "healthy-user", healthy, role="player")

        started = asyncio.get_running_loop().time()
        await manager.broadcast("sess", {"type": "token_moved", "payload": {"x": 1}})
        elapsed = asyncio.get_running_loop().time() - started

        # The healthy client received the frame immediately, not after waiting
        # behind the wedged client's full hang.
        assert healthy.sent, "healthy recipient must receive the broadcast"
        # Broadcast returns once the wedged send hits its (short) timeout, not
        # after the 3600s hang. Comfortably under 1s proves no head-of-line block.
        assert elapsed < 2.0, f"broadcast blocked on wedged socket for {elapsed:.2f}s"

        # The wedged socket is reaped so future broadcasts skip it entirely.
        assert not manager.is_connected("sess", "wedged-user")
        assert manager.is_connected("sess", "healthy-user")

    asyncio.run(run_case())


def test_send_to_wedged_socket_times_out_and_reaps(monkeypatch):
    monkeypatch.setenv("WS_SEND_TIMEOUT_SECONDS", "1")

    async def run_case():
        manager = ConnectionManager()
        wedged = WedgedWebSocket()
        await manager.connect("sess2", "u", wedged, role="player")

        started = asyncio.get_running_loop().time()
        ok = await manager.send_to("sess2", "u", {"type": "ping"})
        elapsed = asyncio.get_running_loop().time() - started

        assert ok is False, "send to a wedged socket must report failure"
        assert elapsed < 2.0, f"send_to blocked for {elapsed:.2f}s instead of timing out"
        assert not manager.is_connected("sess2", "u"), "wedged socket must be reaped"

    asyncio.run(run_case())


def test_healthy_broadcast_still_delivers_to_all(monkeypatch):
    monkeypatch.delenv("WS_SEND_TIMEOUT_SECONDS", raising=False)

    async def run_case():
        manager = ConnectionManager()
        a = HealthyWebSocket()
        b = HealthyWebSocket()
        c = HealthyWebSocket()
        await manager.connect("sess3", "a", a, role="dm")
        await manager.connect("sess3", "b", b, role="player")
        await manager.connect("sess3", "c", c, role="player")

        await manager.broadcast("sess3", {"type": "state_sync", "payload": {}}, exclude_user="a")

        assert not a.sent, "excluded user must not receive the broadcast"
        assert b.sent and c.sent, "all non-excluded users must receive the broadcast"

    asyncio.run(run_case())
