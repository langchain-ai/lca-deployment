# Invoke and Run: Local vs Deployed Execution

If you have taken previous LangChain or LangGraph courses that demonstrate by running graphs locally, you may recall 

- **Locally**, you call `graph.invoke(input, config)` directly. 
 
While,  

- **Against a deployment**, you call `client.runs.wait(thread_id, assistant_id, input)`.

These look different on the surface but accomplish the same thing. The difference is *where* the work happens and *how* it's orchestrated.

---

## Local: in-process invoke

When you run a LangGraph app locally — in a script, notebook, or test — your code holds the compiled graph in memory. You call `invoke` (or `stream`) directly. Three inputs to the graph are:

- **`input`** — the state to start with (messages, etc.)
- **`context`** — typed runtime values matching the graph's `context_schema` (e.g., `module_id`, `store_namespace`)
- **`config`** — LangGraph runtime config: `recursion_limit`, plus `configurable` where `thread_id` lives

<Tabs>
  <Tab title="Python">
```python
result = graph.invoke(
    {"messages": [{"role": "user", "content": "What module is this?"}]},
    context={"module_id": "module-1", "store_namespace": "jane@example_com"},
    config={"configurable": {"thread_id": "abc-123"}},
)
```
  </Tab>
  <Tab title="TypeScript">
```typescript
const result = await graph.invoke(
  { messages: [{ role: "user", content: "What module is this?" }] },
  {
    context: { module_id: "module-1", store_namespace: "jane@example_com" },
    configurable: { thread_id: "abc-123" },
  },
);
```
  </Tab>
</Tabs>

Context and config are different things: context is what the graph's nodes read at runtime to do their work; config is LangGraph plumbing (which thread, what recursion limit, etc.).

---

## Deployed: client → API server → queue worker → invoke

When the graph is deployed, you don't have it in your local process anymore. It lives inside a container managed by LangSmith Deployment. The same three pieces from the local invoke — `input`, `context`, `config` — still apply, but you have a choice about *when* to send them.

### Pattern A: Configure on create, run with just input

Send `context` and `config` to the deployment's persistent storage when you create (or update) the assistant. Each subsequent run sends only `input`; the deployment loads the stored values and injects them into the graph at run time. (Unlike a local invoke, the values can't sit in process memory — workers are stateless and any worker can pick up any run.)

<Tabs>
  <Tab title="Python">
```python
# One-time setup (or whenever you want to change defaults)
assistant = await client.assistants.create(
    graph_id="tutor",
    context={"module_id": "module-1", "store_namespace": "jane@example_com"},
    config={"recursion_limit": 50},
)

# Every run uses the stored context and config
result = await client.runs.wait(
    thread["thread_id"],
    assistant["assistant_id"],
    input={"messages": [{"role": "user", "content": "What module is this?"}]},
)
```
  </Tab>
  <Tab title="TypeScript">
```typescript
// One-time setup
const assistant = await client.assistants.create({
  graphId: "tutor",
  context: { module_id: "module-1", store_namespace: "jane@example_com" },
  config: { recursion_limit: 50 },
});

// Every run uses the stored context and config
const result = await client.runs.wait(thread.thread_id, assistant.assistant_id, {
  input: { messages: [{ role: "user", content: "What module is this?" }] },
});
```
  </Tab>
</Tabs>

### Pattern B: Send context and config in the run

Pass `context` and/or `config` directly to `runs.wait` to override the assistant's stored values for this specific call. The shape mirrors the local `invoke` — all three pieces in one call:

<Tabs>
  <Tab title="Python">
```python
result = await client.runs.wait(
    thread["thread_id"],
    assistant["assistant_id"],
    input={"messages": [{"role": "user", "content": "What module is this?"}]},
    context={"module_id": "module-1", "store_namespace": "jane@example_com"},
    config={"recursion_limit": 50},
)
```
  </Tab>
  <Tab title="TypeScript">
```typescript
const result = await client.runs.wait(thread.thread_id, assistant.assistant_id, {
  input: { messages: [{ role: "user", content: "What module is this?" }] },
  context: { module_id: "module-1", store_namespace: "jane@example_com" },
  config: { recursion_limit: 50 },
});
```
  </Tab>
</Tabs>

Behind the scenes:

```text
client.runs.wait(thread_id, assistant_id, input=...)
                                                   ↓ HTTP POST /runs
                                       API server enqueues a run
                                                   ↓
                                       Queue worker picks it up
                                                   ↓
                                       Worker calls graph.invoke(input, config) ← invoke happens HERE
                                                   ↓
                                       Returns result via HTTP / SSE
```

The invoke still happens — just inside a queue worker on the server, after the API server hands the run off to the queue. See the [run execution lifecycle docs](https://docs.langchain.com/langsmith/agent-server#run-execution-lifecycle) for the full lifecycle.

---

## Recap

- Local execution is in-process: `graph.invoke(input, context=..., config=...)`.
- Deployed execution is over HTTP: `client.runs.wait(thread_id, assistant_id, input=input)`.
- The invoke still happens — just inside a queue worker on the server, hidden behind the run abstraction.
- **Context** (typed runtime values) lives on the assistant. **`thread_id`** identifies the conversation. **`config`** carries LangGraph runtime knobs like `recursion_limit`. **`input`** is the per-run payload.
