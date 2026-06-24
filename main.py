"""Hermes Mission Control — FastAPI app (read-only dashboard)."""
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

STATIC_DIR = Path(__file__).resolve().parent / "static"
PYTHON = "/tmp/.venv/bin/python3"


def _is_authenticated(request: Request) -> bool:
    token = request.cookies.get("mc_session")
    if token and validate_session(token):
        return True
    # Also check Authorization header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and validate_session(auth[7:]):
        return True
    return False


def _auth_required(request: Request):
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")


app = FastAPI(title="Hermes Mission Control")


# Login endpoint
class LoginRequest(BaseModel):
    password: str


@app.post("/api/login")
async def login(body: LoginRequest, response: Response):
    if not has_password():
        # First run — set password
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


# Read-only API endpoints
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


# Serve SPA — static files with fallback to index.html
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve index.html for all non-API routes (SPA fallback)."""
    # Don't intercept API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    idx = STATIC_DIR / "index.html"
    if not idx.exists():
        return JSONResponse({"error": "SPA not built"}, status_code=500)
    return FileResponse(str(idx))
