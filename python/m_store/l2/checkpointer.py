"""
m_store L2 — Part 2: The Checkpointer

Sends a message to the deep_tutor agent and reads the thread state from
the checkpointer after the run completes.

The checkpointer is LangGraph's execution log. After every node, LangGraph
writes the current state (including all messages) to Postgres. From the SDK
client, the checkpointer is read-only — LangGraph manages all writes.

Run with deep_tutor running locally:
  uv run python checkpointer.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv(Path(__file__).parent / ".env")

DEPLOYMENT_URL = "http://127.0.0.1:2024"
API_KEY = os.environ.get("LANGSMITH_API_KEY", "")


async def main() -> None:
    client = get_client(url=DEPLOYMENT_URL, api_key=API_KEY)

    # ---------------------------------------------------------------------------
    # Create an assistant and thread
    #
    # An assistant is a named configuration on top of a graph.
    # A thread is a conversation — the checkpointer saves state per thread.
    # ---------------------------------------------------------------------------

    assistant = await client.assistants.create(
        graph_id="tutor",
        name="checkpointer-exercise",
        context={
            "module_id": "module-1",
            "student_name": "Jane Doe",
            "store_namespace": "jane_doe",
        },
    )
    thread = await client.threads.create()
    print(f"Assistant: {assistant['assistant_id']}")
    print(f"Thread:    {thread['thread_id']}\n")

    # ---------------------------------------------------------------------------
    # Send a message and wait for the response
    # ---------------------------------------------------------------------------

    result = await client.runs.wait(
        thread["thread_id"],
        assistant["assistant_id"],
        input={"messages": [{"role": "user", "content": "What is the checkpointer in LangGraph?"}]},
    )

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        content = last.get("content", "")
        if isinstance(content, list):
            content = "".join(
                b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
            )
        print(f"Agent response (truncated):\n{str(content)[:300]}...\n")

    # ---------------------------------------------------------------------------
    # Read thread state from the checkpointer
    #
    # get_state returns the last checkpoint — the full state after the final node.
    # values["messages"] contains the complete message history for this thread.
    # ---------------------------------------------------------------------------

    state = await client.threads.get_state(thread["thread_id"])
    messages = state["values"].get("messages", [])
    print(f"Checkpointer — thread has {len(messages)} messages:")
    for msg in messages:
        role = msg.get("type", msg.get("role", "?"))
        content = msg.get("content", "")
        if isinstance(content, list):
            content = content[0].get("text", "") if content else ""
        print(f"  [{role}]: {str(content)[:80]}")

    # ---------------------------------------------------------------------------
    # Read thread history
    #
    # get_history returns all checkpoints ever saved for this thread —
    # one per node execution. Shows how state evolved step by step.
    # ---------------------------------------------------------------------------

    history = await client.threads.get_history(thread["thread_id"])
    print(f"\nCheckpointer history — {len(history)} checkpoints saved for this thread")

    # ---------------------------------------------------------------------------
    # Clean up
    # ---------------------------------------------------------------------------

    await client.assistants.delete(assistant["assistant_id"])
    print(f"\nDeleted assistant {assistant['assistant_id']}")


if __name__ == "__main__":
    asyncio.run(main())
