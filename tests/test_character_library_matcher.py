from server.character.library_matcher import (
    attach_library_gap_report,
    build_library_gap_report,
    match_name,
    normalize_match_key,
    summarize_library_gaps_from_profiles,
)


def test_library_matcher_normalizes_case_punctuation_and_aliases():
    assert normalize_match_key("Studded Leather Armour") == normalize_match_key("studded-leather armor")

    dagger = match_name("Daggers", "items")
    assert dagger["status"] == "alias"
    assert dagger["matched_name"] == "Dagger"

    shield = match_name("+1 Shield", "items")
    assert shield["status"] in {"exact", "alias", "partial"}

    fireball = match_name("fireball", "spells")
    assert fireball["status"] == "exact"
    assert fireball["matched_name"] == "Fireball"

    partial = match_name("Fireball (bonus)", "spells")
    assert partial["status"] == "partial"
    assert partial["matched_name"] == "Fireball"


def test_library_gap_report_preserves_missing_imported_names_and_notes():
    document = {
        "equipment": {
            "inventory": [
                {"name": "Daggers", "notes": "Imported as a plural weapon."},
                {"name": "Xyzzyq Uncatalogued Item", "notes": "Homebrew item from the PDF."},
            ]
        },
        "spellState": {
            "spellbookEntries": [
                {"name": "Fireball", "notes": "Known spell."},
                {"name": "Xyzzyq Impossible Spell", "notes": "Homebrew spell text."},
            ]
        },
        "species": {"name": "Wood Elf", "traits": [{"name": "Fey Ancestry"}]},
        "background": {"name": "Acolyte"},
        "classes": [{"name": "Fighter", "features": [{"name": "Second Wind"}, {"name": "Pocket Timeline"}]}],
    }

    report = build_library_gap_report(document)

    assert set(report) == {"items", "spells", "features"}
    for group in report.values():
        assert set(group) == {"exact", "alias", "partial", "missing"}

    assert any(row["imported_name"] == "Daggers" for row in report["items"]["alias"])
    missing_item = next(row for row in report["items"]["missing"] if row["imported_name"] == "Xyzzyq Uncatalogued Item")
    assert missing_item["notes"] == "Homebrew item from the PDF."
    assert any(row["imported_name"] == "Fireball" for row in report["spells"]["exact"])
    missing_spell = next(row for row in report["spells"]["missing"] if row["imported_name"] == "Xyzzyq Impossible Spell")
    assert missing_spell["notes"] == "Homebrew spell text."
    assert any(row["imported_name"] == "Pocket Timeline" for row in report["features"]["missing"])


def test_attach_and_aggregate_library_gap_report_from_profiles():
    document = {
        "identity": {"name": "Gap Hero"},
        "sourceMode": "dndbeyond_json",
        "equipment": {"inventory": [{"name": "Uncatalogued Lantern"}]},
        "spellState": {"spellbookEntries": [{"name": "Uncatalogued Spark"}]},
        "classes": [{"name": "Wizard", "features": [{"name": "Uncatalogued Thesis"}]}],
        "importMeta": {"origin": "dndbeyond_json"},
    }

    report = attach_library_gap_report(document)
    assert document["importMeta"]["libraryGapReport"] == report

    summary = summarize_library_gaps_from_profiles(
        {
            "player-one": [
                {
                    "id": "gap-hero",
                    "name": "Gap Hero",
                    "sourceMode": "dndbeyond_json",
                    "nativeCharacter": document,
                }
            ]
        }
    )

    assert summary["ok"] is True
    assert summary["top_missing"]["items"][0]["name"] == "Uncatalogued Lantern"
    assert summary["top_missing"]["spells"][0]["sources"][0]["character"] == "Gap Hero"
    assert summary["top_missing"]["features"][0]["sources"][0]["source"] == "dndbeyond_json"
