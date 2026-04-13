070j patch notes

- Fixed Character Book import follow-up error by restoring refreshPlayerColorSwatches()
- Added clickable d20 rolls for Character Book Saving Throws and Skills with modifier support
- Added labeled dice results and chat log entries for skill/save checks
- Reduced duplicate imported attack rows from D&D Beyond PDF parsing
- De-duplicated imported gear/inventory sync rows so identical items merge instead of stacking duplicate lines

071a - Spell rules database + scaling engine foundation
- Added modular rules database tables for official/open structured spell metadata, DM custom spells, and review queue.
- Added spell matching/enrichment API with cantrip scaling, slot scaling, rays/darts/targets scaling, and unmatched review flags.
- Added Character Book rules-linked spellbook UI plus DM-only custom spell review/editor modal.
