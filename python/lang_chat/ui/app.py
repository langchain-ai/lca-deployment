"""
app.py — FastAPI custom routes app

Serves index.html and provides endpoints that proxy requests to the agent
via agent_client.py.

Registered as a custom route in langgraph.json via the http.app field.
The deployment URL is derived from the incoming request — see deployment.py.

Run locally with:
    uv run langgraph dev
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt
import httpx
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from ui.agent_client import (
    LESSONS,
    create_client,
    create_student_sessions,
    get_sessions,
    get_student_profile,
    lookup_namespace,
    stream_response,
    write_identity_map,
    write_sessions,
    write_student_profile,
)
from ui.deployment import get_deployment_url

app = FastAPI()

UI_DIR = os.path.dirname(__file__)

_clients: dict[str, object] = {}
_admin_seeded = False


def get_client(deployment_url: str, token: str | None = None):
    if token:
        return create_client(deployment_url, token=token)
    if deployment_url not in _clients:
        _clients[deployment_url] = create_client(deployment_url)
    return _clients[deployment_url]


def service_token() -> str:
    """Short-lived admin JWT for internal app.py → Store calls (register, login, seed).
    Always uses JWT_SECRET — consistent with auth_local.py and auth_supabase.py."""
    secret = os.environ.get("JWT_SECRET")
    return jwt.encode(
        {"sub": "__service__", "role": "admin", "exp": int(time.time()) + 300},
        secret,
        algorithm="HS256",
    )


# ==========================================================
# JWT validation
# ==========================================================

def _decode_token(authorization: str | None) -> dict:
    """Decode and validate the JWT. Returns the payload dict."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    if _using_supabase():
        # Admin tokens are signed with JWT_SECRET — verify fully.
        local_secret = os.environ.get("JWT_SECRET")
        if local_secret:
            try:
                return jwt.decode(token, local_secret, algorithms=["HS256"], options={"verify_aud": False})
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token expired")
            except jwt.InvalidTokenError:
                pass
        # Supabase user tokens — skip local signature verification (auth_supabase.py
        # calls the Supabase API on every agent-facing request, which is the real check).
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="Token expired")
        return payload
    secret = os.environ["JWT_SECRET"]
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], options={})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency — returns the identity (sub) from the JWT."""
    return _decode_token(authorization)["sub"]


async def get_current_namespace(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency — returns the Store namespace (first_last) from the JWT."""
    payload = _decode_token(authorization)
    # Supabase tokens carry namespace in user_metadata; local/admin tokens have it top-level
    if _using_supabase():
        return (payload.get("user_metadata") or {}).get("namespace") or payload.get("namespace") or payload["sub"]
    return payload.get("namespace") or payload["sub"]


# ==========================================================
# Admin seeding — runs once on first auth request
# ==========================================================

