import asyncio

from server.handlers import summons as summon_handlers
from server.session import Session, User, Token


def test_summon_action_use_applies_damage_and_logs(monkeypatch):
    session = Session(id='SUMMONF')
    player = User(id='u1', name='Ayla', role='player')
    target_owner = User(id='u2', name='Bram', role='player')
    session.users[player.id] = player
    session.users[target_owner.id] = target_owner

    session.tokens['tok-summon'] = Token(id='tok-summon', name='🐾 Beast', x=0, y=0, width=40, height=40, color='#fff', shape='circle', owner_id=player.id, token_type='companion', hp=20, max_hp=20)
    session.tokens['tok-target'] = Token(id='tok-target', name='Goblin', x=0, y=0, width=40, height=40, color='#fff', shape='circle', owner_id='', token_type='monster', hp=18, max_hp=18)

    session.char_profiles = {
        player.name.lower(): [
            {
                'id': 'profile-ranger',
                'nativeCharacter': {
                    'summons': {
                        'activeSummons': [
                            {
                                'id': 'active-1',
                                'tokenId': 'tok-summon',
                                'ownerProfileId': 'profile-ranger',
                                'actor': {
                                    'name': 'Primal Beast',
                                    'commandModel': 'bonus_action_command',
                                    'actions': [
                                        {
                                            'id': 'maul',
                                            'displayName': 'Maul',
                                            'actionType': 'action',
                                            'classification': 'attack',
                                            'damage': {'formula': '1d6+2', 'type': 'force'},
                                            'summary': 'Test strike.',
                                            'commandModel': 'bonus_action_command',
                                        }
                                    ],
                                    'hp': {'current': 20, 'max': 20},
                                },
                            }
                        ]
                    }
                },
            }
        ]
    }

    sent = []
    async def _send_to(*args, **kwargs):
        sent.append((args, kwargs))
    async def _broadcast(*args, **kwargs):
        sent.append((args, kwargs))
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(summon_handlers.manager, 'send_to', _send_to)
    monkeypatch.setattr(summon_handlers.manager, 'broadcast', _broadcast)
    monkeypatch.setattr(summon_handlers, 'save_campaign_async', _noop)
    monkeypatch.setattr(summon_handlers, '_send_char_profiles', _noop)

    asyncio.run(
        summon_handlers.handle_summon_action_use(
            {'token_id': 'tok-summon', 'action_id': 'maul', 'target_id': 'tok-target'},
            session,
            player,
        )
    )

    assert session.tokens['tok-target'].hp < 18
    assert any((call[0][2] if len(call[0]) > 2 else {}).get('type') == 'summon_action_result' for call in sent if call[0])
