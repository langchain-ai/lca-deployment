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
  5. Run a thread using assistant_l1 (non-streaming)
  5b. Create assistant_l2 and run it streaming — same question, different context
  6. Delete both assistants when done

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

    assistant_l1 = await client.assistants.create(
        graph_id="tutor",
        name="Tutor — Lesson 1",
        context={},
    )
    print(f"\nCreated assistant: {assistant_l1['assistant_id']}  name={assistant_l1['name']}")

    # ---------------------------------------------------------------------------
    # Step 4: Update the assistant with a system prompt
    #
    # The system prompt is passed via the `context` field.
    # NOTE: When updating, include ALL context fields — not just the ones changing.
    # ---------------------------------------------------------------------------

    assistant_l1 = await client.assistants.update(
        assistant_l1["assistant_id"],
        context={
            "lesson_id": "tutor_l1",
            "student_name": "Student",
        },
    )
    print(f"Updated assistant: {assistant_l1['assistant_id']}")

    # ---------------------------------------------------------------------------
    # Step 5: Run a thread using the assistant
    # ---------------------------------------------------------------------------

    thread = await client.threads.create()
    print(f"\nThread: {thread['thread_id']}")

    result = await client.runs.wait(
        thread["thread_id"],
        assistant_l1["assistant_id"],
        input={"messages": [{"role": "user", "content": "What lesson number is this?"}]},
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
    # Step 5b: Create a second assistant with lesson 2 context — streaming output
    #
    # Same graph, same question — different context means a different lesson.
    # This time we stream the response to show how streaming works.
    # ---------------------------------------------------------------------------

    assistant_l2 = await client.assistants.create(
        graph_id="tutor",
        name="Tutor — Lesson 2",
        context={
            "lesson_id": "tutor_l2",
            "student_name": "Student",
        },
    )
    print(f"\nCreated assistant: {assistant_l2['assistant_id']}  name={assistant_l2['name']}")

    thread_l2 = await client.threads.create()
    print(f"Thread: {thread_l2['thread_id']}\n")

    printed: dict[str, int] = {}
    async for event in client.runs.stream(
        thread_l2["thread_id"],
        assistant_l2["assistant_id"],
        input={"messages": [{"role": "user", "content": "What lesson number is this?"}]},
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
                    content = "".join(
                        b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                if isinstance(content, str):
                    already = printed.get(msg_id, 0)
                    if len(content) > already:
                        print(content[already:], end="", flush=True)
                        printed[msg_id] = len(content)
    print()

    # ---------------------------------------------------------------------------
    # Step 6: Delete both assistants
    #
    # Frees the configuration records. Does not affect compute resources.
    # ---------------------------------------------------------------------------

    await client.assistants.delete(assistant_l1["assistant_id"])
    print(f"\nDeleted assistant_l1: {assistant_l1['assistant_id']}")
    await client.assistants.delete(assistant_l2["assistant_id"])
    print(f"Deleted assistant_l2: {assistant_l2['assistant_id']}")


if __name__ == "__main__":
    asyncio.run(main())
