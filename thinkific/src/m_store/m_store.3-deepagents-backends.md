# Memory in the Tutor

Now that you have used the SDK to access memory, let's take a look at how the tutor and the deepagents library use memory.

The tutor uses all three of the memory types that were discussed:

| Storage | What it holds | Who writes it | Who reads it |
|---|---|---|---|
| **Checkpointer** | Conversation state per thread | LangGraph automatically | LangGraph automatically |
| **Store** | Student profile (name, email, goals) | UI on register/login | Agent on every model call |
| **Local filesystem** | Lesson content (skills) | Image build | Agent via deepagents backend |


This lesson covers the Store and filesystem in more detail. The checkpointer runs automatically — there is nothing to configure.

---

## The Store: Student Profile
The store provides read/write access to a database that persists over time and across different containers.  This allows users to logout/in and maintain their account status information.

### Writing the profile

When a student registers, the UI calls `POST /register`. The server writes the profile to the Store before creating any sessions.

<!-- block: m_store.3-register-python-code -->
```python
# python/deep_tutor/ui/app.py
@app.post("/register")
async def register(request: Request, req: RegisterRequest):
    namespace = email_to_namespace(req.email)

    await client.store.put_item(
        (namespace,),
        key="profile",
        value={
            "first_name": req.first_name,
            "last_name": req.last_name,
            "email": req.email,
            "goals": req.goals,
        },
    )
    sessions = await create_student_sessions(client, ..., namespace=namespace)
    await client.store.put_item(
        (namespace,),
        key="sessions",
        value={"sessions": sessions},
    )
    return {"sessions": sessions, "profile": ...}
```
<!-- /block: m_store.3-register-python-code -->

The namespace is the student's email with `.` replaced by `_` — for example, `jane@example.com` becomes `("jane@example_com",)`. The LangGraph SDK uses `.` as a namespace separator internally, so periods in labels are not allowed.

On login, the server reads both items back and returns them to the UI, which restores the session without creating new assistants or threads.

### Reading the profile in the agent

The agent reads the profile from the Store at the start of every model call, inside the dynamic prompt. This ensures the agent always has the latest data — even if the student updated their goals since their last session.

<!-- block: m_store.3-prompt-python-code -->
```python
# python/deep_tutor/agent/agent.py
@dynamic_prompt
def tutor_prompt(request: ModelRequest) -> str:
    module_id = request.runtime.context.module_id
    student_name = request.runtime.context.student_name
    store_namespace = request.runtime.context.store_namespace
    goals = request.runtime.context.goals

    if store_namespace and request.runtime.store:
        item = request.runtime.store.get((store_namespace,), key="profile")
        if item is not None:
            profile = item.value
            student_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or student_name
            goals = profile.get("goals", goals)

    goals_line = f"\n\nThe student's goals: {goals}" if goals else ""
    return (
        f"You are a tutor agent. Your student's name is {student_name}. "
        f"They are working on {module_id}.{goals_line}\n\n"
        f"On your first response, read the SKILL.md for {module_id} from /skills/{module_id}/SKILL.md. "
        f"That file contains your teaching instructions — follow them. "
        f"When you need to answer a factual question, read /skills/{module_id}/information.md."
    )
```
<!-- /block: m_store.3-prompt-python-code -->

`store_namespace` is the only field that must come from context — it is the key needed to find the student's data. Everything else (name, goals) comes from the Store.

`request.runtime.store` is the LangGraph Store injected directly into the graph at runtime — no HTTP. The agent is already inside the trust boundary of the deployment.

Notice how the skills are used to gather information about a particular module. Skills are a feature that is built into the deepagent library. They are based on files.

---

## The Filesystem: Lesson Content

Lesson content is stored as skills — directories of markdown files baked into the Docker image at `deep_tutor/skills/`. The agent reads them via the deepagents backend abstraction.

### The backend abstraction

deepagents defines a `BackendProtocol` — a file-system-like interface (`ls`, `read`, `write`, `download_files`, etc.) that every backend implements. Three backends ship with deepagents:

| Backend | LangGraph primitive | Scope | Survives redeployment |
|---|---|---|---|
| `FilesystemBackend` | Local filesystem | Container | No — baked into the image |
| `StoreBackend` | LangGraph Store | Deployment-wide | Yes |
| `StateBackend` | Checkpointer / agent state | Thread | Yes (within thread) |

The rest of the framework calls backend methods without knowing which backend is in use. Swapping backends changes where data is stored — not how the framework accesses it.

It's important to note the scope and the redeployment behavior. The file system is a convenient place to store data, but a thread may exist across multiple containers during its lifetime, so using the local file system for writes is problematic. Read-only data available when the image is created works well. Note that it could change during a redeploy when new images are uploaded if the redeploy updates files.

### How deep_tutor loads skills

`create_deep_agent` sets up a `SkillsMiddleware` internally. Before each model call, it calls `backend.ls(source_path)` to list skill directories, then `backend.download_files(paths)` to fetch each `SKILL.md`. The skill names and descriptions are injected into the system prompt.

`deep_tutor` uses `FilesystemBackend` pointed at the `skills/` directory baked into the image:

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

`virtual_mode=True` anchors all paths to `root_dir`, so `/skills/` maps to `deep_tutor/skills/` on disk. The `FilesystemPermission` denies writes — the agent can read skills but cannot modify them at runtime.

You can find more details on the deepagents file system [here](https://docs.langchain.com/oss/python/deepagents/backends).

---

## Check your understanding

<MCQ
    question="The agent reads the student's goals from the Store on every model call. What is the minimum information that must come from context instead?"
    choices='["Nothing — the agent could find any student by searching the Store", "The store_namespace — needed to know which Store entry belongs to this student", "The student_name — used as a fallback if the Store read fails", "The module_id — determines which skills to load"]'
    correctIndex={1}
    explanation="store_namespace is the key to the student's data. Without it, the agent has no way to look up the right profile. Everything else — name, goals — can come from the Store once the namespace is known."
/>

<MCQ
    question="A student updates their goals and logs in again. The agent reads the profile from the Store. Does it see the updated goals?"
    choices='["No — the assistant context was set at registration and is not updated", "Yes — the Store read happens at prompt time and always returns the latest value", "Only if the student starts a new thread", "Depends on whether the Store was written before or after the session was created"]'
    correctIndex={1}
    explanation="The dynamic prompt reads from the Store on every model call. The Store always returns the current value — it does not cache the value from when the session was created."
/>

<MCQ
    question="SkillsMiddleware is reconfigured to use StoreBackend instead of FilesystemBackend. Which method calls change?"
    choices='["ls() and download_files() are replaced with store-specific calls", "None — SkillsMiddleware calls the same BackendProtocol methods regardless of backend", "The middleware bypasses the backend and reads from the Store directly", "The sources= paths must be updated to use store namespaces"]'
    correctIndex={1}
    explanation="SkillsMiddleware only calls ls() and download_files() from BackendProtocol. Swapping the backend changes where those calls go — not how the middleware works."
/>
