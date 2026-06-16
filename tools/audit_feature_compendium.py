#!/usr/bin/env python3
"""Audit the 5e2024 feature compendium for runtime-shape problems."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "server" / "data" / "rules" / "5e2024" / "features"


def _slug(value: object) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())


def _load_rows() -> list[dict]:
    index = json.loads((FEATURE_DIR / "index.json").read_text(encoding="utf-8"))
    files = index.get("files", index if isinstance(index, list) else [])
    rows: list[dict] = []
    for name in files:
        path = FEATURE_DIR / str(name)
        if not path.exists():
            rows.append({"__audit_error__": f"missing file {name}"})
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("features", payload if isinstance(payload, list) else []):
            if isinstance(row, dict):
                rows.append({**row, "__file__": name})
    return rows


def audit() -> dict:
    rows = _load_rows()
    names = Counter(_slug(r.get("name")) for r in rows if r.get("name"))
    ids = Counter(str(r.get("id") or "").lower() for r in rows if r.get("id"))
    problems: list[str] = []
    for row in rows:
        if row.get("__audit_error__"):
            problems.append(row["__audit_error__"])
            continue
        label = f"{row.get('__file__')}:{row.get('id') or row.get('name')}"
        for key in ("id", "name", "kind", "safe_summary"):
            if not row.get(key):
                problems.append(f"{label} missing {key}")
        resource_name = row.get("resource_name")
        grants_actions = row.get("grants_actions") if isinstance(row.get("grants_actions"), list) else []
        if resource_name and str(row.get("recovery") or "").lower() in {"", "none"}:
            problems.append(f"{label} has resource {resource_name!r} without rest recovery")
        for action in grants_actions:
            if isinstance(action, dict) and (action.get("resource_name") or action.get("resource_cost")) and not resource_name:
                problems.append(f"{label} grants resource-cost action without feature resource")
        for spell in row.get("grants_spells") or []:
            if not (isinstance(spell, dict) and (spell.get("name") or spell.get("id"))):
                problems.append(f"{label} grants spell with no id/name")
    duplicate_names = sorted(k for k, v in names.items() if k and v > 1)
    duplicate_ids = sorted(k for k, v in ids.items() if k and v > 1)
    return {"feature_count": len(rows), "duplicate_feature_names": duplicate_names, "duplicate_feature_ids": duplicate_ids, "problems": problems}


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(1 if result["problems"] else 0)
