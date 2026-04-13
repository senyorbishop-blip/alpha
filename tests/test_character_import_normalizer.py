from server.character.import_normalizer import normalize_ddb_json_payload, normalize_pdf_payload


def test_normalize_ddb_json_payload_produces_canonical_document():
    payload = {
        "data": {
            "id": 987654,
            "name": "Aela",
            "stats": [
                {"id": 1, "value": 10},
                {"id": 2, "value": 14},
                {"id": 3, "value": 12},
                {"id": 4, "value": 8},
                {"id": 5, "value": 13},
                {"id": 6, "value": 16},
            ],
            "classes": [
                {
                    "level": 3,
                    "definition": {"name": "Rogue"},
                    "subclassDefinition": {"name": "Arcane Trickster"},
                }
            ],
            "race": {
                "fullName": "Wood Elf",
                "weightSpeeds": {"normal": {"walk": 35}},
            },
            "background": {"definition": {"name": "Urchin"}},
        }
    }

    result = normalize_ddb_json_payload(payload, external_id="987654")
    doc = result["document"]

    assert doc["schema"] == "casual-dnd.character"
    assert doc["sourceMode"] == "dndbeyond"
    assert doc["identity"]["characterId"] == "987654"
    assert doc["identity"]["name"] == "Aela"
    assert doc["classes"][0]["name"] == "Rogue"
    assert doc["abilities"]["scores"]["dex"] == 14
    assert doc["species"]["name"] == "Wood Elf"
    assert isinstance(result["warnings"], list)


def test_normalize_pdf_payload_reports_missing_content_warnings():
    parsed = {
        "name": "Unknown Hero",
        "stats": [10, 10, 10, 10, 10, 10],
        "classes": [],
        "race": "",
        "background": "",
        "currency": "12 gp, 3 sp",
    }

    result = normalize_pdf_payload(parsed, filename="imported.pdf")

    assert result["document"]["sourceMode"] == "dndbeyond"
    assert result["document"]["equipment"]["currency"]["gp"] == 12
    assert result["document"]["equipment"]["currency"]["sp"] == 3
    assert any("Species" in warning for warning in result["warnings"])
    assert any("Background" in warning for warning in result["warnings"])
