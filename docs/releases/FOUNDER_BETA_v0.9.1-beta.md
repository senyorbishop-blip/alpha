# Founder Beta Release Notes — v0.9.1-beta

**Release date:** 2026-03-30  
**Channel:** Founder Beta

## Summary

This patch hardens founder-beta release operations without changing gameplay architecture: clearer operator workflows, more explicit support boundaries, and targeted regression guards for release/handoff documents.

## What this release improves

- Safer install/update handoff with explicit smoke checks.
- Clearer backup/update/rollback validation guidance for operators.
- More explicit known-limitations language to prevent unsupported assumptions.
- Better release-ops checklist alignment with current founder-beta reality.
- Focused test coverage for release-readiness documentation consistency.

## Runtime impact

- No gameplay protocol changes.
- No WebSocket message format changes.
- No save/load schema changes.

## Upgrade / rollback notes

- Before updating, run the backup steps in `docs/backup-update-rollback.md`.
- If rollback is required, restore both code and data snapshot from the same known-good point.

## Known founder-beta limits

See `docs/known-issues-founder-beta.md`.
