from pathlib import Path

from server.static_compat import resolve_legacy_class_portrait


def test_legacy_class_portrait_path_falls_back_for_barbarian():
    root = Path(__file__).resolve().parents[1]
    static_dir = root / "client" / "static"
    resolved = resolve_legacy_class_portrait(static_dir, "barbarian.png")
    assert resolved is not None
    assert resolved.exists()
    assert resolved.name == "Human Female Barbarian.png"


def test_legacy_plural_classes_portrait_path_is_supported():
    root = Path(__file__).resolve().parents[1]
    static_dir = root / "client" / "static"
    resolved = resolve_legacy_class_portrait(static_dir, "fighter.png")
    assert resolved is not None
    assert resolved.exists()
