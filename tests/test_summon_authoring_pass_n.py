import importlib.util
from pathlib import Path


_CATALOG_PATH = Path(__file__).resolve().parents[1] / "server" / "character" / "summon_catalog.py"
_SPEC = importlib.util.spec_from_file_location("summon_catalog_pass_n", _CATALOG_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

SUMMON_TEMPLATE_REGISTRY = _MODULE.SUMMON_TEMPLATE_REGISTRY
get_summon_template = _MODULE.get_summon_template
list_summon_templates_for_group = _MODULE.list_summon_templates_for_group
list_summon_templates_for_source = _MODULE.list_summon_templates_for_source
validate_summon_template_registry = _MODULE.validate_summon_template_registry


def test_live_registry_passes_validation():
    assert validate_summon_template_registry() == []


def test_validation_flags_missing_source_linkage_and_spell_constraints():
    broken = {
        'spell-bad': {
            'id': 'spell-bad',
            'displayName': 'Broken Spell Summon',
            'summonCategory': 'spell_effect',
            'sourceClassId': 'wizard',
            'sourceFeatureId': 'conjure-fey',
            'variantGroup': 'spell-bad-group',
            'actorType': 'spell_effect',
            'tokenName': 'Bad',
            'commandModel': 'spell_effect',
            'maxActive': 1,
            'replaceOnResummon': True,
            'summonOrigin': 'spell',
            'temporary': True,
            'durationSeconds': 0,
            'cleanupPolicy': [],
            'baseStats': {'scaling': 'placeholder'},
        }
    }
    errors = validate_summon_template_registry(broken)
    combined = ' | '.join(errors)
    assert "sourceClassId='spell'" in combined
    assert 'spellId' in combined
    assert "sourceFeatureId like 'spell:<id>'" in combined
    assert 'positive durationSeconds' in combined


def test_validation_flags_entity_kind_and_creature_semantic_mismatch():
    broken = {
        'device-bad': {
            'id': 'device-bad',
            'displayName': 'Broken Device',
            'summonCategory': 'deployable',
            'sourceClassId': 'tinker',
            'sourceFeatureId': 'artillerist-arc-cannon',
            'variantGroup': 'tinker-artillerist-cannon',
            'actorType': 'deployable',
            'tokenName': 'Broken Device',
            'commandModel': 'action_command',
            'maxActive': 1,
            'replaceOnResummon': True,
            'entityKind': 'creature',
            'isCreature': False,
            'baseStats': {'scaling': 'placeholder'},
        }
    }
    errors = validate_summon_template_registry(broken)
    assert any("isCreature=false conflicts" in err for err in errors)


def test_extension_point_group_and_source_queries_expose_live_families():
    ranger_group = list_summon_templates_for_group('ranger-primal-beast')
    assert {row['id'] for row in ranger_group} == {
        'ranger-primal-beast-land',
        'ranger-primal-beast-sea',
        'ranger-primal-beast-sky',
    }

    pact_rows = list_summon_templates_for_source(class_id='warlock', feature_id='warlock-pact-boon')
    pact_ids = {row['id'] for row in pact_rows}
    assert 'warlock-chain-imp' in pact_ids
    assert 'warlock-chain-sprite' in pact_ids


def test_spell_templates_keep_backwards_compatible_runtime_fields():
    before = SUMMON_TEMPLATE_REGISTRY['spell-conjure-fey-manifestation']
    assert before.get('sourceClassId') == 'spell'
    assert before.get('spellId') == 'conjure-fey'

    template = get_summon_template('spell-conjure-fey-manifestation')
    assert template is not None
    assert template.get('temporary') is True
    assert template.get('durationSeconds') == 3600
    assert template.get('controlModel') == 'caster_owned_independent_effect'
