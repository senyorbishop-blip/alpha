"""Tests for two combat/dice fixes:

1. Deleted tokens must leave the initiative roster mid-combat (no ghost
   combatants), via remove_token_from_combat / sync pruning / per-user filtering.
2. Non-initiative dice rolls are private to the roller + DM(s); only initiative
   is broadcast to the whole table.
"""
import asyncio

from server.session import Session, Token, User
from server.handlers.combat import (
    remove_token_from_combat,
    sync_fogged_combatants,
)
from server.handlers.common import _combat_state_payload_for_user, _prune_deleted_token_combatants
from server.handlers import content as content_handlers


def tok(id, typ='monster', owner=None):
    return Token(id=id, name=id.title(), x=0, y=0, width=50, height=50, color='#999',
                 shape='circle', owner_id=owner, token_type=typ, map_context='world',
                 hp=7, max_hp=10, speed=30)


def combatant(t, init=18):
    return {'id': f'combat-{t.id}', 'token_id': t.id, 'name': t.name, 'initiative': init,
            'roll': 15, 'modifier': 3, 'hp': t.hp, 'max_hp': t.max_hp, 'speed': t.speed,
            'map_context': 'world'}


def base_session():
    s = Session(id='s')
    s.dm_map_context = 'world'
    s.combat = {'active': True, 'turn': 0, 'round': 1, 'combatants': []}
    return s


# ── Issue 2: deleted tokens leave combat ────────────────────────────────────

def test_remove_token_from_combat_drops_combatant():
    s = base_session()
    g, o = tok('goblin'), tok('orc')
    s.tokens.update({g.id: g, o.id: o})
    s.combat['combatants'] = [combatant(g, 18), combatant(o, 12)]
    s.combat['turn'] = 1  # orc is current
    # Delete the orc's token, then prune combat.
    s.tokens.pop('orc', None)
    changed = remove_token_from_combat(s, 'orc')
    assert changed is True
    assert [c['token_id'] for c in s.combat['combatants']] == ['goblin']
    assert 0 <= s.combat['turn'] <= 0


def test_remove_token_from_combat_keeps_active_pointer_on_survivor():
    s = base_session()
    g, o = tok('goblin'), tok('orc')
    s.tokens.update({g.id: g, o.id: o})
    s.combat['combatants'] = [combatant(g, 18), combatant(o, 12)]
    s.combat['turn'] = 1  # orc is current and survives
    s.tokens.pop('goblin', None)
    changed = remove_token_from_combat(s, 'goblin')
    assert changed is True
    assert [c['token_id'] for c in s.combat['combatants']] == ['orc']
    assert s.combat['combatants'][s.combat['turn']]['token_id'] == 'orc'


def test_remove_token_not_in_combat_is_noop():
    s = base_session()
    g = tok('goblin')
    s.tokens[g.id] = g
    s.combat['combatants'] = [combatant(g)]
    assert remove_token_from_combat(s, 'ghost') is False
    assert [c['token_id'] for c in s.combat['combatants']] == ['goblin']


def test_remove_token_also_prunes_suspended_lists():
    s = base_session()
    s.combat['combatants'] = []
    s.combat['suspended_combatants'] = [{'token_id': 'goblin', 'name': 'Goblin', 'suspended_reasons': ['fog']}]
    s.combat['fog_suspended_combatants'] = [{'token_id': 'goblin', 'name': 'Goblin', 'suspended_reasons': ['fog']}]
    assert remove_token_from_combat(s, 'goblin') is True
    assert s.combat['suspended_combatants'] == []
    assert s.combat['fog_suspended_combatants'] == []


def test_sync_prunes_combatant_whose_token_was_deleted():
    s = base_session()
    g = tok('goblin')
    s.combat['combatants'] = [combatant(g)]  # token never added / already deleted
    result = sync_fogged_combatants(s, 'test', 'world')
    assert result['changed'] is True
    assert s.combat['combatants'] == []


