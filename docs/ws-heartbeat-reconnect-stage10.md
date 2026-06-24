# WebSocket Heartbeat & Reconnect Guardrails (Stage 10)

## Purpose

P10 protects the live table from false disconnects and reconnect storms while players are under heavy browser load, especially during combat, fog rendering, token movement, or multi-tab testing.

## Current live behavior

- The server heartbeat loop in `main.py` sends `ping` every 30 seconds.
- The server closes only after 60 seconds without liveness.
- The server receive loop refreshes liveness on any valid decoded frame, not just `pong`.
- Invalid/undecodable frames do not refresh liveness.
- `pong` refreshes liveness but is skipped from gameplay dispatch.
- The client replies to `ping` inside `client/static/js/core/ws.js` before gameplay dispatch.
- The client reconnects in-place and does not reload the page.
- The client does not reconnect a socket that was explicitly replaced by a newer socket owner.

## Policy guardrails

- Timeout must remain at least two heartbeat intervals.
- Heartbeat pings must never be routed into gameplay handlers.
- Any valid gameplay frame should count as liveness so active play cannot be disconnected simply because a pong is delayed.
- Garbage frames must not keep a dead socket alive.
- Reconnect recovery must be in-place through `AppWS.connectWS()`, not page reload/navigation.
- Replaced sockets must not reconnect, otherwise duplicate tabs or boot retries can create reconnect wars.

## Focused tests

Run:

```bash
python -m pytest tests/test_p10_heartbeat_reconnect_policy.py tests/test_ws_heartbeat_server.py tests/test_ws_heartbeat_pong_client.py tests/test_ws_single_owner_reconnect_storm.py tests/test_ws_lifecycle_hardening.py -v --tb=short
```

## Follow-up implementation note

`server/utils/ws_heartbeat_policy.py` centralises the desired timeout math and frame-dispatch decisions. The current endpoint still owns the live heartbeat loop. A future local edit can wire the endpoint defaults to `heartbeat_policy_from_env()` once `main.py` is being edited directly, then expose:

- `WS_HEARTBEAT_INTERVAL_SECONDS`
- `WS_HEARTBEAT_TIMEOUT_SECONDS`

The defaults should remain 30/60 unless real production telemetry shows they need to be widened.
