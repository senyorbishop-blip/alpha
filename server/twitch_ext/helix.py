"""
server/twitch_ext/helix.py — minimal Twitch Helix client for server-side
subscription verification (the sub-power path must not trust the client claim).

Uses an App Access Token (client_credentials) minted from the extension client
id + an OAuth client secret, cached in-memory until shortly before it expires.
"""
import time
import asyncio

import httpx

from server.twitch_ext.config import client_id, client_secret

_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
_SUBS_URL = "https://api.twitch.tv/helix/subscriptions/user"

_token_cache: dict = {"access_token": "", "expires_at": 0.0}
_token_lock = asyncio.Lock()


async def _app_access_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] - 60 > now:
        return _token_cache["access_token"]
    async with _token_lock:
        now = time.time()
        if _token_cache["access_token"] and _token_cache["expires_at"] - 60 > now:
            return _token_cache["access_token"]
        cid, csecret = client_id(), client_secret()
        if not cid or not csecret:
            raise RuntimeError("Helix app token requires TWITCH_EXT_CLIENT_ID and TWITCH_EXT_CLIENT_SECRET")
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.post(
                _TOKEN_URL,
                params={
                    "client_id": cid,
                    "client_secret": csecret,
                    "grant_type": "client_credentials",
                },
            )
        resp.raise_for_status()
        data = resp.json()
        token = str(data.get("access_token") or "")
        if not token:
            raise RuntimeError("Twitch did not return an app access token")
        _token_cache["access_token"] = token
        _token_cache["expires_at"] = time.time() + float(data.get("expires_in") or 3600)
        return token


async def is_subscribed(broadcaster_id: str, user_id: str) -> bool:
    """Return True if ``user_id`` has an active subscription to ``broadcaster_id``.

    Helix returns 200 with a populated ``data`` array when subscribed, and 404
    when not. Network/auth errors propagate so the caller can fail closed.
    """
    bid = str(broadcaster_id or "").strip()
    uid = str(user_id or "").strip()
    if not bid or not uid:
        return False
    token = await _app_access_token()
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.get(
            _SUBS_URL,
            params={"broadcaster_id": bid, "user_id": uid},
            headers={"Authorization": f"Bearer {token}", "Client-Id": client_id()},
        )
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    data = resp.json()
    return bool(data.get("data"))
