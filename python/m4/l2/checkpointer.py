"""
m4 L2 — Part 2: The Checkpointer

Sends a message to the deep_tutor agent and reads the thread state from
the checkpointer after the run completes.

The checkpointer is LangGraph's execution log. After every superstep, LangGraph
writes the current state (including all messages) to Postgres. From the SDK
client, the checkpointer is read-only — LangGraph manages all writes.

Steps:
  1. Connect to your deployment
  2. Create an assistant and thread
  3. Send a message and wait for the response
  4. Read thread state from the checkpointer
  5. Read thread history
  6. Clean up

Run against a local deployment (default) or pass a cloud URL:
  uv run python checkpointer.py
  uv run python checkpointer.py https://tutor-xyz.us.langgraph.app
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv(override=True)  # prefer .env file

_url_provided = len(sys.argv) > 1
DEPLOYMENT_URL = sys.argv[1] if _url_provided else "http://localhost:2024"
API_KEY = os.environ.get("LANGSMITH_API_KEY", "")

CHECK = "✅"
ARROW = "→"


async def check_connection() -> None:
    try:
        async with httpx.AsyncClient() as http:
            r = await http.get(f"{DEPLOYMENT_URL}/ok", timeout=5)
            r.raise_for_status()
    except Exception as e:
        if _url_provided:
            sys.exit(f"Cannot reach deployment at {DEPLOYMENT_URL}\nCheck the URL and try again.\n{e}")
        else:
            sys.exit(f"Cannot reach local dev server at {DEPLOYMENT_URL}\nIs `langgraph dev` running?\n{e}")


async def main() -> None:
    await check_connection()

    # ---------------------------------------------------------------------------
    # Step 1: Connect to your deployment
    # ---------------------------------------------------------------------------

    client = get_client(url=DEPLOYMENT_URL, api_key=API_KEY)
    print(f"{CHECK} Connected: {DEPLOYMENT_URL}")

    # ---------------------------------------------------------------------------
    # Step 2: Create an assistant and thread
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
    print(f"{CHECK} Assistant: {assistant['assistant_id']}")
    print(f"{CHECK} Thread:    {thread['thread_id']}")

    # ---------------------------------------------------------------------------
    # Step 3: Send a message and wait for the response
    # ---------------------------------------------------------------------------

    query = "What is the checkpointer in LangGraph?"
    print(f"\n{ARROW} Running (wait): {query}")
    result = await client.runs.wait(
        thread["thread_id"],
        assistant["assistant_id"],
        input={"messages": [{"role": "user", "content": query}]},
    )

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        content = last.get("content", "")
        if isinstance(content, list):
            content = "".join(
                b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
            )
        print(f"{CHECK} Response (truncated): {str(content)[:300]}...")

    # ---------------------------------------------------------------------------
    # Step 4: Read thread state from the checkpointer
    #
    # get_state returns the last checkpoint — the full state after the final node.
    # values["messages"] contains the complete message history for this thread.
    # ---------------------------------------------------------------------------

    state = await client.threads.get_state(thread["thread_id"])
    messages = state["values"].get("messages", [])
    print(f"\n{CHECK} Checkpointer — thread has {len(messages)} messages:")
    for msg in messages:
        role = msg.get("type", msg.get("role", "?"))
        content = msg.get("content", "")
        if isinstance(content, list):
            content = content[0].get("text", "") if content else ""
        print(f"  [{role}]: {str(content)[:80]}")

    # ---------------------------------------------------------------------------
    # Step 5: Read thread history
    #
    # get_history returns all checkpoints ever saved for this thread —
    # one per node execution. Shows how state evolved step by step.
    # ---------------------------------------------------------------------------

    history = await client.threads.get_history(thread["thread_id"])
    print(f"\n{CHECK} Checkpointer history — {len(history)} checkpoints saved for this thread")

    # ---------------------------------------------------------------------------
    # Step 6: Clean up
    # ---------------------------------------------------------------------------

    await client.assistants.delete(assistant["assistant_id"])
    print(f"\n{CHECK} Deleted assistant {assistant['assistant_id']}")


if __name__ == "__main__":
    asyncio.run(main())