def test_player_view_hides_ghost_combatant():
    s = base_session()
    g = tok('goblin')
    # Combatant references a token id that no longer exists.
    s.combat['combatants'] = [combatant(g)]
    player = User(id='u1', name='Hero', role='player')
    out = _combat_state_payload_for_user(s, player, 1)
    assert [c['token_id'] for c in out['combatants']] == []


def test_player_view_keeps_manual_combatant_without_token():
    s = base_session()
    manual = {'id': 'm1', 'token_id': '', 'name': 'Lair Trap', 'initiative': 20}
    s.combat['combatants'] = [manual]
    player = User(id='u1', name='Hero', role='player')
    out = _combat_state_payload_for_user(s, player, 1)
    assert [c['name'] for c in out['combatants']] == ['Lair Trap']


def test_central_prune_removes_ghost_and_keeps_manual():
    s = base_session()
    g = tok('goblin')
    s.tokens[g.id] = g
    manual = {'id': 'm1', 'token_id': '', 'name': 'Trap', 'initiative': 25}
    ghost = combatant(tok('wraith'), 10)  # wraith token not in session.tokens
    s.combat['combatants'] = [manual, combatant(g, 18), ghost]
    s.combat['turn'] = 2  # ghost is current
    changed = _prune_deleted_token_combatants(s)
    assert changed is True
    ids = [c.get('token_id') or c.get('name') for c in s.combat['combatants']]
    assert ids == ['Trap', 'goblin']
    assert 0 <= s.combat['turn'] <= 1


def test_central_prune_noop_when_all_tokens_present():
    s = base_session()
    g = tok('goblin')
    s.tokens[g.id] = g
    s.combat['combatants'] = [combatant(g)]
    assert _prune_deleted_token_combatants(s) is False


# ── Issue 1: dice roll privacy ──────────────────────────────────────────────

class _Capture:
    """Stand-in for manager: records broadcast vs per-user sends."""
    def __init__(self):
        self.broadcasts = []
        self.sent = []  # (user_id, message)

    async def broadcast(self, session_id, message, exclude_user=None):
        self.broadcasts.append(message)

    async def send_to(self, session_id, user_id, message):
        self.sent.append((user_id, message))
        return True


def _dice_session():
    s = base_session()
    s.combat = {'active': False, 'turn': 0, 'round': 1, 'combatants': []}
    s.users = {
        'dm1': User(id='dm1', name='DM', role='dm'),
        'p1': User(id='p1', name='Alice', role='player'),
        'p2': User(id='p2', name='Bob', role='player'),
    }
    return s


def _run_roll(monkeypatch_manager, session, user, label):
    payload = {'dice_type': 20, 'quantity': 1, 'modifier': 2, 'roll_label': label, 'seed': 42}
    asyncio.run(content_handlers.handle_dice_roll(payload, session, user))


def test_attack_roll_is_private(monkeypatch):
    s = _dice_session()
    cap = _Capture()
    monkeypatch.setattr(content_handlers, 'manager', cap)
    _run_roll(cap, s, s.users['p1'], 'Longsword Attack')
    # No broadcast; only the roller receives it by default (not even the DM).
    dice_msgs = [m for m in cap.broadcasts if m.get('type') == 'dice_result']
    assert dice_msgs == []
    recipients = {uid for uid, m in cap.sent if m.get('type') == 'dice_result'}
    assert recipients == {'p1'}
    assert 'p2' not in recipients
    assert 'dm1' not in recipients
    # Private rolls are not persisted to the shared session log.
    assert all(e.get('type') != 'dice' for e in s.log)


def test_initiative_roll_is_private_by_default(monkeypatch):
    """An "initiative"-labelled roll is no longer special-cased as public.

    The combat initiative tracker is synced separately via combat_state, so the
    dice popup stays private to the roller. The label alone must NOT broadcast
    the dice_result to the whole table anymore.
    """
    s = _dice_session()
    cap = _Capture()
    monkeypatch.setattr(content_handlers, 'manager', cap)
    _run_roll(cap, s, s.users['p1'], 'Initiative')
    dice_msgs = [m for m in cap.broadcasts if m.get('type') == 'dice_result']
    assert dice_msgs == []
    recipients = {uid for uid, m in cap.sent if m.get('type') == 'dice_result'}
    assert recipients == {'p1'}
    assert 'p2' not in recipients
    assert 'dm1' not in recipients
    # Private rolls are not persisted to the shared session log.
    assert all(e.get('type') != 'dice' for e in s.log)


