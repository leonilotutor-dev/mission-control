"""API: log tail from gateway.log."""
import os
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))


def get_logs(lines: int = 50):
    log_file = HERMES_HOME / "logs" / "gateway.log"
    agent_log = HERMES_HOME / "logs" / "agent.log"
    error_log = HERMES_HOME / "logs" / "errors.log"

    def tail(filepath: Path, n: int):
        if not filepath.exists():
            return []
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
            lines_list = text.rstrip("\n").split("\n")
            return lines_list[-n:]
        except Exception:
            return [f"[error reading {filepath.name}]"]

    return {
        "gateway": tail(log_file, lines),
        "agent": tail(agent_log, lines),
        "errors": tail(error_log, lines),
    }
