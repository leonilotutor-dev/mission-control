"""API: Kanban board — lightweight file-based task manager."""
import json, uuid, time, os
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))

# Try shared volume first, fall back to app-local storage if read-only
_PRIMARY_DIR = HERMES_HOME / "kanban"
_FALLBACK_DIR = Path(__file__).resolve().parent.parent / "data" / "kanban"

def _get_kanban_dir() -> Path:
    """Return writable kanban directory. Try shared volume, fall back to local."""
    try:
        _PRIMARY_DIR.mkdir(parents=True, exist_ok=True)
        test_file = _PRIMARY_DIR / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        return _PRIMARY_DIR
    except (OSError, PermissionError):
        _FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        return _FALLBACK_DIR

def _ensure_file():
    d = _get_kanban_dir()
    kanban_file = d / "kanban.json"
    if not kanban_file.exists():
        _write_to(d, {"columns": ["todo", "in-progress", "done"], "cards": []})

def _read() -> dict:
    d = _get_kanban_dir()
    kanban_file = d / "kanban.json"
    _ensure_file()
    try:
        return json.loads(kanban_file.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        data = {"columns": ["todo", "in-progress", "done"], "cards": []}
        _write_to(d, data)
        return data

def _write(data: dict):
    d = _get_kanban_dir()
    _write_to(d, data)

def _write_to(d: Path, data: dict):
    (d / "kanban.json").write_text(json.dumps(data, indent=2))

_COLUMN_LABELS = {
    "todo": "To Do",
    "in-progress": "In Progress",
    "done": "Done",
}
DEFAULT_COLUMNS = ["todo", "in-progress", "done"]

def get_kanban():
    data = _read()
    columns = data.get("columns", DEFAULT_COLUMNS)
    grouped = {col: [] for col in columns}
    for card in data.get("cards", []):
        col = card.get("column", "todo")
        if col in grouped:
            grouped[col].append(card)
        else:
            grouped.setdefault(col, []).append(card)
    return {
        "columns": [
            {"id": col, "label": _COLUMN_LABELS.get(col, col.capitalize())}
            for col in columns
        ],
        "cards": data.get("cards", []),
        "grouped": grouped,
    }

def create_card(title: str, column: str = "todo", description: str = "") -> dict:
    data = _read()
    ts = int(time.time())
    card = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "description": description,
        "column": column if column in data.get("columns", DEFAULT_COLUMNS) else "todo",
        "created_at": ts,
        "updated_at": ts,
        "order": len([c for c in data.get("cards", []) if c.get("column") == column]),
    }
    data.setdefault("cards", []).append(card)
    _write(data)
    return card

def update_card(card_id: str, updates: dict) -> dict | None:
    data = _read()
    for card in data.get("cards", []):
        if card["id"] == card_id:
            allowed = {"title", "description", "column"}
            for key in updates:
                if key in allowed:
                    card[key] = updates[key]
            card["updated_at"] = int(time.time())
            if "column" in updates:
                col_cards = [c for c in data["cards"] if c.get("column") == card["column"]]
                for i, c in enumerate(col_cards):
                    c["order"] = i
            _write(data)
            return card
    return None

def delete_card(card_id: str) -> bool:
    data = _read()
    before = len(data.get("cards", []))
    data["cards"] = [c for c in data.get("cards", []) if c["id"] != card_id]
    if len(data["cards"]) < before:
        _write(data)
        return True
    return False
