"""Hermes Mission Control — FastAPI app (read-only dashboard + kanban)."""
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth import verify_password, create_session, validate_session, set_password, has_password

from api.status import get_status
from api.cron import get_cron_jobs
from api.profiles import get_profiles
from api.skills import get_skills
from api.sessions import get_sessions
from api.logs import get_logs
from api.config import get_config
from api.kanban import get_kanban, create_card, update_card, delete_card

STATIC_DIR = Path(__file__).resolve().parent / "static"

def _is_authenticated(request: Request) -> bool:
    token = request.cookies.get("mc_session")
    if token and validate_session(token):
        return True
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and validate_session(auth[7:]):
        return True
    return False

def _auth_required(request: Request):
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

app = FastAPI(title="Hermes Mission Control")

# --- Auth ---
class LoginRequest(BaseModel):
    password: str

@app.post("/api/login")
async def login(body: LoginRequest, response: Response):
    if not has_password():
        set_password(body.password)
        token = create_session()
        response.set_cookie(
            key="mc_session", value=token,
            httponly=True, samesite="lax", max_age=86400,
        )
        return {"ok": True, "message": "Password set and logged in"}
    if verify_password(body.password):
        token = create_session()
        response.set_cookie(
            key="mc_session", value=token,
            httponly=True, samesite="lax", max_age=86400,
        )
        return {"ok": True, "message": "Logged in"}
    raise HTTPException(status_code=403, detail="Invalid password")

@app.get("/api/logout")
async def logout(response: Response):
    response.delete_cookie("mc_session")
    return {"ok": True}

@app.get("/api/check-auth")
async def check_auth(request: Request):
    return {"authenticated": _is_authenticated(request)}

# --- Read-only API ---
@app.get("/api/status")
async def status(request: Request):
    _auth_required(request)
    return get_status()

@app.get("/api/cron")
async def cron(request: Request):
    _auth_required(request)
    return get_cron_jobs()

@app.get("/api/profiles")
async def profiles(request: Request):
    _auth_required(request)
    return get_profiles()

@app.get("/api/skills")
async def skills(request: Request):
    _auth_required(request)
    return get_skills()

@app.get("/api/sessions")
async def sessions(request: Request, limit: int = 20):
    _auth_required(request)
    return get_sessions(min(limit, 50))

@app.get("/api/logs")
async def logs(request: Request, lines: int = 50):
    _auth_required(request)
    return get_logs(min(lines, 200))

@app.get("/api/config")
async def config(request: Request):
    _auth_required(request)
    return get_config()

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# --- Kanban API ---
class KanbanCreateRequest(BaseModel):
    title: str
    column: str = "todo"
    description: str = ""

class KanbanUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    column: str | None = None

@app.get("/api/kanban")
async def kanban_list(request: Request):
    _auth_required(request)
    return get_kanban()

@app.post("/api/kanban")
async def kanban_create(request: Request, body: KanbanCreateRequest):
    _auth_required(request)
    card = create_card(body.title, body.column, body.description)
    return {"ok": True, "card": card}

@app.patch("/api/kanban/{card_id}")
async def kanban_update(request: Request, card_id: str, body: KanbanUpdateRequest):
    _auth_required(request)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    card = update_card(card_id, updates)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True, "card": card}

@app.delete("/api/kanban/{card_id}")
async def kanban_delete(request: Request, card_id: str):
    _auth_required(request)
    if not delete_card(card_id):
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}

# --- SPA ---
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    idx = STATIC_DIR / "index.html"
    if not idx.exists():
        return JSONResponse({"error": "SPA not built"}, status_code=500)
    return FileResponse(str(idx))
