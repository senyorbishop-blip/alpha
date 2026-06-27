"""
server/twitch_ext/jwt_verify.py — Twitch Extension JWT + Bits receipt verification.

Every EBS call carries a Helper-issued JWT signed (HS256) with the base64
extension secret. Bits transactions additionally carry a signed receipt JWT.
We verify signature + ``exp`` on BOTH and never trust client-sent identity, sku,
or price — only what the signature attests.
"""
import jwt  # PyJWT (already a hard dependency via server.auth.jwt_utils)

from server.twitch_ext.config import secret_bytes

_ALGS = ["HS256"]


class ExtJWTError(Exception):
    """Raised when an Extension JWT / receipt fails verification."""


def _decode(token: str) -> dict:
    if not token or not isinstance(token, str):
        raise ExtJWTError("missing token")
    try:
        # require_exp + signature verification are the security boundary.
        return jwt.decode(
            token,
            secret_bytes(),
            algorithms=_ALGS,
            options={"require": ["exp"], "verify_exp": True, "verify_signature": True},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExtJWTError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ExtJWTError("invalid token") from exc
    except ValueError as exc:  # bad/missing secret
        raise ExtJWTError(str(exc)) from exc


def verify_ext_jwt(token: str) -> dict:
    """Verify a viewer/broadcaster Extension JWT and return normalized claims.

    Returns dict with: channel_id, user_id (real Twitch id, only present once
    the viewer shared identity), opaque_user_id, role, raw (full claims).
    """
    claims = _decode(token)
    channel_id = str(claims.get("channel_id") or "").strip()
    role = str(claims.get("role") or "").strip().lower()
    opaque = str(claims.get("opaque_user_id") or "").strip()
    # ``user_id`` is only present after the viewer grants identity share.
    user_id = str(claims.get("user_id") or "").strip()
    if not channel_id:
        raise ExtJWTError("missing channel_id")
    return {
        "channel_id": channel_id,
        "user_id": user_id,
        "opaque_user_id": opaque,
        "role": role,
        "raw": claims,
    }


def verify_bits_receipt(token: str) -> dict:
    """Verify a Bits transaction receipt JWT and return its essentials.

    Returns dict with: transaction_id, sku, user_id (Twitch id of the buyer),
    cost ({amount, type}), display_name, in_development.
    """
    claims = _decode(token)
    topic = str(claims.get("topic") or "").strip()
    if topic != "bits_transaction_receipt":
        raise ExtJWTError("not a bits transaction receipt")
    data = claims.get("data") if isinstance(claims.get("data"), dict) else {}
    product = data.get("product") if isinstance(data.get("product"), dict) else {}
    transaction_id = str(data.get("transactionId") or "").strip()
    sku = str(product.get("sku") or "").strip()
    if not transaction_id:
        raise ExtJWTError("missing transactionId")
    if not sku:
        raise ExtJWTError("missing product sku")
    return {
        "transaction_id": transaction_id,
        "sku": sku,
        "user_id": str(data.get("userId") or "").strip(),
        "cost": dict(product.get("cost") or {}),
        "display_name": str(product.get("displayName") or "").strip(),
        "in_development": bool(product.get("inDevelopment", False)),
    }
