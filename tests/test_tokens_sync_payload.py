import asyncio

from server.handlers import common as common_handlers
from server.session import Session, User, Token


class _CaptureManager:
    def __init__(self):
        self.sent = []

    async def send_to(self, session_id, user_id, message):
        self.sent.append((session_id, user_id, message))


def test_tokens_sync_includes_corpse_states(monkeypatch):
    session = Session(id='TESTSYNC')
    dm = User(id='dm1', name='DM', role='dm')
    player = User(id='pl1', name='Player', role='player')
    session.users[dm.id] = dm
    session.users[player.id] = player

    token = Token(
        id='tok1', name='Wolf', x=0, y=0, width=40, height=40,
        color='#fff', shape='circle', owner_id=None, hp=0, max_hp=12,
        token_type='monster',
    )
    session.tokens[token.id] = token
    session.corpse_states[token.id] = {
        'corpse_id': token.id,
        'token_id': token.id,
        'token_name': token.name,
        'depleted': False,
        'search_attempts': {},
        'harvest_attempts': {},
    }

    capture = _CaptureManager()
    monkeypatch.setattr(common_handlers, 'manager', capture)

    asyncio.run(common_handlers._broadcast_token_state_sync(session))

    assert capture.sent, 'expected tokens_sync messages'
    for _sid, _uid, msg in capture.sent:
        assert msg.get('type') == 'tokens_sync'
        payload = msg.get('payload') or {}
        assert payload.get('corpse_states') == session.corpse_states
