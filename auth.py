"""Hermes Mission Control — auth module.
Single-user shared-password auth with signed session cookies.

Password comes from MC_PASSWORD env var first, then falls back to
PASSWORD_FILE on the HERMES_HOME volume. This allows read-only volume
mounts (env var mode, no writes needed) or writable mounts (file mode).
"""

import hashlib
import os
import secrets
import time
from pathlib import Path

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

AUTH_DIR = Path(os.environ.get("HERMES_HOME", str(Path(__file__).resolve().parent)))
PASSWORD_FILE = (AUTH_DIR / "mission-control" / ".mc-password")
SECRET_FILE = (AUTH_DIR / "mission-control" / ".mc-secret")

# Session lifetime: 24 hours
SESSION_MAX_AGE = 86400

# Password from env var (takes priority over file)
_ENV_PASSWORD = os.environ.get("MC_PASSWORD", "")


def _ensure_secret() -> str:
    """Return a stable signing secret, creating one if absent.
    When an MC_PASSWORD env var is set, derive the secret from it
    so it's stable across restarts without needing to write to disk.
    """
    if _ENV_PASSWORD:
        return hashlib.sha256(_ENV_PASSWORD.encode()).hexdigest()
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text().strip()
    secret = secrets.token_hex(32)
    try:
        SECRET_FILE.write_text(secret)
        SECRET_FILE.chmod(0o600)
    except OSError:
        # Read-only volume — use ephemeral secret (sessions invalidated on restart)
        pass
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
    """Hash and store the password."""
    h = _hash_password(password)
    try:
        PASSWORD_FILE.write_text(h)
        PASSWORD_FILE.chmod(0o600)
    except OSError:
        pass  # Read-only volume — we'll use env var instead


def verify_password(password: str) -> bool:
    """Check a plaintext password against env var or stored hash."""
    # Check env var first (read-only volume mode)
    if _ENV_PASSWORD:
        return password == _ENV_PASSWORD
    # Fall back to file
    if not PASSWORD_FILE.exists():
        return False
    import bcrypt
    stored = PASSWORD_FILE.read_text().strip()
    try:
        return bcrypt.checkpw(password.encode(), stored.encode())
    except Exception:
        return False


def has_password() -> bool:
    """Return True if a password is configured (env var or file)."""
    return bool(_ENV_PASSWORD) or PASSWORD_FILE.exists()


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
