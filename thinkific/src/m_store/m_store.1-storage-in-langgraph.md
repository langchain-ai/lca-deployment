# Memory in LangGraph Deployments

LangGraph describes short and long-term memory. Langgraph uses short-term memory to store a thread's state after each superstep. This is referred to as the checkpoint memory. Long-term memory can be read and written by all threads and is referred to as a store. There is a third type of storage available, evident in deployment. The container file system is also available. 

This lesson describes these options and related deployment considerations.

---

## The Three Storage Options

| Storage | Storage Scope | Lifetime | On Node Failure | On Redeployment |
|---|---|---|---|---|
| **Checkpointer** | Deployment-wide | Thread | Writes rolled back; step retries from last checkpoint | Preserved — DB is scoped to the deployment, survives image updates |
| **LangGraph Store** | Deployment-wide | Deployment | Writes survive; retry may write again — idempotency required | Preserved — DB is scoped to the deployment, survives image updates |
| **Local filesystem** | Container-local | Image | Read-only; nothing to roll back | Replaced — new image brings new files; runtime writes lost |

### Checkpointer

After every superstep, LangGraph writes the current state to the checkpoint database. This is what makes runs durable: if a worker crashes mid-run, the next worker picks up from the last checkpoint rather than starting over.

The checkpointer storage scope is deployment-wide. All containers in the deployment access the same checkpointer. 

A thread sees only its own checkpoints. It accumulates the full message history and state for that thread. Those checkpoints persist as long as the thread exists. A new thread starts fresh.

The checkpointer provides durable compute. If execution were to fail, for example, a container failed, the checkpointer can be used to restore the thread on another container and pick up execution at the start of the last node.

When redeploying, the checkpointer is preserved so the existing threads maintain their state.

### Store

The Store is long-term memory that persists across threads. It is a key-value store where each item is identified by a namespace tuple and a key. Unlike the checkpointer, it is not tied to any thread — a write from one thread is immediately visible to all other threads.

The store scope is deployment-wide. All containers in the deployment access the same store.

On failure, completed writes persist and are available when the graph is restored. Because nodes restart execution at the beginning of the failed node, any writes prior to the failure will be repeated, so idempotent design is important.

The Store survives redeployment. It lives in the same Postgres database as the rest of the deployment, scoped to the deployment name. 

You can write to the Store from outside the agent (via the SDK) or from inside a graph node.

### Local Filesystem

Every deployment runs in a Docker container. The container has a local filesystem — files baked into the image are available at their expected paths. The agent can read them with plain file I/O.

Files baked into the image are replaced with new files on redeployment, since the new image includes its own copy. The files may be identical. But any writes the agent makes at runtime — files created or modified during a run — are lost when the container is replaced. 

Updating filesystem content requires building and deploying a new image.

---

## How You Access Each Storage

There are two access patterns: from outside the deployment via the SDK client, and from inside a graph node.

| Storage | SDK client | Graph node |
|---|---|---|
| **Checkpointer** | access thread state and history | Automatic — state injected by LangGraph, no direct calls |
| **Store** | Read + write (`put_item`, `get_item`, `search_items`) | Read + write (`store.put`, `store.get`, `store.search`) |
| **Local filesystem** | Not accessible | Read + write — plain Python file I/O |

The SDK client connects over HTTP and requires authentication (a LangSmith API key, or a user token when auth is enabled). 

Inside a graph node, the store is injected directly as a Python object — no HTTP, no authentication. The node is already inside the trust boundary of the deployment.

---

## Check your understanding

<MCQ
    question="You write a value to the Store inside a graph node. The node then fails. What happens to the write?"
    choices='["It is rolled back — the Store reverts to the previous value", "It survives — the write is already in Postgres", "It depends on whether the deployment uses Postgres or Redis", "It is lost with the container"]'
    correctIndex={1}
    explanation="Store writes are immediate and not transactional with node execution. The write survives the failure. On retry, the node may write again — which is why idempotent design matters."
/>

<MCQ
    question="A student is mid-conversation on thread A. You deploy a new image. What happens to their thread state?"
    choices='["Lost — the checkpointer is tied to the image", "Preserved — the checkpointer database survives redeployment", "Preserved, but only if the student sends a new message first", "Depends on whether the graph schema changed"]'
    correctIndex={1}
    explanation="The checkpointer lives in Postgres, scoped to the deployment name — not the image. Redeploying replaces the image but leaves the database untouched."
/>

<MCQ
    question="Which storage type is NOT accessible from the SDK client running outside the deployment?"
    choices='["Checkpointer", "Store", "Local filesystem", "All three are accessible"]'
    correctIndex={2}
    explanation="The local filesystem is inside the container. The SDK client connects over HTTP and has no path to it. The Store and Checkpointer are both reachable via the SDK."
/>

<MCQ
    question="You want to update a skill file so all students see the change immediately, without redeploying. Which storage type supports this?"
    choices='["Local filesystem — edit the file in place", "Checkpointer — update the thread state directly", "Store — write the new content via the SDK", "None — a redeploy is always required"]'
    correctIndex={2}
    explanation="The Store is the only option. It is writable from outside the deployment via the SDK, and the change is visible to all threads immediately. The filesystem requires a redeploy; the checkpointer is read-only from the SDK."
/>

---

## What's Next

- **L2** — An exercise using all three storage types. Two files: a client script and a simple agent. The client loads entries into the Store from a file, reads them back, updates a value. The agent updates a Store entry during a run. The client reads again to see the change.
- **L3** — deepagents backends. How `FilesystemBackend`, `StoreBackend`, and `StateBackend` map to the LangGraph primitives. How `deep_tutor` is currently configured and why the filesystem backend makes skill updates impossible.
- **L4** — The fix. Swap `deep_tutor` to `StoreBackend`, seed the Store with the existing skills, and add a cron graph that checks a git repository for updates and reloads changed files — live updates with no redeploy required.
