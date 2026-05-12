"""
m6/ui/app.py — Local UI server for a CLI-deployed dacli_tutor

This is a stripped-down variant of python/deep_tutor/ui/app.py for use against
a CLI-deployed agent. The CLI deployment exposes only the standard LangGraph
Agent Server endpoints (/threads, /runs, /store, etc.) — it does NOT host
deep_tutor's custom routes (/register, /login, /chat). So we run THIS UI
server locally on the student's machine; it serves the HTML and proxies the
chat to the CLI deployment via the LangGraph SDK.

The deployment URL is passed as a command-line argument:

    uv run python app.py https://tutor-xyz.us.langgraph.app

Auth flow
---------
/register and /login are stubbed to accept any input and return a canned
session. This keeps the index.html UI unchanged from deep_tutor and leaves
the auth scaffolding in place — wiring in a real auth provider later
(Supabase, Clerk, or a code-path handler) is a server-side change only,
with no UI rework.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from agent_client import create_client, stream_response

# The CLI's default assistant id is "agent" — see project_default_assistant_id
# memory note. The CLI's generated langgraph.json hardcodes the graph name to
# "agent", so the default assistant created for that graph has id "agent".
ASSISTANT_ID = "agent"

DEPLOYMENT_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:2024"

REPO_ROOT = Path(__file__).resolve().parents[3]
DEEP_TUTOR_HTML = REPO_ROOT / "python" / "deep_tutor" / "ui" / "index.html"

app = FastAPI()
client = create_client(DEPLOYMENT_URL)

# Maps email -> thread_id. A stable thread per "logged-in" email across page
# reloads (only while the server is running — restarts wipe the map).
threads_by_email: dict[str, str] = {}


async def _get_or_create_thread(email: str) -> str:
    if email not in threads_by_email:
        thread = await client.threads.create()
        threads_by_email[email] = thread["thread_id"]
    return threads_by_email[email]


def _make_session(thread_id: str, first_name: str = "Student", last_name: str = "") -> dict:
    """Return the shape the UI expects from /register and /login."""
    return {
        "sessions": [
            {"module_id": "module-1", "assistant_id": ASSISTANT_ID, "thread_id": thread_id},
        ],
        "profile": {"first_name": first_name, "last_name": last_name},
    }


@app.get("/")
async def index():
    return FileResponse(DEEP_TUTOR_HTML)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/modules")
async def modules():
    return {"modules": [{"id": "module-1", "label": "deployment architecture", "active": True}]}


# ==========================================================
# Faked auth — see module docstring for the why
# ==========================================================

class RegisterRequest(BaseModel):
    first_name: str = "Student"
    last_name: str = ""
    email: str = "student@example.com"
    goals: str = ""


@app.post("/register")
async def register(req: RegisterRequest):
    thread_id = await _get_or_create_thread(req.email)
    return _make_session(thread_id, first_name=req.first_name, last_name=req.last_name)


class LoginRequest(BaseModel):
    email: str


@app.post("/login")
async def login(req: LoginRequest):
    thread_id = await _get_or_create_thread(req.email)
    return _make_session(thread_id)


# ==========================================================
# Chat — real; talks to the CLI deployment via the SDK
# ==========================================================

class ChatRequest(BaseModel):
    message: str
    assistant_id: str
    thread_id: str


@app.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        stream_response(client, req.thread_id, req.assistant_id, req.message),
        media_type="text/plain",
    )


@app.get("/resources")
async def resources():
    """Debug tab — list assistants and threads."""
    assistants = await client.assistants.search(limit=100)
    threads = await client.threads.search(limit=100)
    return {"assistants": assistants, "threads": threads}


if __name__ == "__main__":
    import uvicorn
    print(f"m6 UI server starting; chatting with {DEPLOYMENT_URL}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
