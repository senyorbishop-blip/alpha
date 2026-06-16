# AC/HP Runtime Manual QA

Use this checklist after changing character AC/HP, PDF import, token sync, or DM inspection.

1. Upload/import a player PDF.
2. Confirm imported AC is preserved in `importedAc` and the AC audit panel.
3. Confirm imported HP is preserved in `importedMaxHp`, `importedCurrentHp`, and `importedTempHp`.
4. Confirm Alpha calculated AC/HP is shown beside imported values.
5. Confirm mismatch creates an “AC needs review” or “HP needs review” badge, not a silent override.
6. Confirm player/DM can approve imported PDF AC by persisting `acSelectedMode: imported_pdf`.
7. Confirm player/DM can approve calculated AC by persisting `acSelectedMode: calculated`.
8. Confirm manual override works with `acManualOverride` / `hpManualOverride` and is labelled manual.
9. Confirm HP current/max/temp sync to token.
10. Confirm DM inspection matches player sheet values from `characterSheetRuntime`.
11. Equip armor and shield and confirm AC updates.
12. Attune/equip Ring/Cloak of Protection and confirm AC/save bonus review behavior.
13. Change Constitution and confirm HP recalculation warning before imported/manual HP is overwritten.
14. Build a native level 5 Fighter and confirm HP/AC.
15. Build Barbarian and Monk and confirm Unarmored Defense.
16. Long Rest and confirm HP/resource behaviour.
17. Reopen the character and confirm selected AC/HP mode persists.

## Expected behaviour

- PDF values are preserved separately from Alpha calculations.
- Mismatches are review states, never “use higher value” decisions.
- Token HP, player sheet HP, combat quick bar, and DM inspection all read from `characterSheetRuntime`.

## Current manual QA result

Not run in this non-browser automation pass. Run the checklist above in multiple browser sessions (DM, player, viewer where relevant) before production release.
