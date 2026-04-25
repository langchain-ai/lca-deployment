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
    {"id": "tutor_l2", "label": "connecting to a deployment", "active": True},
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

def create_client(deployment_url: str, token: str | None = None) -> LangGraphClient:
    """Create a LangGraph client.

    Args:
        deployment_url: The LangGraph deployment URL entered in the UI.
                        Use http://127.0.0.1:2024 for local LangGraph Studio.
        token: Optional JWT to forward as Authorization: Bearer — used in step 2
               when auth.py is enabled in langgraph.json. Safe to pass in step 1;
               the header is ignored when auth is disabled.
    """
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}  # step 2: forward JWT to agent
    return get_client(url=deployment_url, api_key=api_key, headers=headers)


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
                    # Some LLMs (e.g. Gemini) return content as a list of typed blocks.
                    # Include plain strings and type="text" blocks; skip anything else
                    # (e.g. type="thinking" blocks from extended thinking models).
                    parts = []
                    for block in content:
                        if isinstance(block, str):
                            parts.append(block)
                        elif isinstance(block, dict):
                            if block.get("type") == "text":
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


async def write_sessions(client: LangGraphClient, namespace: str, sessions: list) -> None:
    """Persist sessions to the Store so they can be reused on subsequent logins."""
    await client.store.put_item((namespace,), key="sessions", value={"sessions": sessions})


async def get_sessions(client: LangGraphClient, namespace: str) -> list | None:
    """Read persisted sessions from the Store. Returns None if not found."""
    try:
        item = await client.store.get_item((namespace,), key="sessions")
        return item["value"]["sessions"] if item else None
    except Exception:
        return None


async def write_identity_map(client: LangGraphClient, identity: str, namespace: str) -> None:
    """Write an identity → namespace mapping to the Store.

    Allows login to find the student's profile (stored under first_last namespace)
    from an email or username identity. Periods and @ in identity are escaped.
    """
    safe = identity.replace("@", "_at_").replace(".", "_")
    await client.store.put_item(("__identity_map__",), key=safe, value={"namespace": namespace})


async def lookup_namespace(client: LangGraphClient, identity: str) -> str | None:
    """Look up the Store namespace for a given identity (email or username)."""
    safe = identity.replace("@", "_at_").replace(".", "_")
    try:
        item = await client.store.get_item(("__identity_map__",), key=safe)
        return item["value"]["namespace"] if item else None
    except Exception:
        return None
