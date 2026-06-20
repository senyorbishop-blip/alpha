from server.session import Session, Token, User
from server.handlers.combat import sync_fogged_combatants, is_token_visible_to_party
from server.handlers.common import _combat_state_payload_for_user


def tok(id, typ='monster', owner=None, x=0, y=0, hidden=False, staged=False):
    return Token(id=id, name=id.title(), x=x, y=y, width=50, height=50, color='#999', shape='circle', owner_id=owner, token_type=typ, hidden=hidden, staged=staged, map_context='world', hp=7, max_hp=10, speed=30)


def session_with_fog(revealed=True):
    s = Session(id='s')
    s.dm_map_context = 'world'
    cells = ['0'] * 16
    if revealed:
        cells[10] = '1'  # token center at (0,0) for 4x4 grid over default map
    s.fog_maps = {'world': {'enabled': True, 'cols': 4, 'rows': 4, 'cells': ''.join(cells)}}
    s.combat = {'active': True, 'turn': 0, 'round': 1, 'combatants': []}
    return s


def combatant(t, init=18):
    return {'id': f'combat-{t.id}', 'token_id': t.id, 'name': t.name, 'initiative': init, 'roll': 15, 'modifier': 3, 'hp': t.hp, 'max_hp': t.max_hp, 'speed': t.speed, 'map_context': 'world'}


def test_npc_combatant_visible_remains_in_combatants():
    s = session_with_fog(True); g = tok('goblin'); s.tokens[g.id] = g; s.combat['combatants'] = [combatant(g)]
    result = sync_fogged_combatants(s, 'test', 'world')
    assert result['changed'] is False
    assert [c['token_id'] for c in s.combat['combatants']] == ['goblin']


def test_npc_combatant_fogged_moves_to_suspended():
    s = session_with_fog(False); g = tok('goblin'); s.tokens[g.id] = g; s.combat['combatants'] = [combatant(g)]
    result = sync_fogged_combatants(s, 'test', 'world')
    assert result['changed'] is True
    assert s.combat['combatants'] == []
    assert s.combat['fog_suspended_combatants'][0]['token_id'] == 'goblin'
    assert s.combat['fog_suspended_combatants'][0]['initiative'] == 18


def test_suspended_npc_visible_again_restored_with_same_initiative():
    s = session_with_fog(False); g = tok('goblin'); s.tokens[g.id] = g; s.combat['combatants'] = [combatant(g, 18)]
    sync_fogged_combatants(s, 'test', 'world')
    s.fog_maps['world']['cells'] = '0' * 10 + '1' + '0' * 5
    result = sync_fogged_combatants(s, 'test', 'world')
    assert result['changed'] is True
    assert s.combat['combatants'][0]['token_id'] == 'goblin'
    assert s.combat['combatants'][0]['initiative'] == 18
    assert s.combat['suspended_combatants'] == []


def test_player_combatant_fogged_remains_in_combatants():
    s = session_with_fog(False); pc = tok('hero', typ='player', owner='u1'); s.tokens[pc.id] = pc; s.combat['combatants'] = [combatant(pc)]
    result = sync_fogged_combatants(s, 'test', 'world')
    assert result['changed'] is False
    assert s.combat['combatants'][0]['token_id'] == 'hero'


def test_hidden_or_staged_npc_visible_not_auto_added():
    s = session_with_fog(True); h = tok('hidden', hidden=True); st = tok('staged', staged=True); s.tokens[h.id] = h; s.tokens[st.id] = st
    sync_fogged_combatants(s, 'test', 'world')
    assert s.combat['combatants'] == []


def test_current_turn_removed_turn_index_valid():
    s = session_with_fog(False); g = tok('goblin'); o = tok('orc'); s.tokens[g.id] = g; s.tokens[o.id] = o
    s.combat['combatants'] = [combatant(g, 18), combatant(o, 12)]; s.combat['turn'] = 0
    sync_fogged_combatants(s, 'test', 'world')
    assert 0 <= s.combat['turn'] <= max(0, len(s.combat['combatants']) - 1)


def test_repeated_sync_no_duplicates_or_repeat_changes():
    s = session_with_fog(True); g = tok('goblin'); s.tokens[g.id] = g
    first = sync_fogged_combatants(s, 'test', 'world')
    second = sync_fogged_combatants(s, 'test', 'world')
    assert first['changed'] is True
    assert second['changed'] is False
    assert [c['token_id'] for c in s.combat['combatants']] == ['goblin']


