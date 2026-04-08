"""
server.py — FastAPI UI server

Serves index.html and provides endpoints that proxy requests to the LangGraph
deployment via agent_client.py.

Run with:
    uv run uvicorn ui.server:app --reload
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from ui.agent_client import (
    LESSONS,
    create_client,
    create_student_sessions,
    create_thread,
    get_student_profile,
    stream_response,
    write_student_profile,
)

app = FastAPI()

UI_DIR = os.path.dirname(__file__)

# Cache clients per deployment URL
_clients: dict[str, object] = {}

# Active sessions per student namespace: {namespace: [{lesson_id, assistant_id, thread_id}]}
_sessions: dict[str, list[dict]] = {}


def get_client(deployment_url: str):
    if deployment_url not in _clients:
        _clients[deployment_url] = create_client(deployment_url)
    return _clients[deployment_url]


@app.get("/")
async def index():
    return FileResponse(f"{UI_DIR}/index.html")


@app.get("/lessons")
async def lessons():
    """Return the list of lessons and which are active."""
    return {"lessons": LESSONS}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    deployment_url: str
    assistant_id: str
    thread_id: str


@app.post("/chat")
async def chat(req: ChatRequest):
    """Stream a response from the agent."""
    try:
        client = get_client(req.deployment_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        stream_response(client, req.thread_id, req.assistant_id, req.message),
        media_type="text/plain",
    )


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class StudentStartRequest(BaseModel):
    deployment_url: str
    first_name: str
    last_name: str
    goals: str = ""
    preferences: str = ""


class StudentUpdateRequest(BaseModel):
    deployment_url: str
    namespace: str
    goals: str = ""
    preferences: str = ""


@app.post("/student/start")
async def student_start(req: StudentStartRequest):
    """Initialize a student session.

    Creates one assistant + thread per lesson and writes the student profile
    to the LangGraph Store. Returns sessions for the client to save locally.
    """
    namespace = f"{req.first_name.lower()}_{req.last_name.lower()}"

    try:
        client = get_client(req.deployment_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Create one assistant + thread per lesson
    sessions = await create_student_sessions(client, namespace, student_name=req.first_name)
    _sessions[namespace] = sessions

    # Write student profile to the Store
    profile = {
        "first_name": req.first_name,
        "last_name": req.last_name,
        "namespace": namespace,
        "goals": req.goals,
        "preferences": req.preferences,
    }
    await write_student_profile(client, namespace, profile)

    return {"namespace": namespace, "sessions": sessions}


@app.post("/student/update")
async def student_update(req: StudentUpdateRequest):
    """Update a student's goals and preferences in the Store."""
    try:
        client = get_client(req.deployment_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Read existing profile to preserve name fields
    existing = await get_student_profile(client, req.namespace) or {}
    existing.update({"goals": req.goals, "preferences": req.preferences})
    await write_student_profile(client, req.namespace, existing)

    return {"status": "updated"}
