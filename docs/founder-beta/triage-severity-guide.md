# Founder Beta Triage Severity Guide

Use this to classify incoming bugs consistently.

## Critical

Use when core play is blocked or data integrity is at risk.

Examples:
- App cannot start or cannot stay running.
- DM/player cannot join session.
- Save/load corruption or unrecoverable loss.
- Combat flow completely unusable.

## High

Use when major gameplay systems are broken but partial play may still continue.

Examples:
- Fog/vision controls fail in live play.
- Token ownership/permissions are wrong.
- Password reset/admin recovery path broken.
- Frequent reconnect failures.

## Medium

Use when feature works imperfectly, causes confusion, or affects quality without fully blocking play.

Examples:
- Layout clutter in a key panel.
- Confusing interaction sequence.
- One tab/panel scroll or state issue with workaround.
- Phone UX friction in non-core path.

## Low

Use when issue is minor, cosmetic, or polish-only.

Examples:
- Wording/label typo.
- Icon spacing/alignment issue.
- Non-critical style inconsistency.

## Nice-to-have

Use for improvement requests or enhancements, not defects.

Examples:
- New quality-of-life shortcuts.
- Optional visual polish ideas.
- Workflow improvements that are not regressions.
