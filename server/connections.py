"""
server/connections.py — WebSocket connection registry and broadcaster
"""
import json
import logging
import uuid
from typing import Dict, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Dict[str, WebSocket]] = {}
        self._connection_ids: Dict[str, Dict[str, str]] = {}

    def get_session_connections(self, session_id: str) -> Dict[str, WebSocket]:
        return self._connections.get(session_id, {})

    async def connect(self, session_id: str, user_id: str, websocket: WebSocket, role: str | None = None, connection_id: str | None = None) -> str:
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = {}
        if session_id not in self._connection_ids:
            self._connection_ids[session_id] = {}
        connection_id = connection_id or uuid.uuid4().hex
        prior = self._connections[session_id].get(user_id)
        if prior and prior is not websocket:
            logger.warning(
                "[ws] replacing socket session_id=%s user_id=%s role=%s old_socket_replaced=true new_socket_connected=false",
                session_id, user_id, role or "unknown",
            )
            try:
                await prior.close(code=1001, reason="Replaced by a newer connection")
            except Exception as exc:
                logger.warning(
                    "[ws] old socket close failed during replacement session_id=%s user_id=%s role=%s error=%s",
                    session_id, user_id, role or "unknown", exc,
                )
        self._connections[session_id][user_id] = websocket
        self._connection_ids[session_id][user_id] = connection_id
        logger.info(
            "[ws] connected session_id=%s user_id=%s role=%s old_socket_replaced=%s new_socket_connected=true",
            session_id, user_id, role or "unknown", bool(prior and prior is not websocket),
        )
        return connection_id

    def disconnect(self, session_id: str, user_id: str, websocket: Optional[WebSocket] = None) -> bool:
        if session_id in self._connections:
            if websocket is not None:
                current = self._connections[session_id].get(user_id)
                if current is not websocket:
                    return False
            self._connections[session_id].pop(user_id, None)
            if session_id in self._connection_ids:
                self._connection_ids[session_id].pop(user_id, None)
                if not self._connection_ids[session_id]:
                    del self._connection_ids[session_id]
            if not self._connections[session_id]:
                del self._connections[session_id]
            return True
        return False

    async def send_to(self, session_id: str, user_id: str, message: dict) -> bool:
        ws = self._connections.get(session_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
                return True
            except Exception:
                logger.warning("[ws] send_to failed session_id=%s user_id=%s message_type=%s", session_id, user_id, message.get("type"))
                self.disconnect(session_id, user_id)
        return False

    async def broadcast(self, session_id: str, message: dict, exclude_user: Optional[str] = None):
        connections = dict(self._connections.get(session_id, {}))
        payload = json.dumps(message)
        dead = []
        for uid, ws in connections.items():
            if uid == exclude_user:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(session_id, uid)

    async def broadcast_to_role(self, session_id: str, message: dict, roles: Set[str], session_obj):
        connections = dict(self._connections.get(session_id, {}))
        payload = json.dumps(message)
        dead = []
        for uid, ws in connections.items():
            user = session_obj.users.get(uid)
            if user and user.role in roles:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(uid)
        for uid in dead:
            self.disconnect(session_id, uid)

    async def broadcast_filtered(self, session_id: str, message: dict,
                                 hide_hidden_tokens: bool = False, dm_id: str = None,
                                 session_obj=None):
        """Broadcast with token visibility filtering.

        Hidden tokens are replaced with a token_removed_hidden notification for
        non-DM recipients.  DM-created tokens (no owner_id) ARE visible to all
        non-DM users unless they are explicitly marked hidden — the original
        implementation incorrectly dropped ownerless tokens for non-DMs.

        NOTE: This method is currently unused; all token-specific broadcasts use
        _broadcast_token_event() in handlers/common.py which applies per-user
        visibility filtering.  Kept for potential future use.
        """
        connections = dict(self._connections.get(session_id, {}))
        dm_payload = json.dumps(message)
        dead = []
        for uid, ws in connections.items():
            try:
                is_dm = (uid == dm_id)
                if not is_dm and hide_hidden_tokens:
                    payload_data = message.get("payload", {})
                    token = payload_data.get("token") if isinstance(payload_data, dict) else None
                    if token and token.get("hidden"):
                        alt = json.dumps({"type": "token_removed_hidden", "payload": {"id": token["id"]}})
                        await ws.send_text(alt)
                        continue
                    # Note: tokens without owner_id are DM-created NPCs and ARE
                    # visible to players (unless hidden=True, handled above).
                await ws.send_text(dm_payload)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(session_id, uid)

    def is_connected(self, session_id: str, user_id: str) -> bool:
        return user_id in self._connections.get(session_id, {})

    def get_socket(self, session_id: str, user_id: str) -> Optional[WebSocket]:
        return self._connections.get(session_id, {}).get(user_id)

    def get_connection_id(self, session_id: str, user_id: str) -> Optional[str]:
        return self._connection_ids.get(session_id, {}).get(user_id)

    def is_current_connection(self, session_id: str, user_id: str, connection_id: str) -> bool:
        return self.get_connection_id(session_id, user_id) == connection_id

    def get_active_session_ids(self) -> list:
        """Return a snapshot of all currently active session IDs."""
        return list(self._connections.keys())


manager = ConnectionManager()
