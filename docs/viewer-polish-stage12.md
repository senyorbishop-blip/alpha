# Viewer Polish Guardrails (Stage 12)

## Purpose

P12 keeps viewer interaction fun and stream-friendly without turning viewers into players or assistant-DMs.

Viewer polish should improve feedback, clarity, and spectator delight while preserving strict server authority and role separation.

## Live ownership

- Server viewer-power authority lives in `server/handlers/viewer_powers.py`.
- WebSocket role gating lives in `server/handlers/ws_permissions.py`.
- Viewer FX/client helper ownership lives in `client/static/js/gameplay/viewer_powers.js` through `window.AppGameplayViewer`.
- Viewer chat-feed rendering remains owned by `client/static/js/ui/chat_log.js`.

## Allowed viewer actions

Viewer WebSocket messages should stay limited to:

- `ping`
- `pong`
- `viewer_power_use`
- `viewer_cursor_update`
- `viewer_emote`
- `poll_vote`

Anything that grants powers, revokes powers, changes presence settings, moves tokens, edits fog, edits combat, or sends normal player chat must remain blocked for the viewer role.

## UX guardrails

- Viewer powers must clearly explain target mode: token target, map point, line/cone/source token, or aura.
- Cooldowns should be visible before use.
- FX overlays must be non-interactive and self-cleaning so they do not block map clicks or build up DOM nodes.
- Viewer power recaps should be readable for stream and DM moderation.
- Viewer feedback should be exciting but never override DM/player authority.

## Focused tests

Run:

```bash
python -m pytest tests/test_p12_viewer_polish_guardrails.py tests/test_viewer_power_fx_feedback.py tests/test_integration_viewer_powers_tab.py tests/test_ws_role_policy.py -v --tb=short
```

## Follow-up implementation note

The next visual pass can improve the viewer panel itself: clearer empty states, better disabled-state copy for cooldown/no-charge powers, and less disruptive reduced-motion FX. Keep these changes inside the viewer modules and update P12 tests in the same patch.
