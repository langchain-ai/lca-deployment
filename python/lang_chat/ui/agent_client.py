"""
agent_client.py — LangGraph client

This is the interesting file for students learning how to connect to a deployed
LangGraph agent. It shows how to:

  1. Create a client connected to a LangGraph deployment
  2. Create and manage threads
  3. Send a message and stream the response back
  4. Create assistants (one per lesson, per student)
  5. Read and write student profiles via the LangGraph Store

The deployment URL comes from the UI (students paste their URL in).
The API key comes from .env — it never touches the browser.

Documentation:
  LangGraph SDK (Python): https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from langgraph_sdk import get_client
from langgraph_sdk.client import LangGraphClient

load_dotenv()

# Lessons available in this course
LESSONS = [
    {"id": "tutor_l1", "label": "deployment architecture", "active": True},
    {"id": "tutor_l2", "label": "lesson 2", "active": False},
    {"id": "tutor_l3", "label": "lesson 3", "active": False},
    {"id": "tutor_l4", "label": "lesson 4", "active": False},
    {"id": "tutor_l5", "label": "lesson 5", "active": False},
    {"id": "tutor_l6", "label": "lesson 6", "active": False},
    {"id": "tutor_l7", "label": "lesson 7", "active": False},
]

# ---------------------------------------------------------------------------
# 1. Create a client connected to a LangGraph deployment
#    URL comes from the UI; API key comes from .env
# ---------------------------------------------------------------------------

def create_client(deployment_url: str) -> LangGraphClient:
    """Create a LangGraph client.

    Args:
        deployment_url: The LangGraph deployment URL entered in the UI.
                        Use http://127.0.0.1:2024 for local LangGraph Studio.
    """
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    return get_client(url=deployment_url, api_key=api_key)


# ---------------------------------------------------------------------------
# 2. Thread management
# ---------------------------------------------------------------------------

async def create_thread(client: LangGraphClient) -> str:
    """Create a new conversation thread. Returns the thread_id."""
    thread = await client.threads.create()
    return thread["thread_id"]


# ---------------------------------------------------------------------------
# 3. Send a message and stream the response
# ---------------------------------------------------------------------------

async def stream_response(
    client: LangGraphClient,
    thread_id: str,
    assistant_id: str,
    message: str,
) -> AsyncGenerator[str, None]:
    """Send a message to the agent and stream the response.

    Args:
        client: LangGraph client
        thread_id: The thread to send the message on
        assistant_id: Which assistant to use
        message: The user's message

    Yields:
        Text chunks from the agent's response
    """
    printed: dict[str, int] = {}  # track cumulative content per message ID
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
                    # Normalize list content blocks to a single string.
                    # Gemini 2.5 Flash uses extended thinking: thinking blocks are
                    # dicts with extras.signature; the actual response is a plain string.
                    parts = []
                    for block in content:
                        if isinstance(block, str):
                            parts.append(block)
                        elif isinstance(block, dict):
                            # Skip thinking blocks (have extras.signature)
                            if block.get("type") == "text" and not block.get("extras", {}).get("signature"):
                                parts.append(block.get("text", ""))
                    content = "".join(parts)
                if isinstance(content, str):
                    already = printed.get(msg_id, 0)
                    if len(content) > already:
                        yield content[already:]
                        printed[msg_id] = len(content)


# ---------------------------------------------------------------------------
# 4. Student setup — assistants and threads
#
# Called once when a student hits Start. Creates one assistant and one thread
# per lesson, each with the student's store namespace in the assistant context.
# ---------------------------------------------------------------------------

async def create_student_sessions(
    client: LangGraphClient,
    namespace: str,
    student_name: str = "Student",
) -> list[dict]:
    """Create one assistant + thread per lesson for a student.

    Args:
        client: LangGraph client
        namespace: Student namespace (first_last), used as Store key prefix
        student_name: Student's display name, included in assistant context

    Returns:
        List of session dicts: [{lesson_id, assistant_id, thread_id}, ...]
    """
    sessions = []
    for lesson in LESSONS:
        assistant = await client.assistants.create(
            graph_id="tutor",
            name=f"{namespace} — {lesson['id']}",
            context={
                "lesson_id": lesson["id"],
                "store_namespace": namespace,
                "student_name": student_name,
            },
        )
        thread = await client.threads.create()
        sessions.append({
            "lesson_id": lesson["id"],
            "assistant_id": assistant["assistant_id"],
            "thread_id": thread["thread_id"],
        })
    return sessions


# ---------------------------------------------------------------------------
# 5. Student profile — LangGraph Store
#
# The Store provides persistent, cross-thread memory keyed by namespace.
# We use it to store the student's profile (name, goals, preferences).
# The deployed agent reads this at runtime to personalize responses.
# ---------------------------------------------------------------------------

async def write_student_profile(
    client: LangGraphClient,
    namespace: str,
    profile: dict,
) -> None:
    """Write a student profile to the LangGraph Store.

    Args:
        client: LangGraph client
        namespace: Student namespace (first_last)
        profile: Dict with fields: first_name, last_name, goals, preferences
    """
    await client.store.put_item(
        (namespace,),
        key="profile",
        value=profile,
    )


async def get_student_profile(
    client: LangGraphClient,
    namespace: str,
) -> dict | None:
    """Read a student profile from the LangGraph Store.

    Args:
        client: LangGraph client
        namespace: Student namespace (first_last)

    Returns:
        Profile dict, or None if not found
    """
    try:
        item = await client.store.get_item(
            (namespace,),
            key="profile",
        )
        return item["value"] if item else None
    except Exception:
        return None
