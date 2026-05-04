"""
app.py — FastAPI custom routes app

Serves index.html and proxies chat requests to the agent via agent_client.py.
Registered as a custom route in langgraph.json via the http.app field.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
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
# Start — create sessions for a student
# ==========================================================

class StartRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    goals: str = ""


@app.post("/start")
async def start(request: Request, req: StartRequest):
    """Create one assistant + thread per module and return sessions."""
    client = get_cached_client(get_deployment_url(request))
    sessions = await create_student_sessions(
        client,
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        goals=req.goals,
    )
    return {"sessions": sessions}


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
