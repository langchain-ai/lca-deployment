# deepagents Backends

deepagents builds on the three LangGraph storage primitives from L1. It wraps them behind a uniform interface — the backend — so the rest of the framework doesn't care where files are stored.

This lesson covers what the backend abstraction is, how `SkillsMiddleware` uses it, and how `deep_tutor` is currently configured.

---

## The Backend Abstraction

deepagents defines a `BackendProtocol` that every backend must implement. The protocol is a file-system-like interface: `ls`, `read`, `write`, `glob`, `grep`, `download_files`, `upload_files`.

Three backends ship with deepagents, each backed by a different LangGraph primitive:

| Backend | LangGraph primitive | Scope | Survives redeployment |
|---|---|---|---|
| `FilesystemBackend` | Local filesystem | Container | No — baked into the image |
| `StoreBackend` | LangGraph Store | Deployment-wide | Yes |
| `StateBackend` | Checkpointer / agent state | Thread | Yes (within thread) |

The rest of the framework — including `SkillsMiddleware` — calls backend methods without knowing which backend is in use. Swapping backends changes where data is stored, not how the framework accesses it.

---

## How SkillsMiddleware Uses a Backend

`SkillsMiddleware` loads skills from the backend before each model call. It takes a `backend` and a list of `sources` — paths in the backend where skills are organized.

Loading follows two steps:

**1. List** — `backend.ls(source_path)` returns the entries in the source directory. Each subdirectory is a candidate skill.

**2. Fetch** — `backend.download_files(paths)` retrieves the `SKILL.md` file from each skill directory.

The middleware then parses the YAML frontmatter in each `SKILL.md`, builds a skill listing, and injects skill names and descriptions into the system prompt.

Because the middleware only calls `backend.ls()` and `backend.download_files()`, it works identically with any backend. Swapping from `FilesystemBackend` to `StoreBackend` changes where skills are stored — the loading logic is unchanged.

---

## How deep_tutor Is Currently Configured

`deep_tutor` uses `FilesystemBackend` pointed at the `skills/` directory baked into the image.

<!-- block: m_store.3-agent-config-python-code -->
```python
# python/deep_tutor/agent/agent.py
backend = FilesystemBackend(
    root_dir=Path(__file__).parent.parent,
    virtual_mode=True,
)

graph = create_deep_agent(
    model=model,
    tools=[*mcp_tools],
    middleware=[tutor_prompt],
    backend=backend,
    skills=["/skills/"],
    permissions=[
        FilesystemPermission(operations=["write"], paths=["/skills/**"], mode="deny"),
    ],
    context_schema=ContextSchema,
)
```
<!-- /block: m_store.3-agent-config-python-code -->

`root_dir` is the `deep_tutor/` directory — one level above the `agent/` package. `virtual_mode=True` means all paths are virtual paths anchored to that root, so `/skills/` maps to `deep_tutor/skills/` on disk.

When `SkillsMiddleware` calls `backend.ls("/skills/")`, it reads that real directory. When it calls `backend.download_files(...)`, it reads actual files from the image.

The `FilesystemPermission` denies writes to `/skills/**` — the agent can read skills but cannot modify them at runtime.

---

## Check your understanding

<MCQ
    question="SkillsMiddleware is reconfigured to use StoreBackend instead of FilesystemBackend. Which method calls change?"
    choices='["ls() and download_files() are replaced with store-specific calls", "None — SkillsMiddleware calls the same BackendProtocol methods regardless of backend", "The middleware bypasses the backend and reads from the Store directly", "The sources= paths must be updated to use store namespaces"]'
    correctIndex={1}
    explanation="SkillsMiddleware only calls ls() and download_files() from BackendProtocol. Swapping the backend changes where those calls go — not how the middleware works."
/>

<MCQ
    question="deep_tutor uses FilesystemBackend with virtual_mode=True and root_dir pointing to deep_tutor/. What does the path /skills/ resolve to?"
    choices='["The absolute path /skills/ on the container", "deep_tutor/skills/ on disk", "The LangGraph Store namespace skills", "Depends on the container runtime environment"]'
    correctIndex={1}
    explanation="virtual_mode=True anchors all paths to root_dir. /skills/ is a virtual path relative to that root, so it resolves to deep_tutor/skills/ on the actual filesystem."
/>

<MCQ
    question="A student starts a new conversation thread. Skills are loaded from FilesystemBackend. Are the skills available in the new thread?"
    choices='["No — FilesystemBackend is thread-scoped and resets per thread", "Yes — FilesystemBackend reads files baked into the image, which are always present", "Only if the previous thread was checkpointed", "Depends on whether virtual_mode is enabled"]'
    correctIndex={1}
    explanation="FilesystemBackend reads from the container filesystem — files baked into the image. They are not tied to any thread. Every thread, new or existing, reads the same files."
/>
