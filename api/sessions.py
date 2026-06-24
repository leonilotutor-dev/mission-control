"""API: recent sessions from state.db."""
import os, sqlite3
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))


def get_sessions(limit: int = 20):
    state_db = HERMES_HOME / "state.db"
    if not state_db.exists():
        return {"sessions": [], "total": 0}

    try:
        conn = sqlite3.connect(str(state_db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT id, title, started_at, updated_at, message_count,
                      source, platform
               FROM sessions
               ORDER BY started_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()

        sessions = []
        for r in rows:
            sessions.append({
                "id": r["id"],
                "title": r["title"] or "Untitled",
                "started_at": r["started_at"],
                "updated_at": r["updated_at"],
                "message_count": r["message_count"],
                "source": r["source"],
                "platform": r["platform"],
            })
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        return {"sessions": [], "total": 0, "error": str(e)}
