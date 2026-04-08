"""
2.1 — Connecting an Assistant to a Deployment

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
  4. Update the assistant with a system prompt (context)
  5. Run a thread using the assistant
  6. Delete the assistant when done

Once you have created a client and set up an assistant:
- Context (system prompt, model config) is stored server-side on the assistant.
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

from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()

DEPLOYMENT_URL = os.environ.get("LANGGRAPH_URL", "http://127.0.0.1:2024")
API_KEY = os.environ.get("LANGSMITH_API_KEY", "")


async def main():

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

    assistant = await client.assistants.create(
        graph_id="tutor",
        name="Tutor — Lesson 1",
        context={},
    )
    print(f"\nCreated assistant: {assistant['assistant_id']}  name={assistant['name']}")

    # ---------------------------------------------------------------------------
    # Step 4: Update the assistant with a system prompt
    #
    # The system prompt is passed via the `context` field.
    # NOTE: When updating, include ALL context fields — not just the ones changing.
    # ---------------------------------------------------------------------------

    assistant = await client.assistants.update(
        assistant["assistant_id"],
        context={
            "lesson_id": "tutor_l1",
            "student_name": "Student",
        },
    )
    print(f"Updated assistant: {assistant['assistant_id']}")

    # ---------------------------------------------------------------------------
    # Step 5: Run a thread using the assistant
    # ---------------------------------------------------------------------------

    thread = await client.threads.create()
    print(f"\nThread: {thread['thread_id']}")

    printed = 0  # track how much of the cumulative content we've already printed
    async for event in client.runs.stream(
        thread["thread_id"],
        assistant["assistant_id"],
        input={"messages": [{"role": "user", "content": "What is the Agent Server?"}]},
        stream_mode="messages",
    ):
        if isinstance(event.data, list):
            for item in event.data:
                msg = item[0] if isinstance(item, (list, tuple)) else item
                if isinstance(msg, dict) and msg.get("type") in ("AIMessageChunk", "AIMessage", "ai"):
                    content = msg.get("content", "")
                    if isinstance(content, str) and len(content) > printed:
                        print(content[printed:], end="", flush=True)
                        printed = len(content)
    print()

    # ---------------------------------------------------------------------------
    # Step 6: Delete the assistant
    #
    # Frees the configuration record. Does not affect compute resources.
    # ---------------------------------------------------------------------------

    await client.assistants.delete(assistant["assistant_id"])
    print(f"\nDeleted assistant: {assistant['assistant_id']}")


if __name__ == "__main__":
    asyncio.run(main())
