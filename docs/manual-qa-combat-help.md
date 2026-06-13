# Manual QA Script — Combat Help, Tutorials & Combat Guidance

Stage: Combat Coach + Help Hub integration
Files touched: `onboarding.js`, `player_shell.js`, `play.html`
Roles to test: DM, Player, Viewer

---

## Pre-conditions

1. Two browsers open: one DM, one Player (use incognito for the second).
2. Start from a fresh session with at least one map loaded.
3. Player has a token with a movement speed > 0 (e.g. speed = 30 ft).

---

## Section 1 — New Player Join & First Tour

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | New Player joins session for the first time (clear localStorage first). | Auto-show walkthrough modal appears after ~900ms with "Welcome, Adventurer" step. |
| 1.2 | Step through the 5-step player walkthrough using Next →. | Each step shows correct icon, title, body, and tip. Progress bar advances. |
| 1.3 | Press Escape or click backdrop. | Modal closes. localStorage key `tavern_onboard_seen_player_<userId>` is set. |
| 1.4 | Reload page. | Walkthrough does NOT auto-show again (already seen). |

---

## Section 2 — Help Hub Access

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | Click the topbar **?** button (top-right). | Help Hub modal opens showing a grid of topic cards. Role label shows "Player". |
| 2.2 | Verify topic cards include: New Player Tour, Quick Refresh, Combat Quick Guide, Movement Guide, Spells Guide, Inventory Guide. | All 6 cards present. |
| 2.3 | Click **Combat Quick Guide** card. | Combat guide opens as a multi-step guide (4 steps). Step through with Next →. |
| 2.4 | Open player dashboard (click the dashboard area / My Character from left rail). | Dashboard shows "Combat Guide" and "Help Hub" buttons. |
| 2.5 | Click **Help Hub** button in dashboard. | Help Hub modal opens. |
| 2.6 | Click **Combat Guide** button in dashboard. | Help Hub modal opens (defaults to showHelpHub). |
| 2.7 | Open character sheet. In the Advanced edit pages bar, find the **Combat / Actions** tab. | Tab label reads "Combat / Actions" (not just "Actions"). |

---

## Section 3 — DM Starts Combat

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | DM: Open Combat tab on right sidebar. | "Start Combat" button visible. |
| 3.2 | DM: Click Start Combat. | Combat tracker populates with all tokens from the current map. Round 1 label appears. |
| 3.3 | Player browser: Observe the Combat tab button in the right sidebar. | Combat tab glows red/orange (combat-glow animation). |
| 3.4 | Player browser: Observe a hint bar above the combat list. | Non-blocking hint: "Combat has started. Open Combat to see turn order, movement, actions, and End Turn." visible for ~7 seconds. |
| 3.5 | Player browser: Check dashboard and character sheet Actions tab. | Dashboard "Combat Guide" button glows. Character sheet "Combat / Actions" tab has red border attention. |

---

