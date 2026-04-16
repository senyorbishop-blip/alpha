#!/usr/bin/env python3
"""Dry-run inspector for summon/deploy compatibility normalization.

Usage:
    python tools/summon_deploy_compat_report.py --input payload.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from server.character.summon_state import normalize_summon_state


def _extract_summon_state(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    if isinstance(payload.get("summons"), dict):
        return payload.get("summons")
    if isinstance(payload.get("nativeCharacter"), dict):
        native = payload.get("nativeCharacter") or {}
        if isinstance(native.get("summons"), dict):
            return native.get("summons")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run summon/deploy migration compatibility report.")
    parser.add_argument("--input", required=True, help="Path to JSON payload containing summon state.")
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    normalized = normalize_summon_state(_extract_summon_state(raw))
    migration = normalized.get("migration") if isinstance(normalized.get("migration"), dict) else {}

    report = {
        "deploySchemaVersion": normalized.get("deploySchemaVersion"),
        "activeSummons": len(normalized.get("activeSummons") or []),
        "quarantinedSummons": len(normalized.get("quarantinedSummons") or []),
        "legacyUpgradesApplied": list(migration.get("legacyUpgradesApplied") or []),
    }
    print(json.dumps(report, indent=2))
    if normalized.get("quarantinedSummons"):
        print("\n# Quarantined entries")
        for row in (normalized.get("quarantinedSummons") or []):
            if not isinstance(row, dict):
                continue
            print(f"- reason={row.get('reason') or 'unknown'} activeId={row.get('activeId') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

