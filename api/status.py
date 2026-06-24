"""API: status overview — gateway, profiles, uptime, hermes version."""
import os, json, subprocess, time
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))
_VERSION_CACHE_FILE = HERMES_HOME / "mission-control" / ".version_cache.json"
_VERSION_CACHE_TTL = 21600  # 6 hours


def _get_hermes_version() -> dict:
    """Return installed Hermes version + up-to-date status."""
    now = time.time()

    # Check cache first
    if _VERSION_CACHE_FILE.exists():
        try:
            cached = json.loads(_VERSION_CACHE_FILE.read_text())
            if now - cached.get("cached_at", 0) < _VERSION_CACHE_TTL:
                return {k: cached[k] for k in ("version", "date", "up_to_date", "latest_tag") if k in cached}
        except (json.JSONDecodeError, KeyError):
            pass

    result = {
        "version": None,
        "date": None,
        "up_to_date": None,
        "latest_tag": None,
    }

    # Get installed version -- read from .hermes-version.json (written by hermes side)
    version_file = HERMES_HOME / ".hermes-version.json"
    if version_file.exists():
        try:
            vdata = json.loads(version_file.read_text())
            result["version"] = vdata.get("version")
            result["date"] = vdata.get("date")
        except Exception:
            pass
    else:
        # Fallback: try running hermes --version (only works inside hermes container)
        try:
            ver_out = subprocess.run(
                ["/opt/hermes/.venv/bin/hermes", "--version"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            import re
            m = re.search(r'v?(\d+\.\d+\.\d+)\s+\(([^)]+)\)', ver_out)
            if m:
                result["version"] = m.group(1)
                result["date"] = m.group(2)
        except Exception:
            pass

    # Check latest release from GitHub
    latest_tag = None
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.github.com/repos/NousResearch/hermes-agent/releases/latest",
            headers={"User-Agent": "hermes-mission-control/1.0", "Accept": "application/vnd.github.v3+json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        release = json.loads(resp.read())
        latest_tag = release.get("tag_name", "")
    except Exception:
        pass

    result["latest_tag"] = latest_tag

    if result["date"] and latest_tag:
        # Normalize and compare dates: "2026.6.5" -> "20260605", "v2026.6.19" -> "20260619"
        def _pad_date(d: str) -> str:
            parts = d.lstrip("v").split(".")
            return "".join(p.zfill(2) if len(parts) > 1 else p.zfill(8) for p in parts)
        installed_padded = _pad_date(result["date"])
        latest_padded = _pad_date(latest_tag)
        result["up_to_date"] = installed_padded >= latest_padded
    else:
        result["up_to_date"] = None

    # Write cache
    try:
        cache_entry = {
            "cached_at": now,
            "version": result["version"],
            "date": result["date"],
            "up_to_date": result["up_to_date"],
            "latest_tag": result["latest_tag"],
        }
        _VERSION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _VERSION_CACHE_FILE.write_text(json.dumps(cache_entry))
    except Exception:
        pass

    return result


def get_status():
    data = {
        "gateway": "unknown",
        "profiles": 0,
        "cron_jobs": 0,
        "skills": 0,
        "sessions_24h": 0,
        "uptime_seconds": None,
        "hermes": _get_hermes_version(),
    }

    # Gateway state
    gs = HERMES_HOME / "gateway_state.json"
    if gs.exists():
        try:
            raw = json.loads(gs.read_text())
            data["gateway"] = raw.get("gateway_state", raw.get("status", raw.get("state", "unknown")))
            data["gateway_running"] = data["gateway"] == "running"
            data["gateway_platforms"] = list(raw.get("platforms", {}).keys())
            data["gateway_active_agents"] = raw.get("active_agents", 0)
        except Exception:
            pass

    # Profiles
    profiles_dir = HERMES_HOME / "profiles"
    if profiles_dir.is_dir():
        data["profiles"] = len([p for p in profiles_dir.iterdir() if p.is_dir()])

    # Cron
    cron_file = HERMES_HOME / "cron" / "jobs.json"
    if cron_file.exists():
        try:
            jobs = json.loads(cron_file.read_text())
            data["cron_jobs"] = len(jobs.get("jobs", []))
        except Exception:
            pass

    # Skills
    skills_dir = HERMES_HOME / "skills"
    if skills_dir.is_dir():
        skills_count = 0
        for child in skills_dir.iterdir():
            if child.is_dir():
                skills_count += 1
            elif child.suffix == ".md":
                skills_count += 1
        data["skills"] = skills_count

    # Sessions in last 24h
    state_db = HERMES_HOME / "state.db"
    if state_db.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(state_db))
            row = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE started_at > datetime('now', '-1 day')"
            ).fetchone()
            if row:
                data["sessions_24h"] = row[0]
            conn.close()
        except Exception:
            pass

    return data