def test_visibility_dm_includes_roller_and_dm(monkeypatch):
    """visibility="dm" delivers the popup to the roller plus the DM(s)."""
    s = _dice_session()
    cap = _Capture()
    monkeypatch.setattr(content_handlers, 'manager', cap)
    payload = {'dice_type': 20, 'quantity': 1, 'modifier': 2, 'roll_label': 'Stealth',
               'seed': 42, 'visibility': 'dm'}
    asyncio.run(content_handlers.handle_dice_roll(payload, s, s.users['p1']))
    assert [m for m in cap.broadcasts if m.get('type') == 'dice_result'] == []
    recipients = {uid for uid, m in cap.sent if m.get('type') == 'dice_result'}
    assert recipients == {'p1', 'dm1'}
    assert 'p2' not in recipients
    # DM-scoped private rolls still stay out of the shared session log.
    assert all(e.get('type') != 'dice' for e in s.log)


def test_visibility_table_broadcasts_to_everyone(monkeypatch):
    """visibility="table" broadcasts the dice_result and persists the log."""
    s = _dice_session()
    cap = _Capture()
    monkeypatch.setattr(content_handlers, 'manager', cap)
    payload = {'dice_type': 20, 'quantity': 1, 'modifier': 0, 'roll_label': 'Perception',
               'seed': 42, 'visibility': 'table'}
    asyncio.run(content_handlers.handle_dice_roll(payload, s, s.users['p1']))
    dice_msgs = [m for m in cap.broadcasts if m.get('type') == 'dice_result']
    assert len(dice_msgs) == 1
    # Table rolls are persisted to the session log so they survive reconnect.
    assert any(e.get('type') == 'dice' for e in s.log)


def test_private_nat20_fx_follows_dice_result_audience(monkeypatch):
    """A private nat20 sends its dice_special_fx to exactly the same audience as
    the dice_result — the roller only (never broadcast)."""
    s = _dice_session()
    cap = _Capture()
    monkeypatch.setattr(content_handlers, 'manager', cap)
    # seed=5 yields a natural 20 on the first d20.
    payload = {'dice_type': 20, 'quantity': 1, 'modifier': 0, 'roll_label': 'Stealth', 'seed': 5}
    asyncio.run(content_handlers.handle_dice_roll(payload, s, s.users['p1']))
    # Nothing broadcast for a private roll.
    assert [m for m in cap.broadcasts if m.get('type') == 'dice_special_fx'] == []
    fx_recipients = {uid for uid, m in cap.sent if m.get('type') == 'dice_special_fx'}
    dice_recipients = {uid for uid, m in cap.sent if m.get('type') == 'dice_result'}
    assert fx_recipients, "a nat20 must emit a dice_special_fx event"
    assert fx_recipients == dice_recipients == {'p1'}


def test_table_nat20_fx_follows_dice_result_audience(monkeypatch):
    """A visibility="table" nat20 broadcasts the dice_special_fx to the table,
    mirroring the dice_result broadcast."""
    s = _dice_session()
    cap = _Capture()
    monkeypatch.setattr(content_handlers, 'manager', cap)
    payload = {'dice_type': 20, 'quantity': 1, 'modifier': 0, 'roll_label': 'Initiative',
               'seed': 5, 'visibility': 'table'}
    asyncio.run(content_handlers.handle_dice_roll(payload, s, s.users['p1']))
    fx_broadcasts = [m for m in cap.broadcasts if m.get('type') == 'dice_special_fx']
    dice_broadcasts = [m for m in cap.broadcasts if m.get('type') == 'dice_result']
    assert len(dice_broadcasts) == 1
    assert len(fx_broadcasts) == 1
    assert fx_broadcasts[0]['payload']['fx_type'] == 'nat20'
    # No private per-user FX sends when the roll is public.
    assert [uid for uid, m in cap.sent if m.get('type') == 'dice_special_fx'] == []
