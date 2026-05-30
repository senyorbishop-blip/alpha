# Manual QA Checklist: Live Session Smoke Test

Use this checklist after changes that can affect the live tabletop, role entry, WebSocket sync, character sheets, inventory, viewer behavior, or combat. Run it with separate browser tabs/windows or separate profiles so DM, Player, and Viewer session state are isolated.

## Setup

- Start the app from the repository root.
- Use one DM account/session, one Player account/session, and one Viewer account/session when possible.
- Keep the browser console open for each role and note any uncaught errors.
- Record the session/campaign used, browser(s), and date of the QA pass.

## Checklist

| Step | Role(s) | Expected result | Pass/Notes |
| --- | --- | --- | --- |
| 1. DM can create/open session | DM | DM reaches the campaign/session flow and can enter `/play` without boot errors. | |
| 2. Player can join | Player | Player reaches the character flow, selects or creates a character if required, and enters the same live session. | |
| 3. Viewer can join | Viewer | Viewer enters through the viewer watch flow and reaches the live session without DM tools or character-only redirects. | |
| 4. DM can open map | DM | The map area renders, existing scene/map state appears, and map controls are usable. | |
| 5. Token placement works | DM, Player | DM can place a token; if Player-owned placement is supported for the tested flow, Player token ownership and visibility behave as expected. | |
| 6. Character sheet opens | Player, DM | A character sheet/book can be opened and shows core stats without console errors. | |
| 7. Inventory opens | Player, DM | Inventory tab/panel opens and item/gold/encumbrance surfaces render. | |
| 8. Notes field can be tested | DM | DM notes field accepts text, saves, and still appears after a refresh/reconnect if persistence is expected. | |
| 9. Viewer appears in roster | DM, Viewer | Viewer is visible in the roster/presence UI and disconnect/reconnect status updates correctly. | |
| 10. Viewer power can be granted if supported | DM, Viewer | DM can grant a supported viewer power; Viewer sees it; use/approval/cooldown behavior matches the power configuration. | |
| 11. Combat can start | DM, Player | DM can start or update combat with at least one token; turn order/active combat UI appears. | |
| 12. HP/AC display can be checked | DM, Player | Token/character HP and AC surfaces are visible where expected and HP updates sync between roles. | |

## Quick regression notes

- Confirm DM-only controls are not visible or actionable for Viewer.
- Confirm Player cannot move or edit tokens they do not own, especially during combat.
- Confirm Viewer does not receive hidden tokens or restricted content unless explicitly allowed.
- Confirm chat/log panels still update after at least one message or system event.
- Confirm reconnecting one role does not clear map, combat, inventory, or roster state for the other roles.

## Stage 0 outcome

1. **What changed:** Added a developer-facing manual QA checklist for live-session smoke coverage.
2. **Files changed:** `docs/manual-qa-live-session.md`.
3. **How to test it:** Follow the checklist with DM, Player, and Viewer clients after live-session changes.
4. **Risks / follow-up work:** This checklist is manual and does not replace automated tests. Expand it with screenshots or issue links when future stages add or move runtime features.
