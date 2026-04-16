from server.character.summon_runtime import build_active_deployment_entry, normalize_deployment_ui_entry
from server.character.summon_state import normalize_summon_state
from server.session import User, Token


def test_build_active_deployment_entry_exposes_shared_model_fields_for_spell_effects():
    owner = User(id='u-caster', name='Selene', role='player')
    actor = {
        'id': 'summon-u-caster-1',
        'name': 'Conjured Fey',
        'templateId': 'spell-conjure-fey-manifestation',
        'actorType': 'spell_effect',
        'summonCategory': 'spell_effect',
        'commandModel': 'spell_effect',
        'source': {
            'classId': 'spell',
            'featureId': 'spell:conjure-fey',
            'variantGroup': 'spell-conjure-fey',
            'summonOrigin': 'spell',
            'spellId': 'conjure-fey',
        },
    }
    template = {
        'id': 'spell-conjure-fey-manifestation',
        'sourceClassId': 'spell',
        'sourceFeatureId': 'spell:conjure-fey',
        'summonOrigin': 'spell',
        'spellId': 'conjure-fey',
        'temporary': True,
        'concentrationRequired': True,
        'durationSeconds': 3600,
        'cleanupPolicy': ['dismiss', 'duration_expiry'],
        'controlModel': 'caster_owned_independent_effect',
    }

    row = build_active_deployment_entry(
        actor=actor,
        template=template,
        token_id='tok-spell',
        owner_user=owner,
        profile_id='profile-spellcaster',
        selected_variant='spell-conjure-fey-manifestation',
        map_context='world',
        created_at=1000.0,
    )

    assert row['entityKind'] == 'spell_effect'
    assert row['sourceOriginType'] == 'spell'
    assert row['tokenId'] == 'tok-spell'
    assert row['ownerProfileId'] == 'profile-spellcaster'
    assert row['expiresAt'] == 4600.0
    assert row['controlModel'] == 'caster_owned_independent_effect'


def test_normalize_deployment_ui_entry_emits_consistent_ui_metadata():
    token = Token(
        id='tok-1',
        name='⚙️ Arc Cannon',
        x=0,
        y=0,
        width=32,
        height=32,
        color='#fff',
        shape='square',
        owner_id='u1',
        token_type='companion',
        map_context='world',
    )
    ui_entry = normalize_deployment_ui_entry(
        active_entry={
            'id': 'active-arc',
            'entityKind': 'deployable',
            'sourceOriginType': 'feature',
            'temporary': False,
            'controlModel': 'owner_commanded',
            'actor': {'name': 'Arc Cannon'},
        },
        token=token,
        owner_name='Rook',
        owner_bucket_key='rook',
        profile_index=0,
        profile_id='profile-artillerist',
    )

    assert ui_entry['ownerName'] == 'Rook'
    assert ui_entry['tokenPresent'] is True
    assert ui_entry['ui']['entityLabel'] == 'Arc Cannon'
    assert ui_entry['ui']['kindLabel'] == 'deployable'
    assert ui_entry['ui']['originLabel'] == 'feature'
    assert ui_entry['ui']['controllable'] is True


def test_normalize_summon_state_backfills_pass_k_shared_fields():
    state = normalize_summon_state(
        {
            'activeSummons': [
                {
                    'id': 'active-1',
                    'templateId': 'tinker-artillerist-arc-cannon',
                    'sourceFeatureId': 'artillerist-arc-cannon',
                    'tokenId': 'tok-cannon',
                    'ownerProfileId': 'profile-artillerist',
                    'commandModel': 'action_command',
                    'actor': {'actorType': 'deployable'},
                }
            ]
        }
    )
    row = state['activeSummons'][0]

    assert row['entityId'] == 'active-1'
    assert row['entityKind'] == 'deployable'
    assert row['sourceOriginType'] == 'feature'
    assert row['controlModel'] == 'action_command'
    assert row['lifecycle']['status'] == 'active'
