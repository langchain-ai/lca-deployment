"""
app.py — FastAPI custom routes app (m5/l5 — with Supabase auth)

Wires the deep_tutor UI to Supabase for real authentication:
  - /register signs up a new user with Supabase, stores their profile, returns JWT
  - /login exchanges email + password for a Supabase JWT
  - /chat and /resources accept the JWT (Authorization: Bearer <jwt>) and
    forward it to the LangGraph deployment so @auth.authenticate validates
    every call

Registered as a custom route in langgraph.json via the http.app field.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from ui.agent_client import MODULES, create_client, create_student_sessions, stream_response
from ui.deployment import get_deployment_url

app = FastAPI()

UI_DIR = Path(__file__).parent

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]


def email_to_namespace(email: str) -> str:
    """Same conversion auth.py uses for the @auth.on.store namespace check."""
    return email.replace(".", "_")


def extract_jwt(authorization: str | None) -> str:
    """Pull the bearer token out of an Authorization header, or 401."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return token


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/")
async def index():
    return FileResponse(UI_DIR / "index.html")


@app.get("/modules")
async def modules():
    return {"modules": MODULES}


# ==========================================================
# Register — new students
# ==========================================================

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    goals: str = ""


@app.post("/register")
async def register(request: Request, req: RegisterRequest):
    """Sign the user up with Supabase, then store their profile + sessions."""
    # 1. Sign up with Supabase, receive a JWT.
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            json={"email": req.email, "password": req.password},
            headers={"apiKey": SUPABASE_PUBLISHABLE_KEY, "Content-Type": "application/json"},
        )
        if not r.is_success:
            raise HTTPException(status_code=r.status_code, detail=r.json())
        jwt = r.json()["access_token"]

    # 2. Use that JWT to call the deployment — every SDK call now passes
    #    through @auth.authenticate on the way in.
    client = create_client(get_deployment_url(request), jwt=jwt)
    namespace = email_to_namespace(req.email)

    await client.store.put_item(
        (namespace,),
        key="profile",
        value={
            "first_name": req.first_name,
            "last_name": req.last_name,
            "email": req.email,
            "goals": req.goals,
        },
    )

    sessions = await create_student_sessions(
        client,
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        namespace=namespace,
    )

    await client.store.put_item(
        (namespace,),
        key="sessions",
        value={"sessions": sessions},
    )

    return {
        "jwt": jwt,
        "sessions": sessions,
        "profile": {"first_name": req.first_name, "last_name": req.last_name},
    }


# ==========================================================
# Login — returning students
# ==========================================================

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/login")
async def login(request: Request, req: LoginRequest):
    """Exchange email + password for a JWT, then return profile + sessions."""
    # 1. Ask Supabase for a JWT.
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": req.email, "password": req.password},
            headers={"apiKey": SUPABASE_PUBLISHABLE_KEY, "Content-Type": "application/json"},
        )
        if not r.is_success:
            raise HTTPException(status_code=r.status_code, detail=r.json())
        jwt = r.json()["access_token"]

    # 2. Read the existing profile + sessions using the JWT.
    client = create_client(get_deployment_url(request), jwt=jwt)
    namespace = email_to_namespace(req.email)

    profile_item = await client.store.get_item((namespace,), key="profile")
    if profile_item is None:
        raise HTTPException(status_code=404, detail="user not found")

    sessions_item = await client.store.get_item((namespace,), key="sessions")
    if sessions_item is None:
        raise HTTPException(status_code=404, detail="sessions not found")

    return {
        "jwt": jwt,
        "sessions": sessions_item["value"]["sessions"],
        "profile": profile_item["value"],
    }


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
):
    """Stream a response from the agent, authenticated as the calling user."""
    jwt = extract_jwt(authorization)
    client = create_client(get_deployment_url(request), jwt=jwt)
    return StreamingResponse(
        stream_response(client, req.thread_id, req.assistant_id, req.message),
        media_type="text/plain",
    )


# ==========================================================
# Resources — threads and assistants for the calling user
# ==========================================================

@app.get("/resources")
async def resources(
    request: Request,
    authorization: str | None = Header(default=None),
):
    """Return threads and assistants visible to the calling user."""
    jwt = extract_jwt(authorization)
    client = create_client(get_deployment_url(request), jwt=jwt)
    assistants = await client.assistants.search(limit=100)
    threads = await client.threads.search(limit=100)
    return {"assistants": assistants, "threads": threads}
