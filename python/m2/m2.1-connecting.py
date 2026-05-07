"""
m2.1 — Connecting an Assistant to a Deployment

This file shows the steps to connect a LangSmith assistant to a deployed
LangGraph agent.

An assistant is a configuration layer on top of a deployed graph. It lets you:
- Set a custom system prompt
- Configure model and tool settings
- Create multiple variants of the same graph

Steps:
  1. Connect to your deployment
  2. List available graphs (to find the graph_id)
  3. Create an assistant pointing to your graph
  4. Update the assistant with context
  5. Create a thread
  6a. Run the assistant (non-streaming)
  6b. Create assistant_m2 and run it streaming — same question, different context
  7. Delete both assistants when done

Once you have created a client and set up an assistant:
- Context is stored server-side on the assistant.
  You do NOT resend it on every call — the server applies it automatically
  whenever you use that assistant_id.
- Config (e.g. thread_id) is passed per run. It is ephemeral — you pass it
  each time to identify the conversation thread.
- Assistants are configuration records only — deleting one does not affect
  compute resources or running containers.

Documentation:
  LangSmith Assistants:      https://docs.langchain.com/langsmith/assistants
  Create Assistant API:      https://docs.langchain.com/langsmith/agent-server-api/assistants/create-assistant
  Patch Assistant API:       https://docs.langchain.com/langsmith/agent-server-api/assistants/patch-assistant
  Delete Assistant API:      https://docs.langchain.com/langsmith/agent-server-api/assistants/delete-assistant
  SDK examples:              https://docs.langchain.com/langsmith/configuration-cloud
  LangGraph SDK (Python):    https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/
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
    # Step 2: List available assistants/graphs
    # ---------------------------------------------------------------------------

    assistants = await client.assistants.search()
    print("Available assistants/graphs:")
    for a in assistants:
        print(f"  graph_id={a['graph_id']}  assistant_id={a['assistant_id']}  name={a['name']}")

    # ---------------------------------------------------------------------------
    # Step 3: Create an assistant for a graph
    #
    # A default assistant is created automatically for each graph when you deploy.
    # Use this step if you want a named assistant with custom configuration.
    # ---------------------------------------------------------------------------

    assistant_m1 = await client.assistants.create(
        graph_id="tutor",
        name="Tutor — Module 1",
        context={},
    )
    print(f"\nCreated assistant: {assistant_m1['assistant_id']}  name={assistant_m1['name']}")

    # ---------------------------------------------------------------------------
    # Step 4: Update the assistant with context
    #
    # NOTE: When updating, include ALL context fields — not just the ones changing.
    # ---------------------------------------------------------------------------

    assistant_m1 = await client.assistants.update(
        assistant_m1["assistant_id"],
        context={
            "module_id": "module-1",
            "store_namespace": "",
        },
    )
    print(f"Updated assistant: {assistant_m1['assistant_id']}")

    # ---------------------------------------------------------------------------
    # Step 5: Create a thread
    # ---------------------------------------------------------------------------

    thread = await client.threads.create()
    print(f"\nThread: {thread['thread_id']}")

    # ---------------------------------------------------------------------------
    # Step 6a: Run the assistant
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
    # Step 6b: Create a second assistant with module 2 context — streaming output
    #
    # Same graph, same question — different context means different behavior.
    # This time we stream the response to show how streaming works.
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
    # Step 7: Delete both assistants
    #
    # Frees the configuration records. Does not affect compute resources.
    # ---------------------------------------------------------------------------

    await client.assistants.delete(assistant_m1["assistant_id"])
    print(f"\nDeleted assistant_m1: {assistant_m1['assistant_id']}")
    await client.assistants.delete(assistant_m2["assistant_id"])
    print(f"Deleted assistant_m2: {assistant_m2['assistant_id']}")


if __name__ == "__main__":
    asyncio.run(main())
