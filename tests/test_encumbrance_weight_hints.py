from server import encumbrance


def test_get_item_weight_uses_weight_hint_text_from_notes():
    item = {"name": "Ring of Protection", "notes": "1 lb."}
    assert encumbrance.get_item_weight(item) == 1.0


def test_get_item_weight_prefers_explicit_weight_over_hint():
    item = {"name": "Ring of Protection", "weight_lbs": 0.25, "notes": "1 lb."}
    assert encumbrance.get_item_weight(item) == 0.25
