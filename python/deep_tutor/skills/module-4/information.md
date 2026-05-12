# Module 4 — Reference Material

## Three memory mechanisms

A LangGraph deployment ships with three storage primitives. Each has a different scope, persistence model, and intended use.

| Storage | Scope | Persists? | Who reads/writes | Typical content |
|---|---|---|---|---|
| **Checkpointer** | Per-thread | Yes (Postgres) | LangGraph automatically | Conversation state, message history |
| **Store** | Per-deployment, namespaced | Yes (Postgres) | Your code (via SDK or `runtime.store`) | Profiles, settings, cross-thread data |
| **Filesystem** | Per-container image | No (rebuilt on deploy) | Read at runtime, written at build time | Static content: skills, AGENTS.md |

## Checkpointer

The checkpointer is wired in by LangGraph. Each run reads the prior thread state, runs the graph, writes the new state — all automatic. The student does not call a checkpointer API directly. The `thread_id` they passed to `runs.wait` / `runs.stream` is the key.

## Store

The Store is a key-value store keyed by `(namespace, key)` where `namespace` is a tuple. It is per-deployment (not per-thread) and persists across redeploys.

### SDK access

```python
await client.store.put_item(("jane@example_com",), key="profile", value={"name": "Jane", "goals": "..."})
item = await client.store.get_item(("jane@example_com",), key="profile")
items = await client.store.search_items(("jane@example_com",), query="...")
await client.store.delete_item(("jane@example_com",), key="profile")
namespaces = await client.store.list_namespaces()
```

`.` is a reserved namespace separator in the SDK — encode emails as `jane@example_com`, not `jane@example.com`. See `email_to_namespace()` in `deep_tutor/ui/app.py`.

### Direct access inside a graph node

When the agent is running, the Store is injected directly — no HTTP, no SDK:

```python
@dynamic_prompt
def tutor_prompt(request: ModelRequest) -> str:
    if request.runtime.store:
        item = request.runtime.store.get((store_namespace,), key="profile")
        if item is not None:
            profile = item.value
```

This is what `deep_tutor`'s dynamic prompt does on every model call — it reads the profile fresh each turn so updates take effect immediately.

## Filesystem

The filesystem inside a deployed container is the image filesystem. It is built once at deploy time and reset on every redeploy. Writes during a run are not durable across containers.

Suitable for:
- Static content the agent reads at runtime (`skills/`, `AGENTS.md`)
- Lookup data baked in at build time

Not suitable for:
- Anything the agent writes that needs to persist
- Per-user state — use the Store instead

## deepagents Backend Protocol

`deepagents` defines a `BackendProtocol` — a file-system-like interface implemented by every backend. Same methods, different storage substrate:

```python
class BackendProtocol(Protocol):
    def ls(self, path: str) -> list[str]: ...
    def read(self, path: str) -> str: ...
    def write(self, path: str, content: str) -> None: ...
    def download_files(self, paths: list[str]) -> dict[str, str]: ...
```

### Three shipped backends

| Backend | Underlying storage | Scope | Survives redeploy |
|---|---|---|---|
| `FilesystemBackend` | Local filesystem | Container | No — baked into image |
| `StoreBackend` | LangGraph Store | Deployment-wide | Yes |
| `StateBackend` | Checkpointer / agent state | Thread | Yes (within thread) |

Middleware (e.g., `SkillsMiddleware`, `MemoryMiddleware`) calls `BackendProtocol` methods without knowing which backend is in use. Swapping backends changes where data lives, not how it's accessed.

## How `create_deep_agent` uses the backend

`deep_tutor` uses `FilesystemBackend` rooted at the project directory:

```python
backend = FilesystemBackend(
    root_dir=Path(__file__).parent.parent,
    virtual_mode=True,
)

graph = create_deep_agent(
    model=model,
    tools=[*mcp_tools],
    middleware=[tutor_prompt],
    backend=backend,
    memory=["/AGENTS.md"],
    skills=["/skills/"],
    permissions=[
        FilesystemPermission(operations=["write"], paths=["/skills/**"], mode="deny"),
    ],
    context_schema=ContextSchema,
)
```

`virtual_mode=True` anchors all paths to `root_dir`, so `/skills/` maps to `deep_tutor/skills/` on disk. The `FilesystemPermission` denies writes to skills at runtime.

## MemoryMiddleware (the `memory=` arg)

`MemoryMiddleware` reads each file in `memory=` and includes its content in every system prompt. `/AGENTS.md` (the tutor's persona and teaching guidelines) reaches every model call this way. Loaded once per thread, reused on every turn.

## SkillsMiddleware (the `skills=` arg)

`SkillsMiddleware` calls `backend.ls(source_path)` to list skill directories, then `backend.download_files(paths)` to fetch each `SKILL.md`. Only skill names and descriptions are injected into the system prompt — the full body is read on demand by the agent via the `read_file` tool. This is "progressive disclosure": the model knows skills exist without paying the token cost upfront.

When the tutor needs Module 2 content, the dynamic prompt instructs it to `read_file('/skills/module-2/SKILL.md')`. That tool call resolves through the backend.

## Why per-thread filesystem writes break

A LangGraph deployment can run a single thread across multiple worker containers — one run on container A, the next on container B. Each container has its own filesystem. A write on container A is invisible to container B. For persistence across containers, use the Store or the checkpointer.

## Reading the profile in `deep_tutor` — putting it together

| When | What | Where |
|---|---|---|
| Student registers | UI writes `profile` to Store via SDK | `python/deep_tutor/ui/app.py` `register()` |
| Student logs in | UI reads `profile` and `sessions` back | `python/deep_tutor/ui/app.py` `login()` |
| Each model call | Agent reads `profile` from Store | `tutor_prompt` in `agent/agent.py` |
| Each turn | Agent reads `/AGENTS.md` (cached by middleware) | `MemoryMiddleware` |
| Module switch | Agent reads `/skills/module-N/SKILL.md` on demand | `read_file` tool, resolved by `FilesystemBackend` |

The Store carries cross-session state, the filesystem carries static content, the checkpointer carries per-thread message history. Each in its proper lane.
