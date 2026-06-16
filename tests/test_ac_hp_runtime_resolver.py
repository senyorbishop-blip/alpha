from server.character.resolver import resolveArmorClassRuntime, resolveHitPointsRuntime, resolve_character_runtime


def doc(**kw):
    base={"sourceMode":"native","abilities":{"scores":{"dex":14,"con":14,"wis":16}},"classes":[{"name":"Fighter","classId":"fighter","level":1}],"equipment":{"inventory":[]}}
    base.update(kw)
    return base


def test_unarmored_ac_10_plus_dex():
    assert resolveArmorClassRuntime(doc())["calculatedAc"] == 12


def test_barbarian_unarmored_defense():
    d=doc(classes=[{"name":"Barbarian","classId":"barbarian","level":1}])
    assert resolveArmorClassRuntime(d)["calculatedAc"] == 14


def test_monk_unarmored_defense():
    d=doc(classes=[{"name":"Monk","classId":"monk","level":1}])
    assert resolveArmorClassRuntime(d)["calculatedAc"] == 15


def test_medium_armor_dex_cap_and_shield():
    d=doc(equipment={"inventory":[{"name":"Scale Mail","equipment_kind":"armor","equipped":True,"base_ac":14,"armor_type":"medium","dex_cap":2},{"name":"Shield","equipment_kind":"shield","equipped":True,"ac_bonus":2}]})
    assert resolveArmorClassRuntime(d)["calculatedAc"] == 18


def test_heavy_armor_ignores_dex_and_magic_bonus():
    d=doc(equipment={"inventory":[{"name":"Plate +1","equipment_kind":"armor","equipped":True,"base_ac":18,"armor_type":"heavy","ac_bonus":1}]})
    assert resolveArmorClassRuntime(d)["calculatedAc"] == 19


def test_imported_ac_mismatch_needs_review_not_higher_value():
    d=doc(sourceMode="pdf", importedAc=17, ac=17)
    res=resolveArmorClassRuntime(d)
    assert res["needsReview"] is True
    assert res["calculatedAc"] == 12
    assert res["finalAc"] == 17
    assert res["selectedMode"] == "imported_pdf"
    assert "higher value" not in " ".join(res["breakdown"]).lower()


def test_calculated_ac_higher_than_imported_needs_review_not_blindly_calculated():
    d=doc(sourceMode="pdf", importedAc=10, ac=10, equipment={"inventory":[{"name":"Plate","equipment_kind":"armor","equipped":True,"base_ac":18,"armor_type":"heavy"}]})
    res=resolveArmorClassRuntime(d)
    assert res["needsReview"] is True
    assert res["finalAc"] == 10
    assert res["calculatedAc"] == 18


def test_manual_ac_override_labelled():
    res=resolveArmorClassRuntime(doc(acManualOverride=21))
    assert res["finalAc"] == 21
    assert res["selectedMode"] == "manual"
    assert res["reconciliation"]["status"] == "manual_override"


def test_level_1_hp_full_hit_die_plus_con_and_average():
    res=resolveHitPointsRuntime(doc(classes=[{"name":"Fighter","classId":"fighter","level":5}]))
    assert res["calculatedAverageHp"] == 44
    assert res["finalMaxHp"] == 44


def test_multiclass_hp_and_temp_separate_current_capped():
    d=doc(classes=[{"name":"Fighter","classId":"fighter","level":1},{"name":"Wizard","classId":"wizard","level":1}], currentHP=99, tempHP=7)
    res=resolveHitPointsRuntime(d)
    assert res["calculatedAverageHp"] == 18
    assert res["currentHp"] == 18
    assert res["tempHp"] == 7


def test_imported_hp_mismatch_needs_review():
    res=resolveHitPointsRuntime(doc(sourceMode="pdf", importedMaxHp=50, maxHP=50))
    assert res["needsReview"] is True
    assert res["finalMaxHp"] == 50
    assert res["calculatedAverageHp"] != 50


def test_manual_and_rolled_hp_modes():
    assert resolveHitPointsRuntime(doc(hpManualOverride=33))["hpMode"] == "manual"
    rolled=resolveHitPointsRuntime(doc(hpSelectedMode="rolled", hpPerLevelRolls=[10, 6], classes=[{"name":"Fighter","classId":"fighter","level":2}]))
    assert rolled["hpMode"] == "rolled"
    assert rolled["calculatedRolledHp"] == 20


def test_character_sheet_runtime_unified_ac_hp_objects():
    rt=resolve_character_runtime(doc(sourceMode="pdf", importedAc=15, ac=15, importedMaxHp=20, maxHP=20))["runtime"]["characterSheetRuntime"]
    assert rt["ac"]["value"] == 15
    assert rt["ac"]["needsReview"] is True
    assert rt["hp"]["max"] == 20
    assert rt["hp"]["needsReview"] is True