## Section 4 — Player Opens Combat, Glow Stops

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | Player: Click the Combat tab button. | Tab opens. Glow animation stops immediately. Badge clears. |
| 4.2 | Player: Switch to Party tab. | Combat tab re-glows (still active combat, not player's turn). |

---

## Section 5 — Player Turn: YOUR TURN State

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | DM: Advance turn to the Player's combatant. | Player's Combat tab button switches from red glow to teal YOUR TURN animation. "YOUR TURN" micro-label appears below the tab name. Badge shows ★. |
| 5.2 | Player browser: Check hint bar. | Hint: "Your turn. Open Combat, move, choose an action/spell, then End Turn." appears. |
| 5.3 | Player: Click Combat tab. | YOUR TURN glow stops. Combat Coach checklist appears inside the panel above the movement row. |
| 5.4 | Coach checklist shows 5 items: Move (X ft remaining), Action, Bonus Action, Reaction reminder, End Turn. | All 5 items visible. |
| 5.5 | Coach shows a class-specific hint for the player's class (e.g. "Bonus action: Rage" for Barbarian). | Class hint visible at the bottom of the checklist. |
| 5.6 | Player: Switch to Party tab. | Combat tab re-glows with YOUR TURN teal glow (still player's turn, not on Combat tab). |
| 5.7 | Player: Return to Combat tab. | Glow stops, coach re-renders. |

---

## Section 6 — Player Movement

| Step | Action | Expected |
|------|--------|----------|
| 6.1 | Player: Drag token within speed limit (e.g. 15 ft of 30 ft). | Token moves. Combat panel shows updated Used/Remaining ft in the move row. |
| 6.2 | Coach checklist Move item shows updated remaining ft. | "Move (15 ft remaining)" reflects current state. |
| 6.3 | Player: Try to move another token that is NOT their own during their turn. | No movement occurs (tokens reject moves for non-owned tokens). |
| 6.4 | Player: Try to move PAST their speed limit. | Token is clamped to max reachable position. Movement panel shows 0 ft remaining. |
| 6.5 | Player: Click their token again and try to move further. | Movement denied toast appears: "No movement left this turn. Use Dash to add more. [What does this mean?]" The help link is clickable. |
| 6.6 | Click **"What does this mean?"** link. | Opens movement/combat help card via `AppOnboarding.showHelp('combat')`. |

---

## Section 7 — Dash & Disengage

| Step | Action | Expected |
|------|--------|----------|
| 7.1 | Player: Click **Dash** button in the move row. | Movement total doubles. Remaining ft updates. "dash" marker appears in move row summary. |
| 7.2 | Player: Click **Disengage** toggle. | Button shows "Disengaged" highlighted. State persists until End Turn. |
| 7.3 | Player: Click Difficult Terrain toggle. | "Difficult Terrain: ON" shown. Movement cost becomes 2x. |

---

## Section 8 — End Turn

| Step | Action | Expected |
|------|--------|----------|
| 8.1 | Player: Click **End Turn** in the move row. | Turn advances to next combatant. Coach checklist clears from combat panel. |
| 8.2 | New combatant is a non-player token. | Combat tab shows regular combat-glow (not YOUR TURN). Coach is not visible (not player's turn). |
| 8.3 | DM: Advance turn back to the player. | YOUR TURN state reappears. Hint fires again. Coach renders again. |

---

## Section 9 — Viewer

| Step | Action | Expected |
|------|--------|----------|
| 9.1 | Open session in a third browser as Viewer. | Viewer can see combat state in the Combat tab (initiative list, round label). |
| 9.2 | Viewer: Check Combat tab. | No coach checklist visible. No End Turn button. No Dash/Disengage controls. |
| 9.3 | Viewer: Click topbar ? button. | Help Hub opens with viewer-appropriate topics: Viewer Tour, Viewer Powers, Combat Guide. |
| 9.4 | Verify viewer does NOT see "New Player Tour" or "DM Controls" in their hub. | Only viewer topics shown. |

---

## Section 10 — DM Combat Controls

| Step | Action | Expected |
|------|--------|----------|
| 10.1 | DM: Open Combat tab. | Full DM combat controls visible: Prev, Next, End, Round label, add combatant row. |
| 10.2 | DM: Click the ? button in the combat header. | Help Hub opens for DM with DM-appropriate topics. |
| 10.3 | DM: No coach checklist visible. | Coach checklist is player-only; DM sees only standard combat controls. |
| 10.4 | DM: End combat. | All glow/badges clear on Player browser. Coach clears. Hint bar hides. |

---

## Section 11 — Empty / Error States

| Step | Action | Expected |
|------|--------|----------|
| 11.1 | Player with no token on map. | Dashboard shows "No owned token on the map yet. Open My Character to place or claim your token." |
| 11.2 | Player opens Combat tab before combat starts. | Combat tab shows "No combat active" empty state. No coach visible. |
| 11.3 | Player opens Spells tab with no spells. | Empty state message visible (handled by existing spells tab). Help ? button available. |

---

## Pass / Fail Criteria

- All glow states render without JavaScript errors in the console.
- Coach checklist does not appear for DM or Viewer.
- YOUR TURN text only appears for the Player whose token is the active combatant.
- Help Hub opens from topbar ?, combat header ?, dashboard Help Hub button, and dashboard Combat Guide button.
- Movement denial messages include "What does this mean?" link.
- Clicking help links opens the correct guide.
- No regressions in existing combat, inventory, or party panels.
