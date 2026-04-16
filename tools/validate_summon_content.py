#!/usr/bin/env python3
"""Validate summon/deploy content registry entries with actionable errors."""
from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "server" / "character" / "summon_catalog.py"
SPEC = importlib.util.spec_from_file_location("summon_catalog_validator_cli", CATALOG_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load summon catalog from {CATALOG_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
validate_summon_template_registry = MODULE.validate_summon_template_registry


def main() -> int:
    errors = validate_summon_template_registry()
    if errors:
        print("Summon/deploy content validation failed:")
        for idx, err in enumerate(errors, start=1):
            print(f"{idx}. {err}")
        return 1
    print("Summon/deploy content validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