def test_hidden_npc_in_fog_keeps_multiple_suspension_reasons_until_clear():
    s = session_with_fog(False); g = tok('goblin', hidden=True); s.tokens[g.id] = g; s.combat['combatants'] = [combatant(g, 18)]
    sync_fogged_combatants(s, 'test', 'world')
    reasons = set(s.combat['suspended_combatants'][0]['suspended_reasons'])
    assert reasons == {'hidden', 'fog'}
    g.hidden = False
    sync_fogged_combatants(s, 'test', 'world')
    assert s.combat['combatants'] == []
    assert set(s.combat['suspended_combatants'][0]['suspended_reasons']) == {'fog'}
    s.fog_maps['world']['cells'] = '0' * 10 + '1' + '0' * 5
    sync_fogged_combatants(s, 'test', 'world')
    assert s.combat['combatants'][0]['token_id'] == 'goblin'
    assert s.combat['combatants'][0]['initiative'] == 18


def test_hidden_npc_combatant_moves_to_suspended_and_restores_when_unhidden():
    s = session_with_fog(True); g = tok('goblin', hidden=False); s.tokens[g.id] = g; s.combat['combatants'] = [combatant(g, 18)]
    g.hidden = True
    result = sync_fogged_combatants(s, 'hidden_changed', 'world')
    assert result['changed'] is True
    assert s.combat['combatants'] == []
    assert s.combat['hidden_suspended_combatants'][0]['token_id'] == 'goblin'
    assert s.combat['hidden_suspended_combatants'][0]['initiative'] == 18
    g.hidden = False
    result = sync_fogged_combatants(s, 'hidden_changed', 'world')
    assert result['changed'] is True
    assert s.combat['combatants'][0]['token_id'] == 'goblin'
    assert s.combat['combatants'][0]['initiative'] == 18
    assert s.combat['suspended_combatants'] == []


def test_dm_payload_keeps_suspended_fogged_combatant_metadata():
    s = session_with_fog(False); mage = tok('mage'); s.tokens[mage.id] = mage; s.combat['combatants'] = [combatant(mage, 12)]
    sync_fogged_combatants(s, 'test', 'world')
    payload = _combat_state_payload_for_user(s, User(id='dm1', name='DM', role='dm'), 7)
    assert payload['combatants'] == []
    assert payload['suspended_combatants'][0]['token_id'] == 'mage'
    assert payload['suspended_combatants'][0]['initiative'] == 12
    assert payload['suspended_combatants'][0]['suspended_reasons'] == ['fog']
    assert payload['visibility_revision'] == 7


def test_player_payload_strips_fogged_combatant_and_suspended_metadata():
    s = session_with_fog(False); mage = tok('mage'); s.tokens[mage.id] = mage; s.combat['combatants'] = [combatant(mage, 12)]
    sync_fogged_combatants(s, 'test', 'world')
    payload = _combat_state_payload_for_user(s, User(id='p1', name='Player', role='player'), 8)
    assert payload['combatants'] == []
    assert 'suspended_combatants' not in payload
    assert 'fog_suspended_combatants' not in payload
    assert 'hidden_suspended_combatants' not in payload
    assert payload['visibility_revision'] == 8


def test_fogged_npc_reappears_in_player_payload_after_reveal_without_refresh():
    s = session_with_fog(False); mage = tok('mage'); s.tokens[mage.id] = mage; s.combat['combatants'] = [combatant(mage, 12)]
    sync_fogged_combatants(s, 'test', 'world')
    hidden_payload = _combat_state_payload_for_user(s, User(id='p1', name='Player', role='player'), 8)
    assert hidden_payload['combatants'] == []
    s.fog_maps['world']['cells'] = '0' * 10 + '1' + '0' * 5
    sync_fogged_combatants(s, 'test', 'world')
    visible_payload = _combat_state_payload_for_user(s, User(id='p1', name='Player', role='player'), 9)
    assert [c['token_id'] for c in visible_payload['combatants']] == ['mage']
    assert visible_payload['combatants'][0]['initiative'] == 12
    assert 'suspended_combatants' not in visible_payload
