"""
app.py — FastAPI custom routes app

Serves index.html and proxies chat requests to the agent via agent_client.py.
Registered as a custom route in langgraph.json via the http.app field.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from ui.agent_client import MODULES, create_client, create_student_sessions, stream_response
from ui.deployment import get_deployment_url

app = FastAPI()

UI_DIR = Path(__file__).parent

_client_cache: dict[str, object] = {}


def get_cached_client(deployment_url: str):
    if deployment_url not in _client_cache:
        _client_cache[deployment_url] = create_client(deployment_url)
    return _client_cache[deployment_url]


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
# Auth helpers
# ==========================================================

def email_to_namespace(email: str) -> str:
    # TODO: full password auth handled in m_auth module — namespace only for now
    return email.replace(".", "_")


# ==========================================================
# Register — new students
# ==========================================================

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    goals: str = ""


@app.post("/register")
async def register(request: Request, req: RegisterRequest):
    """Create profile + sessions for a new student and persist to Store."""
    client = get_cached_client(get_deployment_url(request))
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

    return {"sessions": sessions, "profile": {"first_name": req.first_name, "last_name": req.last_name}}


# ==========================================================
# Login — returning students
# ==========================================================

class LoginRequest(BaseModel):
    email: str
    # TODO: password field — authentication handled in m_auth module


@app.post("/login")
async def login(request: Request, req: LoginRequest):
    """Look up a returning student's profile and sessions from the Store."""
    client = get_cached_client(get_deployment_url(request))
    namespace = email_to_namespace(req.email)

    profile_item = await client.store.get_item((namespace,), key="profile")
    if profile_item is None:
        raise HTTPException(status_code=404, detail="user not found")

    sessions_item = await client.store.get_item((namespace,), key="sessions")
    if sessions_item is None:
        raise HTTPException(status_code=404, detail="sessions not found")

    return {"sessions": sessions_item["value"]["sessions"], "profile": profile_item["value"]}


# ==========================================================
# Chat
# ==========================================================

class ChatRequest(BaseModel):
    message: str
    assistant_id: str
    thread_id: str


@app.post("/chat")
async def chat(request: Request, req: ChatRequest):
    """Stream a response from the agent."""
    client = get_cached_client(get_deployment_url(request))
    return StreamingResponse(
        stream_response(client, req.thread_id, req.assistant_id, req.message),
        media_type="text/plain",
    )


# ==========================================================
# Resources — threads and assistants
# ==========================================================

@app.get("/resources")
async def resources(request: Request):
    """Return all threads and assistants."""
    client = get_cached_client(get_deployment_url(request))
    assistants = await client.assistants.search(limit=100)
    threads = await client.threads.search(limit=100)
    return {"assistants": assistants, "threads": threads}
