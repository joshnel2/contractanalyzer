"""Strapped AI — FastAPI web application.

Serves the landing page, authentication, demo booking, and customer dashboard.

Run locally:
    uvicorn web.app:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import settings
from core.database import init_db
from core.models import AttorneyPreferences, Tone
from core.table_storage import StrappedTableStorage
from web.auth import UserStore, create_token, decode_token

logger = logging.getLogger("strapped.web")

app = FastAPI(title="Strapped AI", docs_url=None, redoc_url=None)


@app.on_event("startup")
def on_startup() -> None:
    init_db()

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ── Singletons ───────────────────────────────────────────────────────────────

_user_store = UserStore()
_storage = StrappedTableStorage()


def _get_user_store() -> UserStore:
    return _user_store


def _get_storage() -> StrappedTableStorage:
    return _storage


def _current_user(request: Request) -> dict | None:
    token = request.cookies.get("strapped_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return {"email": payload.get("email", ""), "name": payload.get("name", "")}


# ── Public Routes ────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> HTMLResponse:
    user = _current_user(request)
    return templates.TemplateResponse("landing.html", {"request": request, "user": user})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    user = _current_user(request)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    store = _get_user_store()
    user = store.authenticate(email, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password."},
        )
    token = create_token({"email": user["email"], "name": user["name"]})
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(
        "strapped_token", token, httponly=True, max_age=72 * 3600, samesite="lax"
    )
    return response


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request) -> HTMLResponse:
    user = _current_user(request)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("signup.html", {"request": request, "error": None})


@app.post("/signup", response_class=HTMLResponse)
async def signup_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(""),
    password: str = Form(...),
) -> Response:
    store = _get_user_store()
    created = store.create_user(email, password, name=name, company=company)
    if not created:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "An account with that email already exists."},
        )
    token = create_token({"email": email, "name": name})
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie(
        "strapped_token", token, httponly=True, max_age=72 * 3600, samesite="lax"
    )
    return response


@app.get("/logout")
async def logout() -> Response:
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("strapped_token")
    return response


@app.get("/book-demo", response_class=HTMLResponse)
async def book_demo_page(request: Request) -> HTMLResponse:
    user = _current_user(request)
    return templates.TemplateResponse(
        "book_demo.html", {"request": request, "user": user, "submitted": False}
    )


@app.post("/book-demo", response_class=HTMLResponse)
async def book_demo_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(""),
    message: str = Form(""),
) -> HTMLResponse:
    user = _current_user(request)
    try:
        store = _get_user_store()
        store.save_demo_request(name, email, company, message)
    except Exception:
        logger.exception("Failed to save demo request")
    return templates.TemplateResponse(
        "book_demo.html",
        {"request": request, "user": user, "submitted": True, "demo_name": name},
    )


# ── Protected Routes ─────────────────────────────────────────────────────────


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    user = _current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    storage = _get_storage()
    attorneys = storage.list_attorneys()

    selected = request.query_params.get("attorney", "")
    prefs = None
    audit_entries: list = []
    if selected:
        try:
            prefs = storage.get_preferences(selected)
            audit_entries = storage.get_audit_trail(selected, limit=15)
        except Exception:
            pass

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "attorneys": attorneys,
            "selected": selected,
            "prefs": prefs,
            "audit_entries": audit_entries,
        },
    )


@app.post("/dashboard/save-prefs", response_class=HTMLResponse)
async def save_preferences(request: Request) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    form = await request.form()
    email = str(form.get("attorney_email", ""))
    if not email:
        return RedirectResponse("/dashboard", status_code=302)

    storage = _get_storage()
    current = storage.get_preferences(email)

    updated = AttorneyPreferences(
        attorney_email=email,
        display_name=current.display_name,
        working_hours_start=str(form.get("working_hours_start", current.working_hours_start)),
        working_hours_end=str(form.get("working_hours_end", current.working_hours_end)),
        timezone=str(form.get("timezone", current.timezone)),
        buffer_before_minutes=int(form.get("buffer_before_minutes", current.buffer_before_minutes)),
        buffer_after_minutes=int(form.get("buffer_after_minutes", current.buffer_after_minutes)),
        preferred_duration_internal=int(form.get("preferred_duration_internal", current.preferred_duration_internal)),
        preferred_duration_client=int(form.get("preferred_duration_client", current.preferred_duration_client)),
        response_tone=Tone(str(form.get("response_tone", current.response_tone.value))),
        auto_approve_threshold=int(form.get("auto_approve_threshold", current.auto_approve_threshold)),
        default_virtual_platform=str(form.get("default_virtual_platform", current.default_virtual_platform)),
        custom_signature=str(form.get("custom_signature", current.custom_signature)),
        blackout_dates=current.blackout_dates,
        blocked_times=current.blocked_times,
        favorite_locations=current.favorite_locations,
        escalation_keywords=current.escalation_keywords,
        priority_order=current.priority_order,
        court_block_calendars=current.court_block_calendars,
    )
    storage.upsert_preferences(updated)
    return RedirectResponse(f"/dashboard?attorney={email}&saved=1", status_code=302)
