from server.character.rules_catalog import load_rules_catalog


def test_pirate_exists_with_full_progression_and_subclasses():
    catalog = load_rules_catalog()
    classes = {row["id"]: row for row in catalog["classes"]}
    assert "pirate" in classes
    pirate = classes["pirate"]
    assert pirate["subclassLevel"] == 3
    assert pirate["spellcastingType"] == "none"
    assert len(pirate.get("progressionTable") or []) == 20

    subclass_ids = {row["id"] for row in catalog["subclasses"] if row.get("classId") == "pirate"}
    assert {"corsair", "privateer", "smuggler", "dread-captain"} <= subclass_ids


def test_pirate_progression_exposes_core_resource_and_capstone():
    catalog = load_rules_catalog()
    pirate = {row["id"]: row for row in catalog["classes"]}["pirate"]
    level1 = next(row for row in pirate["progressionTable"] if row["level"] == 1)
    level20 = next(row for row in pirate["progressionTable"] if row["level"] == 20)

    assert "Swagger Dice" in level1["features"]
    assert level1["classMechanics"]["swaggerDice"] == "d6"
    assert level20["classMechanics"]["swaggerDice"] == "d12"
    assert "King of the Black Flag" in level20["features"]


def test_pirate_feature_definitions_have_authored_depth():
    catalog = load_rules_catalog()
    pirate = {row["id"]: row for row in catalog["classes"]}["pirate"]
    defs = pirate.get("featureDefinitions") or {}
    assert defs["pirate-swagger-dice"]["trackUses"] is True
    assert defs["pirate-swagger-dice"]["resourceName"] == "Swagger Dice"
    assert defs["pirate-dread-volley"]["type"] == "action"
