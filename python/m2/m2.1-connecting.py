"""
m2.1 — Connecting to your deployment

Demonstrates the basic connect → thread → run flow against a deployed agent.
Uses the default assistant (graph name "tutor") — no named assistant required.

Steps:
  1. Connect to your deployment
  2. Create a thread
  3. Run (wait) against the default assistant
  4. Stream the response

Documentation:
  LangGraph SDK (Python): https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/
  Run execution lifecycle: https://docs.langchain.com/langsmith/agent-server#run-execution-lifecycle
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


async def main():
    await check_connection()

    # ---------------------------------------------------------------------------
    # Step 1: Connect to your deployment
    # ---------------------------------------------------------------------------

    client = get_client(url=DEPLOYMENT_URL, api_key=API_KEY)
    print(f"{CHECK} Connected: {DEPLOYMENT_URL}")

    # ---------------------------------------------------------------------------
    # Step 2: Create a thread
    # ---------------------------------------------------------------------------

    thread = await client.threads.create()
    print(f"{CHECK} Thread created: {thread['thread_id']}")

    # ---------------------------------------------------------------------------
    # Step 3: Run against the default assistant
    #
    # "tutor" is the graph name — it doubles as the assistant_id of the default
    # assistant that the deployment created for that graph.
    # ---------------------------------------------------------------------------

    query = "In one sentence, what is the LangGraph runtime?"
    print(f"\n{ARROW} Running (wait): {query}")
    result = await client.runs.wait(
        thread["thread_id"],
        "tutor",
        input={"messages": [{"role": "user", "content": query}]},
    )
    messages = result.get("messages", [])
    if messages:
        content = messages[-1].get("content", "")
        if isinstance(content, list):
            content = "".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        print(f"{CHECK} Response: {content}")

    # ---------------------------------------------------------------------------
    # Step 4: Stream the response
    # ---------------------------------------------------------------------------

    query = "In one sentence, what does the Agent Server include?"
    print(f"\n{ARROW} Running (stream): {query}")
    print(f"{CHECK} Response: ", end="", flush=True)
    async for event in client.runs.stream(
        thread["thread_id"],
        "tutor",
        input={"messages": [{"role": "user", "content": query}]},
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
            print(content, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
