from server.character.progression import build_levelup_preview, apply_levelup
from server.character.resolver import resolve_character_runtime


def test_levelup_preview_requires_subclass_with_options_when_crossing_unlock_level():
    preview = build_levelup_preview(
        {
            "classes": [{"classId": "barbarian", "level": 2}],
            "abilities": {"scores": {"str": 16, "dex": 12, "con": 14, "int": 8, "wis": 10, "cha": 10}},
        }
    )
    required = [row for row in (preview.get("requiredChoices") or []) if row.get("type") == "subclass"]
    assert required, "Expected subclass choice requirement at Barbarian level 3."
    options = required[0].get("options") or []
    assert any(str(row.get("id") or "") == "berserker" for row in options)
    assert preview.get("subclassChoice", {}).get("required") is True


def test_apply_levelup_accepts_explicit_subclass_choice_without_defaulting():
    applied = apply_levelup(
        {
            "classes": [{"classId": "barbarian", "level": 2}],
            "abilities": {"scores": {"str": 16, "dex": 12, "con": 14, "int": 8, "wis": 10, "cha": 10}},
        },
        choices={"subclassChoice": "berserker"},
    )
    primary = (applied.get("document", {}).get("classes") or [{}])[0]
    assert primary.get("subclassId") == "berserker"
    assert str(primary.get("subclass") or "").lower().startswith("berserker")


def test_runtime_marks_subclass_pending_when_unlock_level_reached_without_choice():
    resolved = resolve_character_runtime(
        {
            "classes": [{"classId": "paladin", "level": 2}],
            "abilities": {"scores": {"str": 16, "dex": 10, "con": 14, "int": 8, "wis": 10, "cha": 14}},
        }
    )
    class_display = resolved.get("runtime", {}).get("classDisplay") or {}
    assert class_display.get("subclassUnlockLevel") == 2
    assert class_display.get("subclassPending") is True
    assert class_display.get("subclassId") == ""
