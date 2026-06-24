"""Hermes Mission Control — auth module.
Single-user shared-password auth with signed session cookies.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

AUTH_DIR = Path(__file__).resolve().parent
PASSWORD_FILE = AUTH_DIR / ".mc-password"
SECRET_FILE = AUTH_DIR / ".mc-secret"

# Session lifetime: 24 hours
SESSION_MAX_AGE = 86400


def _ensure_secret() -> str:
    """Return a stable signing secret, creating one if absent."""
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text().strip()
    secret = secrets.token_hex(32)
    SECRET_FILE.write_text(secret)
    SECRET_FILE.chmod(0o600)
    return secret


_serializer = URLSafeTimedSerializer(
    secret_key=_ensure_secret(),
    salt="mc-session",
)


def _hash_password(password: str) -> str:
    """Return a bcrypt-style hash for the given password."""
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def set_password(password: str):
    """Hash and store the password. Used on first run or via CLI."""
    h = _hash_password(password)
    PASSWORD_FILE.write_text(h)
    PASSWORD_FILE.chmod(0o600)


def verify_password(password: str) -> bool:
    """Check a plaintext password against the stored hash."""
    if not PASSWORD_FILE.exists():
        return False
    import bcrypt
    stored = PASSWORD_FILE.read_text().strip()
    try:
        return bcrypt.checkpw(password.encode(), stored.encode())
    except Exception:
        return False


def has_password() -> bool:
    return PASSWORD_FILE.exists()


def create_session() -> str:
    """Return a signed session token."""
    payload = {
        "iat": int(time.time()),
        "sub": "admin",
    }
    return _serializer.dumps(payload)


def validate_session(token: str) -> bool:
    """Return True if the session token is valid and not expired."""
    try:
        _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def hash_for_display(password: str) -> str:
    """Return a one-shot display hash (for setup verification)."""
    return hashlib.sha256(password.encode()).hexdigest()[:12]
