#!/usr/bin/env python3
"""Static audit for the shared character sheet runtime boundary."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "client/static/js/character/runtime/character_sheet_runtime.js"
ACTIONS = ROOT / "client/static/js/character/tabs/actions_tab.js"
SPELLS = ROOT / "client/static/js/character/tabs/spells_tab.js"
CONTAINER = ROOT / "client/static/js/character/character_sheet_container.js"
QUICK = ROOT / "client/static/js/character/combat_quick_selectors.js"

REQUIRED_KEYS = [
    "identity", "abilities", "saves", "skills", "passiveScores", "senses", "defenses", "conditions",
    "hp", "ac", "speed", "initiative", "proficiencyBonus", "resources", "actions", "bonusActions",
    "reactions", "limitedUseActions", "attacks", "spells", "itemSpells", "features", "traits", "feats",
    "backgroundFeatures", "itemTraits", "inventory", "warnings", "needsReview",
]


def audit() -> dict:
    runtime = RUNTIME.read_text(encoding="utf-8")
    actions = ACTIONS.read_text(encoding="utf-8")
    spells = SPELLS.read_text(encoding="utf-8")
    container = CONTAINER.read_text(encoding="utf-8")
    quick = QUICK.read_text(encoding="utf-8")
    problems: list[str] = []
    for key in REQUIRED_KEYS:
        if not re.search(rf"\b{re.escape(key)}\b", runtime):
            problems.append(f"runtime missing major section {key}")
    for snippet in [
        "charData.characterSheetRuntime = sheetRuntime;",
        "charData.nativeActionCards",
        "charData.rulesSpellbook = sheetRuntime.spells;",
    ]:
        if snippet not in container:
            problems.append(f"sheet container does not consume runtime via {snippet}")
    if "classKey !== 'tinker' && classKey !== 'pirate'" not in actions:
        problems.append("hardcoded custom action cards are not gated behind the runtime boundary")
    if "resolveSpellRuntime" not in runtime or "AppSpellRuntime.resolveSpellRuntime" not in spells:
        problems.append("spells are not visibly connected to the shared spell resolver")
    if "sheetRuntime.spells" not in quick:
        problems.append("combat quick bar selectors do not prefer characterSheetRuntime.spells")
    return {"problems": problems, "required_keys": REQUIRED_KEYS}


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(1 if result["problems"] else 0)
