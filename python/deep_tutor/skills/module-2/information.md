# Module 2 — Reference Material

## The LangGraph SDK

The LangGraph SDK is the client library you use to talk to a deployed agent. It is a thin wrapper over the deployment's HTTP API — every SDK call maps to an HTTP request against the built-in routes.

- **Python:** `from langgraph_sdk import get_client; client = get_client(url=..., api_key=...)`
- **TypeScript:** `import { Client } from "@langchain/langgraph-sdk"; const client = new Client({ apiUrl, apiKey })`

The URL points at the deployment (cloud URL or `http://localhost:2024` for local dev). The API key is read from the environment — never hardcoded.

## Threads

A **thread** is a server-side conversation slot stored in checkpoint memory. Pass `thread_id` on every run against the same conversation so the agent sees prior messages and state.

Threads persist beyond the originating run — any worker container can pick up a run on any thread, because the thread state lives in Postgres, not in process memory.

- Create: `await client.threads.create()` — returns `{thread_id: ...}`
- Reuse: pass `thread_id` to `runs.wait` / `runs.stream`
- Threads accumulate over time and are usually kept (resumability, observability). Delete with `client.threads.delete(thread_id)` if you need to.

## Runs

A **run** is one invocation of the agent. The client kicks off a run, the deployment's API server enqueues it, and a worker picks it up, calls `graph.invoke(...)` internally, and streams the result back.

- `client.runs.wait(thread_id, assistant_id, input=...)` — non-streaming; returns the final state after the run finishes
- `client.runs.stream(thread_id, assistant_id, input=..., stream_mode="messages-tuple")` — streams token-level deltas as the LLM generates

Always use `stream_mode="messages-tuple"` for SDK text streaming. The older `"messages"` mode requires manual dedup.

## Assistants

An **assistant** is a configuration record layered on top of a deployed graph. It holds the `context` injected into every run that uses it.

### Default assistant

When you deploy a graph, the Agent Server automatically creates a default assistant tied to it. The default assistant_id matches the graph name (here: `"tutor"`). You can pass the graph name directly to `runs.wait` / `runs.stream` to use it — no setup required.

### Named assistants

```python
assistant = await client.assistants.create(
    graph_id="tutor",
    name="Tutor — Module 1",
    context={"module_id": "module-1", "store_namespace": ""},
)
```

Context is stored server-side on the assistant. It is **not** resent on every run — the deployment injects it automatically whenever the assistant_id is used.

Two assistants on the same graph behave differently because of context — no code change, no redeployment.

### Updating context

`client.assistants.update(assistant_id, context={...})` replaces the entire context object. Pass all fields you want to keep, not just the ones changing.

### Context per-run override (Pattern B)

You can also pass `context=...` directly to `runs.wait` / `runs.stream`. Values override the assistant's stored context for that run only — the persisted context is unchanged.

```python
result = await client.runs.wait(
    thread_id,
    assistant_id,
    input={"messages": [...]},
    context={"module_id": "module-2"},  # this run only
)
```

### Deleting assistants

`client.assistants.delete(assistant_id)` frees the configuration record. It does not affect running containers or compute — assistants are config only.

## Routes: built-in and custom

Every LangSmith deployment exposes HTTP endpoints. Most are built-in (the **Agent Server API**); you can add your own.

### Built-in routes (Agent Server API)

Grouped roughly:

- `/runs/*` — start and manage runs
- `/threads/*` — manage conversation threads and checkpoints
- `/assistants/*` — create, list, update, delete assistants
- `/store/*` — key-value memory
- `/mcp/*` — Model Context Protocol resources
- plus health, auth, metadata, and `/docs` (Swagger UI listing every endpoint)

SDK calls map directly to these routes. `client.runs.wait` is a POST to `/runs/wait`; `client.threads.create` is a POST to `/threads`, and so on.

### Custom routes

The `http.app` field in `langgraph.json` points at a web application object. LangSmith mounts it alongside the built-in routes:

```json
{
  "graphs": { "tutor": "./agent/agent.py:graph" },
  "http": { "app": "./ui/app.py:app" }
}
```

- Python: a Starlette app (FastAPI works because it is Starlette under the hood)
- TypeScript: a Hono app

Custom routes share the deployment URL with the built-in routes. The tutor UI is the canonical example: a server proxy pattern where the browser talks to `/chat` on the deployment, and the custom `/chat` route uses the SDK to forward into the built-in `/runs` route.

### Discovering the deployment URL at runtime

Custom routes that need to make SDK calls back into the same deployment can't hardcode the URL — it differs between local dev, staging, and production. The recommended approach reads `X-Forwarded-Host` and `X-Forwarded-Proto` from the incoming request headers:

```python
host = request.headers.get("x-forwarded-host") or request.headers.get("host")
scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
url = f"{scheme}://{host}"
```

TLS terminates at the load balancer, so the raw request URL reflects only the internal network. The X-Forwarded headers carry the original public-facing values.

## The Tutor UI architecture

The deep_tutor UI uses a server proxy pattern co-deployed with the agent:

```
Browser (index.html)
    ↓ POST /chat
Custom route (app.py / app.ts)
    ↓ LangGraph SDK
Built-in Agent Server API (/runs)
    ↓
Agent (agent.py / agent.ts) → LLM
```

- Browser and server talk over `/chat`, `/register`, `/login`, `/modules`, `/resources` — all custom routes
- Server uses the LangGraph SDK to forward into the built-in `/runs`, `/threads`, `/assistants` routes
- One assistant + one thread created per module per student at registration; ids saved to `localStorage` and sent on every `/chat` request

## Quiz Questions

1. What is the LangGraph SDK, and what does a call like `client.runs.wait(...)` do under the hood?
2. What is the difference between a thread and an assistant?
3. How do you target the default assistant for a deployed graph without creating anything?
4. Where does the deployment store the context you set on an assistant?
5. What happens to a stored field if you `update()` an assistant with only one context field present?
6. How does passing `context=...` directly to `runs.wait` differ from setting it on the assistant?
7. What are the built-in route categories exposed by every deployment?
8. Which `langgraph.json` field registers custom HTTP routes?
9. Why does a custom route need to discover the deployment URL at runtime instead of hardcoding it?
10. Walk me through what happens when a student types a message into the tutor UI.
