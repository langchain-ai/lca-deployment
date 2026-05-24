"""
agent_client.py — LangGraph SDK client for the m6 local UI server

Trimmed from python/deep_tutor/ui/agent_client.py — the dacli_tutor variant uses
the CLI's default "agent" assistant (no per-module assistant creation), so
create_student_sessions isn't needed here. The streaming pattern is identical.
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from langgraph_sdk import get_client
from langgraph_sdk.client import LangGraphClient

load_dotenv(override=True)  # prefer .env file


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
        if message_chunk.get("type") != "AIMessageChunk":
            continue  # skip tool calls / tool results — show only the agent's reply
        content = message_chunk.get("content", "")
        if isinstance(content, list):
            content = "".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        if content:
            yield content
