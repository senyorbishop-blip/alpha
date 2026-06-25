# Multi-role live-session smoke test

This repo includes a Playwright smoke/regression test that boots the live `play.html` runtime the same way a stream session uses it: one DM browser context, one Player browser context, and one Viewer browser context connected to the same FastAPI/WebSocket session.

## Run locally

```bash
npm install
npx playwright install chromium
npx playwright test tests/e2e/live-session-regression.spec.ts
```

The Playwright config starts the app automatically on `127.0.0.1:8765` with an isolated data directory under `.tmp/playwright-data`. To point at an already-running server instead:

```bash
PLAYWRIGHT_SKIP_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:8765 npx playwright test tests/e2e/live-session-regression.spec.ts
```

## What it covers

- DM, Player, and Viewer live-shell boot and role-specific controls.
- WebSocket connect, heartbeat stability, Player reload/reconnect, and authoritative snapshot hydration.
- Player/Viewer role-safety attempts against DM/editor/token actions.
- Visible token creation/sync and hidden/staged/fog-hidden token filtering.
- Player-owned token movement preview/commit without preview broadcast spam.
- Combat movement revision ordering so stale/lower-revision local state cannot overwrite the committed server position.
- Active-character Quick Actions hydration for weapon, spell, and item-granted spell cards, with diagnostics instead of crashes.
- Short-rest and long-rest sync across token/profile/runtime/inventory/Quick Actions, including reconnect after rest.
- Metadata-only payload-size diagnostics for initial Player/Viewer WebSocket payloads. The test fails if a basic join frame exceeds the hard error threshold; it never prints raw payload content.

## CI

The existing `Playwright E2E` workflow runs `npm run test:e2e`, so the smoke test is included in CI with the rest of the browser suite.
