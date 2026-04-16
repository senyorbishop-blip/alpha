# Character Demo Readiness — Pass F Lock

Last updated: 2026-04-16

This checklist is the final demo lock for the live character experience.
It is intentionally scoped to shipping confidence and blocker containment.

## Scope status

| Area | Status | Notes |
|---|---|---|
| Character creation | ✅ Verified ready | Native builder flow remains the default and supported path for the demo. |
| Character selection / load | ✅ Verified ready | Library + session character selection remains stable for normal player join flow. |
| Sheet open / hydration | ✅ Verified ready | Premium sheet tabs open and populate from runtime character data. |
| Vitals / combat math trust | ✅ Verified ready | Existing Pass C coverage remains the source for HP/AC/attack math confidence. |
| Features / traits / feats | ✅ Verified ready | Feature surface copy tightened to player-facing guidance only. |
| Actions | ✅ Verified ready | Unsupported summon/deploy action rows are now suppressed from the live actions surface. |
| Spells | ✅ Verified ready | Spell cards and drill-in remain available with slot/roll affordances. |
| Level-up continuity | 🟡 Ready with caveat | Gateway-level preview entry is intentionally suppressed to avoid exposing partial path behavior in live demo entry flow. |
| Summon / deploy (live-supported families) | ✅ Verified ready | Beast Master, Pact of the Chain, and Mechanist companion runtime paths remain surfaced. |
| Unsupported-path containment | ✅ Verified ready | Non-runtime summon/deploy rows and gateway preview affordance are hidden in the live flow. |
| Prototype/dev wording leakage | ✅ Verified ready | Feature tab copy now avoids test/audit phrasing in player-facing headers. |

## Demo-safe classes re-verified in Pass F

- Barbarian
- Bard
- Cleric
- Druid
- Fighter
- Monk
- Paladin
- Ranger (including Beast Master summon loop)
- Rogue
- Sorcerer
- Warlock (including Pact of the Chain familiar loop)
- Wizard
- Tinker (including Mechanist deploy loop)
- Pirate

## Remaining issue classification

### Blockers

- None currently identified in the locked character demo path.

### Non-blockers

- Level-up from the gateway card surface is intentionally hidden for this demo cut; use in-sheet/runtime level-up paths.

### Deferred

- Broader expansion of summon/deploy support beyond the currently runtime-supported families.
- Additional level-up UX expansion beyond the locked demo-safe flow.
