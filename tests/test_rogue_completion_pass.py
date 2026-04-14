import json

from server.character.spell_compendium import build_character_spell_manifest, build_spell_limits_for_class


def _load_rogue_class() -> dict:
    with open('server/data/rules/5e2024/classes/rogue.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def test_rogue_progression_unlock_ids_are_authored_not_placeholder():
    rogue = _load_rogue_class()
    feature_defs = rogue.get('featureDefinitions', {})
    assert isinstance(feature_defs, dict)

    for row in rogue.get('progressionTable', []):
        unlock_ids = row.get('unlockIds', []) if isinstance(row, dict) else []
        for feature_id in unlock_ids:
            fid = str(feature_id or '').strip()
            assert fid
            assert not fid.startswith('rogue-l')
            assert fid in feature_defs


def test_arcane_trickster_spell_limits_use_intelligence_and_slots():
    doc = {
        'classes': [{'classId': 'rogue', 'level': 3, 'subclassId': 'arcane-trickster'}],
        'abilities': {'scores': {'dex': 16, 'int': 15, 'con': 12}},
    }
    limits = build_spell_limits_for_class('rogue', 3, doc['abilities'], document=doc, subclass_id='arcane-trickster')
    assert limits.get('castingType') == 'third'
    assert limits.get('spellcastingAbility') == 'int'
    assert (limits.get('spellSlots') or {}).get('1st') == 2
    assert limits.get('cantripsKnown') == 3
    assert limits.get('spellsKnown') == 3


def test_arcane_trickster_spell_manifest_surfaces_cards_for_subclass_access():
    doc = {
        'classes': [{'classId': 'rogue', 'level': 3, 'subclassId': 'arcane-trickster'}],
        'abilities': {'scores': {'dex': 16, 'int': 16, 'con': 12}},
        'spellState': {'known': ['spell_minor_illusion', 'spell_disguise_self']},
    }
    manifest = build_character_spell_manifest(doc)
    limits = manifest.get('limits') or {}
    assert limits.get('spellcastingAbility') == 'int'
    assert limits.get('castingType') == 'third'
    names = {str(card.get('id') or '') for card in (manifest.get('cards') or [])}
    assert 'spell_minor_illusion' in names
