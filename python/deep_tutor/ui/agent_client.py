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
    {"id": "module-2", "label": "module 2", "active": False},
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
    printed: dict[str, int] = {}
    async for event in client.runs.stream(
        thread_id,
        assistant_id,
        input={"messages": [{"role": "user", "content": message}]},
        stream_mode="messages",
    ):
        if not isinstance(event.data, list):
            continue
        for item in event.data:
            msg = item[0] if isinstance(item, (list, tuple)) else item
            if not isinstance(msg, dict):
                continue
            if msg.get("type") in ("AIMessageChunk", "AIMessage", "ai"):
                msg_id = msg.get("id", "")
                content = msg.get("content", "")
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, str):
                            parts.append(block)
                        elif isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    content = "".join(parts)
                if isinstance(content, str):
                    already = printed.get(msg_id, 0)
                    if len(content) > already:
                        yield content[already:]
                        printed[msg_id] = len(content)


async def create_student_sessions(
    client: LangGraphClient,
    first_name: str = "Student",
    last_name: str = "",
    email: str = "",
    goals: str = "",
) -> list[dict]:
    """Create one assistant + thread per module for a student."""
    student_name = f"{first_name} {last_name}".strip()
    namespace = f"{first_name.lower()}_{last_name.lower()}".strip("_")
    sessions = []
    for module in MODULES:
        assistant = await client.assistants.create(
            graph_id="tutor",
            name=f"{student_name} — {module['id']}",
            context={
                "module_id": module["id"],
                "student_name": student_name,
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
