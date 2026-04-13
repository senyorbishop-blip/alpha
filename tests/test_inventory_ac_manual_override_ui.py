def test_token_editor_manual_ac_edit_marks_player_ac_as_manual():
    src = open("client/templates/play.html", "r", encoding="utf-8").read()
    assert "if (ROLE === 'player' && _tokenOwnedByMe(t) && !Number.isNaN(newAc)) {" in src
    assert "_charAcIsEquipmentDerived = false;" in src
    assert "_charSheet.ac = newAc;" in src
