from pathlib import Path


LEGACY_CLASS_PORTRAIT_FALLBACKS = {
    "barbarian": "Human Female Barbarian.png",
    "bard": "Human Female Bard.png",
    "cleric": "Human Female Cleric.png",
    "druid": "Human Female Druid.png",
    "fighter": "Human Male Fighter.png",
    "monk": "Human Female Monk.png",
    "paladin": "Human Female Paladin.png",
    "ranger": "Human Female Ranger.png",
    "rogue": "Human Female Rogue.png",
    "sorcerer": "Human Female Sorcerer.png",
    "warlock": "Human Male Warlock.png",
    "wizard": "Human Female Wizard.png",
}


def resolve_legacy_class_portrait(static_dir: Path, filename: str) -> Path | None:
    normalized = Path(filename).name
    class_path = static_dir / "importer" / "portraits" / "class" / normalized
    if class_path.exists() and class_path.is_file():
        return class_path

    class_id = Path(normalized).stem.strip().lower()
    combo_filename = LEGACY_CLASS_PORTRAIT_FALLBACKS.get(class_id)
    if not combo_filename:
        return None
    combo_path = static_dir / "importer" / "portraits" / "combos" / combo_filename
    if combo_path.exists() and combo_path.is_file():
        return combo_path
    return None
