from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import config

_attempts_lock = Lock()
_attempts: dict[str, deque[float]] = defaultdict(deque)


def _serializer() -> URLSafeTimedSerializer:
    if not config.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured")
    return URLSafeTimedSerializer(config.SECRET_KEY, salt="artist-admin-session")


def verify_password(password: str) -> bool:
    if not config.ADMIN_PASSWORD_HASH:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            config.ADMIN_PASSWORD_HASH.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_session_token(username: str) -> str:
    return _serializer().dumps({"u": username})


def read_session_token(token: str) -> str | None:
    try:
        data = _serializer().loads(token, max_age=config.SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict):
        return None
    user = data.get("u")
    if user != config.ADMIN_USER:
        return None
    return str(user)


def login_allowed(ip: str) -> bool:
    now = time.time()
    with _attempts_lock:
        q = _attempts[ip]
        while q and now - q[0] > config.LOGIN_WINDOW_SEC:
            q.popleft()
        return len(q) < config.LOGIN_MAX_ATTEMPTS


def record_login_failure(ip: str) -> None:
    now = time.time()
    with _attempts_lock:
        q = _attempts[ip]
        while q and now - q[0] > config.LOGIN_WINDOW_SEC:
            q.popleft()
        q.append(now)


def clear_login_failures(ip: str) -> None:
    with _attempts_lock:
        _attempts.pop(ip, None)
