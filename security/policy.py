"""Fallback access policy + JWT decode + role cache."""

from __future__ import annotations

import time

from jose import JWTError, jwt

FALLBACK_POLICY: dict[str, dict[str, list[str]]] = {
    "admin": {
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        "minio_allowed": ["GetObject", "PutObject", "DeleteObject"],
    },
    "user": {
        "allowed_methods": ["GET"],
        "minio_allowed": ["GetObject"],
    },
}

CACHE_TTL = 300

_role_cache: dict[str, dict] = {}


def get_cached_role(user_id: str) -> str | None:
    entry = _role_cache.get(user_id)
    if not entry:
        return None
    if entry["expires_at"] < time.time():
        _role_cache.pop(user_id, None)
        return None
    return entry["role"]


def set_cached_role(user_id: str, role: str) -> None:
    _role_cache[user_id] = {"role": role, "expires_at": time.time() + CACHE_TTL}


def clear_cache() -> None:
    _role_cache.clear()


def check_fallback_access(role: str, method: str) -> bool:
    policy = FALLBACK_POLICY.get(role)
    if not policy:
        return False
    return method.upper() in policy["allowed_methods"]


def decode_jwt_role(token: str, secret: str) -> tuple[str, str]:
    """Decode a JWT and return (user_id, role).

    Role is taken from the ``role`` claim. If absent, defaults to ``"user"``.
    Raises ``JWTError`` on invalid token.
    """
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    user_id = payload.get("sub")
    if not user_id:
        raise JWTError("missing 'sub' claim")
    role = payload.get("role", "user")
    return str(user_id), str(role)
