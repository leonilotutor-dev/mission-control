"""API: Kanban board — lightweight file-based task manager."""
import json, uuid, time, os
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))
KANBAN_DIR = HERMES_HOME / "kanban"
KANBAN_FILE = KANBAN_DIR / "kanban.json"

DEFAULT_COLUMNS = ["todo", "in-progress", "done"]

_COLUMN_LABELS = {
    "todo": "To Do",
    "in-progress": "In Progress",
    "done": "Done",
}


def _ensure_file():
    KANBAN_DIR.mkdir(parents=True, exist_ok=True)
    if not KANBAN_FILE.exists():
        _write({"columns": DEFAULT_COLUMNS, "cards": []})


def _read() -> dict:
    _ensure_file()
    try:
        return json.loads(KANBAN_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        data = {"columns": DEFAULT_COLUMNS, "cards": []}
        _write(data)
        return data


def _write(data: dict):
    KANBAN_FILE.write_text(json.dumps(data, indent=2))


def get_kanban():
    """Return the full kanban board with cards grouped by column."""
    data = _read()
    grouped = {col: [] for col in data.get("columns", DEFAULT_COLUMNS)}
    for card in data.get("cards", []):
        col = card.get("column", "todo")
        if col in grouped:
            grouped[col].append(card)
        else:
            grouped.setdefault(col, []).append(card)
    return {
        "columns": [
            {"id": col, "label": _COLUMN_LABELS.get(col, col.capitalize())}
            for col in data.get("columns", DEFAULT_COLUMNS)
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
