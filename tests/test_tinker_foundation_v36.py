import json
from pathlib import Path


RULES_ROOT = Path("server/data/rules/5e2024")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_tinker_exists_with_full_progression_and_subclasses():
    tinker = _load_json(RULES_ROOT / "classes" / "tinker.json")
    assert tinker["subclassLevel"] == 3
    assert tinker["spellcastingType"] == "half"
    assert len(tinker.get("progressionTable") or []) == 20

    subclass_ids = set()
    for path in (RULES_ROOT / "subclasses").glob("*.json"):
        row = _load_json(path)
        if row.get("classId") == "tinker":
            subclass_ids.add(row["id"])
    assert {"artillerist", "alchemist", "mechanist", "saboteur"} <= subclass_ids


def test_tinker_spell_list_and_subclass_grants_are_available():
    class_spell_lists = _load_json(RULES_ROOT / "class_spell_lists.json")
    tinker_spells = class_spell_lists.get("tinker") or {}
    spell_ids = set()
    for level_bucket in tinker_spells.values():
        if isinstance(level_bucket, list):
            spell_ids.update(level_bucket)
    assert "mending" in spell_ids
    assert "shield" in spell_ids
    assert "revivify" in spell_ids

    artillerist = _load_json(RULES_ROOT / "subclasses" / "artillerist.json")
    grants = artillerist.get("featureDefinitions", {}).get("artillerist-bombardment-spells", {})
    assert "spellcasting" in (grants.get("tags") or [])


def test_tinker_progression_and_subclass_defs_surface_gadget_charge_identity():
    tinker = _load_json(RULES_ROOT / "classes" / "tinker.json")
    level_10 = next(row for row in (tinker.get("progressionTable") or []) if row.get("level") == 10)
    assert level_10["classMechanics"]["gadgetCharges"] == 5

    mechanist = _load_json(RULES_ROOT / "subclasses" / "mechanist.json")
    defs = mechanist.get("featureDefinitions") or {}
    assert defs["mechanist-companion-frame"]["resourceName"] == "Gadget Charges"
    assert defs["mechanist-companion-frame"]["type"] == "bonus action"
    assert defs["mechanist-linked-actions"]["resourceName"] == "Gadget Charges"
    assert defs["mechanist-linked-actions"]["type"] == "bonus action"
