"""
m2.2 — Assistants and Context

Demonstrates creating named assistants with custom context, and how two
assistants on the same graph behave differently based on the context bound
to each.

Steps:
  1. Connect to your deployment
  2. Create a named assistant (assistant_m1) with module-1 context
  3. Create a thread
  4. Run (wait) — module-1 response
  5. Create a second named assistant (assistant_m2) with module-2 context +
     a new thread + a streamed run — module-2 response
  6. Delete both assistants

Documentation:
  LangSmith Assistants:    https://docs.langchain.com/langsmith/assistants
  Create Assistant API:    https://docs.langchain.com/langsmith/agent-server-api/assistants/create-assistant
  Patch Assistant API:     https://docs.langchain.com/langsmith/agent-server-api/assistants/patch-assistant
  LangGraph SDK (Python):  https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()  # expects python/.env — loads LANGSMITH_API_KEY

_url_provided = len(sys.argv) > 1
DEPLOYMENT_URL = sys.argv[1] if _url_provided else "http://localhost:2024"
API_KEY = os.environ.get("LANGSMITH_API_KEY", "")


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


async def main():
    await check_connection()

    # ---------------------------------------------------------------------------
    # Step 1: Connect to your deployment
    # ---------------------------------------------------------------------------

    client = get_client(url=DEPLOYMENT_URL, api_key=API_KEY)

    # ---------------------------------------------------------------------------
    # Step 2: Create a named assistant for module 1
    #
    # Context is stored server-side on the assistant. Every run that uses this
    # assistant_id gets module_id and store_namespace injected automatically.
    # ---------------------------------------------------------------------------

    assistant_m1 = await client.assistants.create(
        graph_id="tutor",
        name="Tutor — Module 1",
        context={
            "module_id": "module-1",
            "store_namespace": "",
        },
    )
    print(f"Created assistant: {assistant_m1['assistant_id']}  name={assistant_m1['name']}")

    # ---------------------------------------------------------------------------
    # Step 3: Create a thread
    # ---------------------------------------------------------------------------

    thread = await client.threads.create()
    print(f"Thread: {thread['thread_id']}")

    # ---------------------------------------------------------------------------
    # Step 4: Run against the named assistant
    # ---------------------------------------------------------------------------

    result = await client.runs.wait(
        thread["thread_id"],
        assistant_m1["assistant_id"],
        input={"messages": [{"role": "user", "content": "What module is this?"}]},
    )
    messages = result.get("messages", [])
    if messages:
        content = messages[-1].get("content", "")
        if isinstance(content, list):
            content = "".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        print(content)

    # ---------------------------------------------------------------------------
    # Step 5: Second assistant with module-2 context — streaming
    #
    # Same graph, same question. Different context => different answer.
    # ---------------------------------------------------------------------------

    assistant_m2 = await client.assistants.create(
        graph_id="tutor",
        name="Tutor — Module 2",
        context={
            "module_id": "module-2",
            "store_namespace": "",
        },
    )
    print(f"\nCreated assistant: {assistant_m2['assistant_id']}  name={assistant_m2['name']}")

    thread_m2 = await client.threads.create()
    print(f"Thread: {thread_m2['thread_id']}\n")

    async for event in client.runs.stream(
        thread_m2["thread_id"],
        assistant_m2["assistant_id"],
        input={"messages": [{"role": "user", "content": "What module is this?"}]},
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
            print(content, end="", flush=True)
    print()

    # ---------------------------------------------------------------------------
    # Step 6: Delete both assistants
    #
    # Frees the configuration records. Does not affect compute or running
    # containers — assistants are config only.
    # ---------------------------------------------------------------------------

    await client.assistants.delete(assistant_m1["assistant_id"])
    print(f"\nDeleted assistant_m1: {assistant_m1['assistant_id']}")
    await client.assistants.delete(assistant_m2["assistant_id"])
    print(f"Deleted assistant_m2: {assistant_m2['assistant_id']}")


if __name__ == "__main__":
    asyncio.run(main())
