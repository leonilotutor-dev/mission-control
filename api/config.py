"""API: sanitised config overview (no secrets)."""
import os, yaml
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))

SECRET_KEYS = {"api_key", "api_secret", "auth_token", "password", "secret", "token",
               "webhook_secret", "signing_secret", "client_secret", "private_key",
               "access_key", "bucket_key", "s3_key"}


def _redact(obj, path=""):
    """Recursively redact secret-looking values."""
    if isinstance(obj, dict):
        return {k: _redact(v, f"{path}.{k}" if path else k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(item, path) for item in obj]
    # Check if any secret key name is a substring of the path
    parts = path.lower().replace(".", "_").split("_")
    if any(sk in parts for sk in {"api", "secret", "key", "token", "password", "auth"}):
        if isinstance(obj, str) and len(obj) > 4:
            return "***REDACTED***"
    return obj


def get_config():
    cfg_file = HERMES_HOME / "config.yaml"
    if not cfg_file.exists():
        return {"config": {}, "error": "config.yaml not found"}

    try:
        raw = yaml.safe_load(cfg_file.read_text())
        redacted = _redact(raw)
        return {"config": redacted}
    except Exception as e:
        return {"config": {}, "error": str(e)}
