# Tutor L2 — Lesson Information

## The LangGraph SDK

The LangGraph SDK is a thin client library for talking to a deployed LangGraph agent. It wraps the Agent Server HTTP API and handles authentication, streaming, and request formatting.

Install:
- Python: `langgraph-sdk` (already a dependency of `langgraph`)
- TypeScript: `@langchain/langgraph-sdk`

## Creating a Client

The client is the entry point for all SDK calls. You need two things:
- **`url`** — the deployment URL. Use `http://127.0.0.1:2024` for local LangGraph Studio; use the URL from the LangSmith Deployments tab for a cloud deployment.
- **`api_key`** — your LangSmith API key. Always read from the environment — never hardcode it.

```python
# Python
from langgraph_sdk import get_client
client = get_client(url=deployment_url, api_key=api_key)
```

```typescript
// TypeScript
import { Client } from "@langchain/langgraph-sdk";
const client = new Client({ apiUrl: deploymentUrl, apiKey });
```

The client is stateless — you can create one per request or cache it per deployment URL.

## Assistants

An assistant is a configuration record stored server-side on top of a deployed graph. It holds:
- **`graph_id`** — which graph this assistant targets (e.g. `"tutor"`)
- **`name`** — a human-readable label
- **`context`** — a dict of runtime configuration values the agent reads at execution time

When you deploy a graph, a default assistant is created automatically. You create additional assistants when you want named variants — for example, one per student per lesson, each pre-configured with that student's context.

```python
# Create an assistant with context
assistant = await client.assistants.create(
    graph_id="tutor",
    name="jane_doe — tutor_l1",
    context={
        "lesson_id": "tutor_l1",
        "store_namespace": "jane_doe",
        "student_name": "Jane",
    },
)
assistant_id = assistant["assistant_id"]
```

**Context is stored server-side.** You set it once when creating (or updating) the assistant. The agent receives it automatically on every run — you do not resend it.

To update context, include ALL fields — the update call replaces the entire context object:

```python
assistant = await client.assistants.update(
    assistant_id,
    context={"lesson_id": "tutor_l2", "store_namespace": "jane_doe", "student_name": "Jane"},
)
```

To list all assistants for a deployment:

```python
assistants = await client.assistants.search()
```

To delete an assistant (frees the config record; does not affect compute):

```python
await client.assistants.delete(assistant_id)
```

## Threads

A thread holds conversation history. All messages in a conversation live in a single thread. Create a thread once; reuse it across turns by passing the same `thread_id`.

```python
thread = await client.threads.create()
thread_id = thread["thread_id"]
```

The thread is a durable record in Postgres. If you lose the `thread_id`, the history is gone from the client's perspective (though it still exists on the server).

## Runs and Streaming

A run executes the agent graph against a thread. Use `client.runs.stream()` to send a message and receive the response as a stream of events.

```python
async for event in client.runs.stream(
    thread_id,
    assistant_id,
    input={"messages": [{"role": "user", "content": "What is the Agent Server?"}]},
    stream_mode="messages",
):
    ...
```

- `thread_id` — the conversation thread
- `assistant_id` — which assistant to use (provides graph_id + context)
- `input` — the message to send (follows LangChain message format)
- `stream_mode` — controls what events are emitted (see below)

## stream_mode="messages"

With `stream_mode="messages"`, each event contains the current state of one or more messages. Because LangGraph emits state updates as the graph runs, the same message may appear multiple times with accumulated content. Your client must track how much of each message it has already processed.

```python
printed: dict[str, int] = {}  # cumulative bytes printed per message ID

async for event in client.runs.stream(..., stream_mode="messages"):
    if not isinstance(event.data, list):
        continue
    for item in event.data:
        msg = item[0] if isinstance(item, (list, tuple)) else item
        if not isinstance(msg, dict):
            continue
        if msg.get("type") in ("AIMessageChunk", "AIMessage", "ai"):
            msg_id = msg.get("id", "")
            content = msg.get("content", "")
            # Normalize list-format content (used by some LLMs, e.g. Gemini)
            if isinstance(content, list):
                content = "".join(
                    block if isinstance(block, str) else block.get("text", "")
                    for block in content
                    if isinstance(block, str) or (
                        isinstance(block, dict)
                        and block.get("type") == "text"
                        and not block.get("extras", {}).get("signature")
                    )
                )
            if isinstance(content, str):
                already = printed.get(msg_id, 0)
                if len(content) > already:
                    yield content[already:]
                    printed[msg_id] = len(content)
```

**Why track cumulative content?** LangGraph sends the full accumulated content each time, not just new characters. Without deduplication, each event would re-print everything from the start of the message.

**Why normalize list content?** Some LLMs (e.g. Gemini 2.5 Flash with extended thinking) return content as a list of blocks instead of a plain string. The code above extracts plain text blocks and skips thinking blocks (identified by `extras.signature`).

## Context vs Config

These two terms are easy to confuse:

| | Context | Config |
|---|---|---|
| **What it is** | Per-assistant configuration (lesson_id, student_name, store_namespace) | Per-run routing (thread_id) |
| **Where it lives** | Stored server-side on the assistant record | Passed by the client on each run call |
| **When you set it** | Once, when creating or updating the assistant | Every run |
| **Purpose** | Shapes the agent's behavior (which lesson, whose name) | Identifies which conversation thread to use |

## create_student_sessions

The tutor UI calls this once when a student clicks Start. It creates one assistant and one thread per lesson, each assistant pre-configured with the student's context. The returned `assistant_id` and `thread_id` pairs are saved in localStorage and sent with every `/chat` request.

```python
async def create_student_sessions(client, namespace, student_name="Student"):
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
```

Each lesson gets its own assistant (so each has its own `lesson_id` context) and its own thread (so each has its own conversation history). Switching lessons in the UI switches both the `assistant_id` and `thread_id`.

## The LangGraph Store

The Store provides persistent, cross-thread memory keyed by namespace. Unlike threads (which hold one conversation), the Store survives across sessions and threads.

The tutor UI uses it to store the student's profile (name, goals, preferences). The agent reads this at runtime when personalizing responses.

```python
# Write a profile
await client.store.put_item(
    (namespace,),       # tuple used as namespace key
    key="profile",
    value={"first_name": "Jane", "goals": "learn LangGraph", "preferences": "concise"},
)

# Read a profile
item = await client.store.get_item((namespace,), key="profile")
profile = item["value"] if item else None
```

- The namespace tuple acts as a hierarchical key prefix (e.g. `("jane_doe",)`)
- Each item has a `key` within the namespace
- `put_item` creates or overwrites; `get_item` returns `None` if not found

## The Server Proxy Pattern

The tutor UI doesn't call the LangGraph SDK directly from the browser. Instead, it uses a server proxy:

```
Browser (index.html)  →  Agent Server (app.py)  →  LangGraph SDK  →  LangSmith Deployment
```

The browser sends requests to the local server, which holds the `LANGSMITH_API_KEY` and makes authenticated SDK calls. This keeps the API key off the client entirely.

The `deployment_url` is passed from the browser on each request (students enter it in the config tab), which lets them switch between local and cloud deployments without restarting the server.

## Quiz Questions

1. What two things do you need to create a LangGraph client? Where does each come from?
2. What is an assistant? What is stored in its `context`?
3. What is the difference between `context` and `config` (thread_id)?
4. What does `stream_mode="messages"` emit? Why do you need to track cumulative content per message ID?
5. What does `create_student_sessions` create, and why one of each per lesson?
6. What is the LangGraph Store used for in the tutor UI?
7. Why does the tutor UI use a server proxy pattern instead of calling the SDK directly from the browser?
