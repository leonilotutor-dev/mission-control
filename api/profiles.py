"""API: profiles listing."""
import os, json
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))


def get_profiles():
    profiles_dir = HERMES_HOME / "profiles"
    if not profiles_dir.is_dir():
        return {"profiles": [], "total": 0}

    result = []
    for pdir in sorted(profiles_dir.iterdir()):
        if not pdir.is_dir():
            continue
        name = pdir.name
        info = {"name": name, "has_gateway": False, "gateway_status": None}

        # Check gateway state
        gs = pdir / "gateway_state.json"
        if gs.exists():
            try:
                raw = json.loads(gs.read_text())
                info["gateway_status"] = raw.get("status", raw.get("state", "unknown"))
                info["has_gateway"] = True
            except Exception:
                pass

        # Check gateway PID
        pid_file = pdir / "gateway.pid"
        if pid_file.exists():
            pid = pid_file.read_text().strip()
            try:
                info["gateway_running"] = os.path.isdir(f"/proc/{pid}")
            except Exception:
                pass

        # Config model info
        cfg = pdir / "config.yaml"
        if cfg.exists():
            import yaml
            try:
                config = yaml.safe_load(cfg.read_text())
                model = config.get("model", {})
                info["model"] = model.get("default", "?")
                info["provider"] = model.get("provider", "?")
            except Exception:
                pass

        result.append(info)

    return {"profiles": result, "total": len(result)}
