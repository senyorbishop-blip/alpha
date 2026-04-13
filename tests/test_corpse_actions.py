import asyncio
import random

from server.handlers.inventory import _resolve_corpse_action, _corpse_dm_config, handle_corpse_harvest
from server.handlers.tokens import handle_token_hp_update
from server.persistence_schema import extract_persistable_campaign_state, normalize_persisted_campaign_data
from server.session import Session, User, Token


def _build_session():
    s = Session(id='TEST1234')
    dm = User(id='dm1', name='DM', role='dm')
    player = User(id='pl1', name='Player', role='player')
    s.users[dm.id] = dm
    s.users[player.id] = player
    s.dm_id = dm.id
    tok = Token(
        id='tok1', name='Wolf', x=0, y=0, width=40, height=40,
        color='#fff', shape='circle', owner_id=None, hp=12, max_hp=12,
        token_type='monster', creature_id='wolf_srd', creature_type='monster', monster_type='beast', cr='1',
    )
    s.tokens[tok.id] = tok
    return s, dm, player, tok


def test_corpse_state_created_when_monster_hits_zero_hp():
    s, dm, _player, tok = _build_session()
    asyncio.run(handle_token_hp_update({'token_id': tok.id, 'hp': 0}, s, dm))
    assert tok.hp == 0
    assert tok.id in s.corpse_states
    corpse = s.corpse_states[tok.id]
    assert corpse['creature_ref']['creature_id'] == 'wolf_srd'
    assert corpse['depleted'] is False


def test_failure_yields_nothing_and_attempts_are_server_tracked():
    s, _dm, player, tok = _build_session()
    s.corpse_states[tok.id] = {
        'corpse_id': tok.id,
        'token_id': tok.id,
        'token_name': tok.name,
        'depleted': False,
        'search_attempts': {},
        'harvest_attempts': {},
        'creature_ref': {'monster_type': 'beast', 'cr': '10'},
    }
    # Force a low roll to fail
    rng = random.Random(1)
    result = _resolve_corpse_action(action='harvest', corpse=s.corpse_states[tok.id], session=s, user=player, rng=rng)
    if result['success']:
        # Retry once with another deterministic seed if this seed hits success.
        result = _resolve_corpse_action(action='harvest', corpse=s.corpse_states[tok.id], session=s, user=player, rng=random.Random(2))
    assert result['success'] is False
    assert result['rewards'] == []
    assert int(s.corpse_states[tok.id]['harvest_attempts'][player.id]) >= 1


def test_deterministic_success_with_seeded_rng():
    s, _dm, player, tok = _build_session()
    corpse = {
        'corpse_id': tok.id,
        'token_id': tok.id,
        'token_name': tok.name,
        'depleted': False,
        'search_attempts': {},
        'harvest_attempts': {},
        'creature_ref': {'monster_type': 'dragon', 'cr': '2'},
    }
    s.corpse_states[tok.id] = corpse

    r1 = _resolve_corpse_action(action='search', corpse=corpse, session=s, user=player, rng=random.Random(7))
    corpse2 = {
        **corpse,
        'search_attempts': {},
        'harvest_attempts': {},
        'depleted': False,
    }
    r2 = _resolve_corpse_action(action='search', corpse=corpse2, session=s, user=player, rng=random.Random(7))
    assert r1['roll'] == r2['roll']
    assert r1['success'] == r2['success']
    assert r1['rewards'] == r2['rewards']


def test_attempt_limits_prevent_unlimited_harvest():
    s, _dm, player, tok = _build_session()
    s.corpse_dm_config = {'harvest_attempts_per_corpse': 1, 'search_attempts_per_corpse': 1}
    _corpse_dm_config(s)
    s.corpse_states[tok.id] = {
        'corpse_id': tok.id,
        'token_id': tok.id,
        'token_name': tok.name,
        'depleted': False,
        'search_attempts': {},
        'harvest_attempts': {player.id: 1},
        'creature_ref': {'monster_type': 'beast', 'cr': '1'},
    }
    tok.hp = 0
    asyncio.run(handle_corpse_harvest({'corpse_id': tok.id}, s, player))
    assert s.corpse_states[tok.id]['harvest_attempts'][player.id] == 1


def test_corpse_persistence_roundtrip_fields():
    s, _dm, _player, tok = _build_session()
    s.corpse_states[tok.id] = {
        'corpse_id': tok.id,
        'token_id': tok.id,
        'token_name': tok.name,
        'depleted': False,
        'search_attempts': {'pl1': 1},
        'harvest_attempts': {},
        'creature_ref': {'monster_type': 'beast', 'cr': '1'},
    }
    s.corpse_dm_config = {'search_attempts_per_corpse': 2, 'harvest_attempts_per_corpse': 1}

    persisted = extract_persistable_campaign_state(s)
    rehydrated = normalize_persisted_campaign_data(persisted)
    assert tok.id in rehydrated['corpse_states']
    assert rehydrated['corpse_states'][tok.id]['search_attempts']['pl1'] == 1
    assert rehydrated['corpse_dm_config']['search_attempts_per_corpse'] == 2


def test_viewer_cannot_harvest():
    s, _dm, _player, tok = _build_session()
    viewer = User(id='vw1', name='Viewer', role='viewer')
    s.users[viewer.id] = viewer
    tok.hp = 0
    s.corpse_states[tok.id] = {
        'corpse_id': tok.id,
        'token_id': tok.id,
        'token_name': tok.name,
        'depleted': False,
        'search_attempts': {},
        'harvest_attempts': {},
        'creature_ref': {'monster_type': 'beast', 'cr': '1'},
    }
    asyncio.run(handle_corpse_harvest({'corpse_id': tok.id}, s, viewer))
    assert s.corpse_states[tok.id]['harvest_attempts'] == {}


def test_corpse_rewards_include_rarity_labels():
    class _RiggedRng:
        def randint(self, a, b):
            return int(b)

        def choice(self, seq):
            return seq[0]

    s, _dm, player, tok = _build_session()
    tok.hp = 0
    corpse = {
        'corpse_id': tok.id,
        'token_id': tok.id,
        'token_name': tok.name,
        'depleted': False,
        'search_attempts': {},
        'harvest_attempts': {},
        'creature_ref': {'monster_type': 'dragon', 'cr': '12'},
    }
    s.corpse_states[tok.id] = corpse
    result = _resolve_corpse_action(action='harvest', corpse=corpse, session=s, user=player, rng=_RiggedRng())
    assert result['success'] is True
    assert result['rewards']
    assert all(str(item.get('rarity') or '').strip() for item in result['rewards'])
