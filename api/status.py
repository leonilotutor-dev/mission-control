"""API: status overview — gateway, profiles, uptime."""
import os, json, subprocess
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))

def get_status():
    data = {
        "gateway": "unknown",
        "profiles": 0,
        "cron_jobs": 0,
        "skills": 0,
        "sessions_24h": 0,
        "uptime_seconds": None,
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