async def seed_admin_once(client) -> None:
    """Seed the admin account from ADMIN_NAME/ADMIN_PASSWORD in .env if not yet present."""
    global _admin_seeded
    if _admin_seeded:
        return
    _admin_seeded = True
    name = os.environ.get("ADMIN_NAME", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not name or not password:
        return
    existing = await get_student_profile(client, name) or {}
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        await write_student_profile(client, name, {
            **existing,
            "username": name,
            "namespace": name,
            "password_hash": hashed,
            "role": "admin",
        })
        await write_identity_map(client, name, name)
    except Exception:
        _admin_seeded = False  # allow retry on next request


# ==========================================================
# Static
# ==========================================================

@app.get("/healthz")
async def healthz(request: Request):
    """Deployment probe — confirms code version and that the service token round-trip works."""
    import importlib.metadata, time as _time
    result: dict = {
        "jwt_secret_set": bool(os.environ.get("JWT_SECRET")),
        "supabase_jwt_secret_set": bool(os.environ.get("SUPABASE_JWT_SECRET")),
        "supabase_oauth": os.environ.get("SUPABASE_OAUTH"),
    }
    try:
        client = get_client(get_deployment_url(request), token=service_token())
        await client.store.get_item(("__healthz__",), key="probe")
        result["store_access"] = "ok"
    except Exception as e:
        result["store_access"] = f"FAILED: {type(e).__name__}: {e}"
    return result


@app.get("/")
async def index():
    return FileResponse(f"{UI_DIR}/index.html")


@app.get("/lessons")
async def lessons():
    return {"lessons": LESSONS}


@app.get("/auth/mode")
async def auth_mode():
    return {"mode": "supabase" if _using_supabase() else "local"}


# ==========================================================
# Auth
# ==========================================================

def _using_supabase() -> bool:
    return os.environ.get("SUPABASE_OAUTH", "false").lower() == "true"


def _supabase_headers() -> dict:
    return {"apikey": os.environ["SUPABASE_ANON_KEY"], "Content-Type": "application/json"}


async def _supabase_register(email: str, password: str, namespace: str) -> None:
    """Register a new user via Supabase Auth REST API. Stores namespace in user_metadata."""
    url = f"{os.environ['SUPABASE_URL']}/auth/v1/signup"
    async with httpx.AsyncClient() as http:
        res = await http.post(
            url,
            json={"email": email, "password": password, "data": {"namespace": namespace}},
            headers=_supabase_headers(),
        )
    if res.status_code == 422:
        raise HTTPException(status_code=409, detail="username_taken")
    if res.status_code not in (200, 201):
        raise HTTPException(status_code=400, detail=res.json().get("msg", "registration failed"))


async def _supabase_login(email: str, password: str) -> str:
    """Exchange email/password for a Supabase JWT."""
    url = f"{os.environ['SUPABASE_URL']}/auth/v1/token?grant_type=password"
    async with httpx.AsyncClient() as http:
        res = await http.post(url, json={"email": email, "password": password}, headers=_supabase_headers())
    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return res.json()["access_token"]


class RegisterRequest(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    goals: str = ""
    preferences: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/register", status_code=201)
async def auth_register(request: Request, req: RegisterRequest):
    """Register a new student. Uses Supabase if configured, otherwise local bcrypt."""
    client = get_client(get_deployment_url(request), token=service_token())
    await seed_admin_once(client)

    namespace = f"{req.first_name.lower()}_{req.last_name.lower()}"
    identity = req.username  # email (Supabase) or username (local)

    if _using_supabase():
        await _supabase_register(identity, req.password, namespace)
    else:
        if await get_student_profile(client, namespace) is not None:
            raise HTTPException(status_code=409, detail="username_taken")
        hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
        profile_extra = {"password_hash": hashed}

    profile = {
        "username": identity,
        "namespace": namespace,
        "first_name": req.first_name,
        "last_name": req.last_name,
        "goals": req.goals,
        "preferences": req.preferences,
        "role": "user",
        **(profile_extra if not _using_supabase() else {}),
    }
    await write_student_profile(client, namespace, profile)
    await write_identity_map(client, identity, namespace)
    return {"message": "registered"}


@app.post("/auth/login")
async def auth_login(request: Request, req: LoginRequest):
    """Verify credentials, create sessions, return JWT + sessions.
    Uses Supabase if configured, otherwise local bcrypt."""
    svc_client = get_client(get_deployment_url(request), token=service_token())
    await seed_admin_once(svc_client)

    is_admin = req.username == os.environ.get("ADMIN_NAME", "")
    use_supabase = _using_supabase() and not is_admin

    if use_supabase:
        token = await _supabase_login(req.username, req.password)
        payload = jwt.decode(token, options={"verify_signature": False})
        identity = payload.get("email") or payload["sub"]
        # namespace is in user_metadata (stored at registration) — no re-issue needed
    else:
        identity = req.username

    # Look up namespace (first_last) from identity map
    namespace = await lookup_namespace(svc_client, identity)

    if use_supabase:
        if namespace is None:
            namespace = (payload.get("user_metadata") or {}).get("namespace") or identity
        profile = await get_student_profile(svc_client, namespace) or {}
        # token is the raw Supabase JWT — no re-issue needed, namespace is in user_metadata
    else:
        if namespace is None:
            namespace = identity  # fallback for pre-mapping accounts
        profile = await get_student_profile(svc_client, namespace) or {}
        if not profile or not bcrypt.checkpw(
            req.password.encode(), profile.get("password_hash", "").encode()
        ):
            raise HTTPException(status_code=401, detail="invalid_credentials")
        token = jwt.encode(
            {"sub": identity, "namespace": namespace, "role": profile.get("role", "user"), "exp": int(time.time()) + 86400},
            os.environ["JWT_SECRET"],  # admin tokens always use JWT_SECRET so auth_supabase.py can verify them
            algorithm="HS256",
        )

    # Reuse existing sessions if available; create and persist on first login
    user_client = get_client(get_deployment_url(request), token=token)
    sessions = await get_sessions(svc_client, namespace)
    if not sessions:
        sessions = await create_student_sessions(
            user_client, namespace, student_name=profile.get("first_name", identity)
        )
        await write_sessions(svc_client, namespace, sessions)
    return {
        "token": token,
        "namespace": namespace,
        "sessions": sessions,
        "profile": {k: v for k, v in profile.items() if k != "password_hash"},
    }


@app.get("/auth/validate")
async def auth_validate(username: str = Depends(get_current_user)):
    """Validate the current JWT. Returns 200 if valid, 401 if expired or invalid."""
    return {"valid": True}


@app.post("/auth/logout")
async def auth_logout():
    """Logout is client-side — this endpoint just confirms the call."""
    return {"message": "logged out"}


# ==========================================================
# Chat
# ==========================================================

class ChatRequest(BaseModel):
    message: str
    assistant_id: str
    thread_id: str


@app.post("/chat")
async def chat(
    request: Request,
    req: ChatRequest,
    authorization: str | None = Header(default=None),
    username: str = Depends(get_current_user),
):
    """Stream a response from the agent. Forwards JWT to agent when auth.py is enabled."""
    try:
        token = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
        client = get_client(get_deployment_url(request), token=token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        stream_response(client, req.thread_id, req.assistant_id, req.message),
        media_type="text/plain",
    )


# ==========================================================
# Resources — all threads + assistants (no filtering in step 1)
# ==========================================================

@app.get("/resources")
async def resources(
    request: Request,
    authorization: str | None = Header(default=None),
    username: str = Depends(get_current_user),
):
    """Return threads and assistants. With auth.py enabled, filtered to owner by the agent."""
    token = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
    client = get_client(get_deployment_url(request), token=token)
    assistants = await client.assistants.search(limit=100)
    threads = await client.threads.search(limit=100)
    return {"assistants": assistants, "threads": threads}


@app.get("/store")
async def store_items(
    request: Request,
    authorization: str | None = Header(default=None),
    namespace: str = Depends(get_current_namespace),
):
    """Return store items. Admins get all namespaces; users get their own namespace only."""
    payload = _decode_token(authorization)
    role = payload.get("role", "user")
    token = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
    client = get_client(get_deployment_url(request), token=token)
    prefix = () if role == "admin" else (namespace,)
    result = await client.store.search_items(prefix, limit=200)
    items = result["items"] if isinstance(result, dict) else result
    return {"items": [
        {
            "namespace": list(item["namespace"]),
            "key": item["key"],
            "value": item["value"],
            "updated_at": item.get("updated_at"),
        }
        for item in items
    ]}


# ==========================================================
# Student
# ==========================================================

class StudentUpdateRequest(BaseModel):
    goals: str = ""
    preferences: str = ""


@app.post("/student/update")
async def student_update(
    request: Request,
    req: StudentUpdateRequest,
    authorization: str | None = Header(default=None),
    namespace: str = Depends(get_current_namespace),
):
    """Update goals and preferences in the Store. Requires JWT. Namespace comes from token."""
    try:
        token = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
        client = get_client(get_deployment_url(request), token=token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    existing = await get_student_profile(client, namespace) or {}
    existing.update({"goals": req.goals, "preferences": req.preferences})
    await write_student_profile(client, namespace, existing)
    return {"status": "updated"}
