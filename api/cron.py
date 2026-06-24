"""API: cron jobs listing."""
import json, os
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))


def get_cron_jobs():
    cron_file = HERMES_HOME / "cron" / "jobs.json"
    if not cron_file.exists():
        return {"jobs": [], "total": 0}
    try:
        data = json.loads(cron_file.read_text())
        jobs = data.get("jobs", [])
        for j in jobs:
            # Clean up large prompt fields for display
            prompt = j.get("prompt", "")
            if len(prompt) > 200:
                j["prompt_preview"] = prompt[:200] + "..."
            else:
                j["prompt_preview"] = prompt
            # Convert UTC times to nice format
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        return {"jobs": [], "total": 0, "error": str(e)}
