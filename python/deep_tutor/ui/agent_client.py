"""
agent_client.py — LangGraph client

Connects to a deployed LangGraph agent, creates threads, and streams responses.

Documentation:
  LangGraph SDK (Python): https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from langgraph_sdk import get_client
from langgraph_sdk.client import LangGraphClient

load_dotenv()

MODULES = [
    {"id": "module-1", "label": "deployment architecture", "active": True},
    {"id": "module-2", "label": "using your deployment", "active": True},
    {"id": "module-3", "label": "module 3", "active": False},
]


def create_client(deployment_url: str) -> LangGraphClient:
    """Create a LangGraph client connected to the deployment."""
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    return get_client(url=deployment_url, api_key=api_key)


async def stream_response(
    client: LangGraphClient,
    thread_id: str,
    assistant_id: str,
    message: str,
) -> AsyncGenerator[str, None]:
    """Send a message and stream the agent's response."""
    async for event in client.runs.stream(
        thread_id,
        assistant_id,
        input={"messages": [{"role": "user", "content": message}]},
        stream_mode="messages-tuple",
    ):
        if event.event != "messages":
            continue
        message_chunk, _metadata = event.data
        content = message_chunk.get("content", "")
        if isinstance(content, list):
            content = "".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        if content:
            yield content


async def create_student_sessions(
    client: LangGraphClient,
    first_name: str = "Student",
    last_name: str = "",
    email: str = "",
    namespace: str = "",
) -> list[dict]:
    """Create one assistant + thread per module for a student."""
    student_name = f"{first_name} {last_name}".strip()
    sessions = []
    for module in MODULES:
        assistant = await client.assistants.create(
            graph_id="tutor",
            name=f"{student_name} — {module['id']}",
            context={
                "module_id": module["id"],
                "store_namespace": namespace,
            },
        )
        thread = await client.threads.create()
        sessions.append({
            "module_id": module["id"],
            "assistant_id": assistant["assistant_id"],
            "thread_id": thread["thread_id"],
        })
    return sessions
