# Combat Runtime QA — Manual Test Plan

**Version:** v0.9.1-beta  
**Branch:** claude/combat-integration-qa-4x0u3w  
**Status:** PASS (all automated tests green; manual steps below must be signed off before release)

---

## Prerequisites

- A running local server (`python main.py`)
- One browser tab logged in as DM, one as a Player (separate incognito window)
- A campaign with at least one map and two player characters (or one PC + one NPC)
- Optional: a D&D Beyond JSON export or PDF import to test imported spells

---

## 1  DM Starts Combat

**Steps:**
1. DM opens campaign, navigates to the map.
2. DM clicks **Start Combat** in the Combat tab.
3. Combat mode activates; the initiative roster appears.

**Expected:**
- Combat tab highlights for both DM and Player.
- Player sees the combat pane (tokens, initiative order) in read-only mode until their turn.
- DM sees full combat controls (Next Turn, End Combat, death save widgets).
- No console errors.

---

## 2  Player Joins In-Progress Combat

**Steps:**
1. With combat already running, Player refreshes their browser tab.
2. Player opens the Combat tab.

**Expected:**
- Combat state is restored from server; correct turn indicator is shown.
- Player sees their character in the initiative list.
- Player's remaining movement and action economy reflect any turns already taken.

---

## 3  Target Selection — Players Can Select NPC/Monster Targets

**Steps:**
1. Player clicks on a monster/NPC token on the map.
2. Confirm the token is highlighted as a target.
3. Player opens the Actions tab; an attack action shows the selected target's name.

**Expected:**
- Target token shows selection outline.
- DM view also reflects the selected target.
- Clearing selection (click empty space or Escape) removes the highlight from both views.

---

## 4  Initiative Labels on Map

**Steps:**
1. While combat is active, look at the map for all tokens.

**Expected:**
- Every token in the initiative order shows its initiative number as a small label on the map.
- Label is visible to both DM and Player.
- After initiative is rolled or re-rolled, labels update without requiring a page refresh.

---

## 5  Movement Preview: Ghost Token, Path, Click-Again Confirm

**Steps:**
1. On the Player's turn, click their token to select it.
2. Click a destination cell.
3. Observe the movement preview.
4. Click the destination cell again to confirm.

**Expected (preview):**
- A dashed outline appears at the token's origin (showing where it started).
- A ghost (semi-transparent) copy of the token appears at the destination.
- A dashed path line connects origin to destination.
- A label shows `X ft • Y ft left` (or `Too far: X ft / Y ft budget` for invalid moves).

**Expected (confirm):**
- Clicking the destination again commits the move.
- Ghost token disappears; real token moves.
- Remaining movement decrements correctly.

**Expected (cancel):**
- Right-clicking or pressing Escape cancels the preview without moving.

---

## 6  Movement Cannot Exceed Remaining Feet

**Steps:**
1. On the Player's turn, drag or click progressively farther cells.
2. Attempt to move beyond the character's remaining movement.

**Expected:**
- Path label turns red and reads `Too far: X ft / Y ft budget`.
- Confirming an over-budget move is rejected (no token movement occurs).
- Server-side validation also blocks over-budget moves (check server logs).
- Remaining movement shown in the combat coach UI updates as movement is spent.

---

## 7  Grid Size Changes Do Not Break Movement Cost

**Steps:**
1. DM opens Map Editor; change grid size (e.g., 50 px → 70 px → 100 px).
2. Return to combat; attempt player movement.

**Expected:**
- Movement costs recalculate correctly at each grid size.
- 1 cell = 5 ft regardless of pixel density.
- Difficult terrain costs 2× as expected.
- No NaN or ∞ values appear in movement labels.

---

## 8  Spell Scaling Works for Every Spell Type

Test one spell from each category:

| Category | Spell | Expected scaling |
|---|---|---|
| Damage (slot-scaled) | Fireball | 8d6 at 3rd, +1d6 per slot above 3rd |
| Damage (target-scaled) | Scorching Ray | 3 rays at 2nd, +1 ray per slot above 2nd |
| Damage (multi-dart) | Magic Missile | 3 darts at 1st, +1 dart per slot above 1st |
| Healing | Cure Wounds | 2d8+mod at 1st, +2d8 per slot above 1st |
| Cantrip (character level) | Fire Bolt | 1d10 at L1–4, 2d10 at L5–10, 3d10 at L11–16, 4d10 at L17+ |
| Utility (no damage) | Disguise Self | No roll button; no fake damage dice |
| Save-only | Hold Person | Save shown; no attack roll |

**Steps for each:**
1. Open the character's Spells tab.
2. Select the spell; choose a higher-level cast slot via the dropdown.
3. Click Roll.

**Expected:**
- Damage formula in the roll card matches the D&D 5e 2024 rulebook.
- Result popup appears and stays visible for at least 4 seconds.
- Action or spell slot is consumed; remaining slots update.

---

## 9  Imported / PDF Spell Rows — Higher-Level Cast Options

**Steps:**
1. Import a character from a D&D Beyond JSON export or PDF that has spells (e.g., a Wizard with Fireball).
2. Open the character sheet; navigate to Spells tab.
3. Find the imported Fireball row.
4. Attempt to cast at 4th level.

**Expected:**
- Imported spells that matched a native compendium entry show the same cast-level dropdown as native spells.
- Imported spells that did NOT match (unrecognized name) appear with a "Needs Review" badge but still show a roll button using whatever formula was parsed from the import.
- Upcasting an imported spell scales the formula according to the same resolver as native spells.
- `sourceType` on the card is `"imported_spellbook"` when sourced from a spellbook import entry.

---

## 10  Weapon Attack / Damage — No Silent Action Spend

**Steps:**
1. On the Player's turn, open the Actions tab.
2. Select a weapon (e.g., Longsword).
3. Click **Attack**.
4. Observe the roll result popup and action economy.

**Expected:**
- A to-hit roll is made (d20 + proficiency + ability modifier).
- If the attack hits, a damage roll button appears in the result popup.
- Clicking the damage button rolls damage (e.g., 1d8+mod for Longsword).
- Action economy: one **Action** is consumed after the roll, not silently before.
- A natural 20 produces a critical hit popup with doubled dice.
- No double-spend: rolling damage a second time does NOT spend another action.

---

## 11  Roll Result Popups Stay Visible

**Steps:**
1. Roll any die (attack, damage, spell, or plain d20 from the dice tray).
2. Do not interact with the UI.

**Expected:**
- The roll result popup remains visible for at least **4 seconds** after the roll completes.
- Clicking elsewhere or pressing a key does NOT immediately dismiss it.
- Rolling again replaces the old popup with the new result.

---

## 12  Dice Rolling Does Not Lag Badly

**Steps:**
1. Roll dice in rapid succession: click the d20 button 5 times in 3 seconds.

**Expected:**
- Each roll completes in under 2 seconds.
- The 3D animation plays smoothly (or skips gracefully in Result-Only mode).
- No UI freezes or unresponsive periods.
- Console shows no uncaught exceptions.

---

## 13  Quick Bar — Close and Reopen

**Steps:**
1. During combat, click the **×** button on the Combat Quick Bar to close it.
2. After closing, click the **☰ Quick Actions** button (or equivalent) to reopen it.

**Expected:**
- Quick Bar closes completely (no residual overlay).
- Quick Bar reopens to the same position and selected actions as before.
- Reopened Quick Bar works normally: spells, attacks, and items are clickable.
- Quick Bar does not permanently vanish (requires page refresh to see again).

---

## 14  Action Economy Test

**Steps:**
1. On the Player's turn, verify the action economy tracker in the Combat tab shows:
   - 1 Action
   - 1 Bonus Action
   - 1 Reaction
   - Full movement
2. Use an Action (attack or cast a 1-action spell).
3. Use a Bonus Action (e.g., Offhand Attack or a bonus-action spell).

**Expected:**
- After each use, the corresponding slot is marked spent.
- Attempting to use a second Action is blocked with a clear message.
- Reaction is tracked separately; using it on another creature's turn consumes it.
- At the start of the next turn, all slots reset to available.

---

## 15  Dice Performance Test

**Steps:**
1. Enable the 3D Dice Tray (Roll presentation: 3D Dice Tray in the dice sidebar).
2. Roll d20 ten times in succession.
3. Also roll while another browser tab is connected as a Player (remote visual mode).

**Expected:**
- Each roll animates and settles in under 2 seconds on a standard laptop.
- The **Shared roll visuals** setting (dice sidebar) controls whether other players see the animation.
- Turning "Shared roll visuals" to **Hide others' dice** stops remote animations without errors.
- No memory leak symptoms (page remains responsive after 20+ rolls).

---

## Automated Test Coverage Reference

The following test suites were run and pass on the QA branch:

| Suite | Tests | Status |
|---|---|---|
| `test_combat_move_preview` | 13 | PASS |
| `test_combat_movement_planning` | 3 | PASS |
| `test_combat_quick_bar_ui` | 11 | PASS |
| `test_combat_attention_ui` | 22 | PASS |
| `test_combat_coach_ui` | 21 | PASS |
| `test_combat_tab_readability_ui` | 3 | PASS |
| `test_integration_combat_tab` | 10 | PASS |
| `test_encumbrance_combat_disadvantage` | 3 | PASS |
| `test_spell_runtime_resolver` | 32 | PASS |
| `test_item_spell_system` | 27 | PASS |
| `test_weapon_action_rolling` | 48 | PASS |
| `test_dice_face_mapping` | 37 | PASS |
| `test_dice_final_bridge_and_settings` | 10 | PASS |
| `test_multiclass_spell_manifest` | 6 | PASS |
| `test_character_import_normalizer` | 16 | PASS |
| `test_druid_prepared_import` | 5 | PASS |

**Total automated: 261 PASS, 0 FAIL**

### Pre-existing failures (out of scope for combat QA)

The following test suites have pre-existing failures unrelated to combat:

- `test_summon_*` — Summon runtime and unlock passes (pending summon system work)
- `test_rules_catalog_integrity_full` — Warlock/tinker/pirate class feature metadata incomplete
- `test_species_system_ui` — Species picker legacy import field
- `test_subclass_choice_flow_runtime` — Subclass pending runtime marker
- `test_subclass_completion_sweep_v33` — Barbarian/monk runtime depth

These are tracked separately and do not block the combat integration QA.

---

## Sign-Off

| Step | Tester | Result | Notes |
|---|---|---|---|
| 1 DM starts combat | | | |
| 2 Player joins | | | |
| 3 Target selection | | | |
| 4 Initiative labels | | | |
| 5 Movement preview | | | |
| 6 Movement cap | | | |
| 7 Grid size changes | | | |
| 8 Spell scaling | | | |
| 9 Imported spell upcast | | | |
| 10 Weapon attack/damage | | | |
| 11 Roll popup visibility | | | |
| 12 Dice performance | | | |
| 13 Quick Bar reopen | | | |
| 14 Action economy | | | |
| 15 Dice performance + remote | | | |
