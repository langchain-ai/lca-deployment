# Authentication and Authorization: Lesson 3 — Private Conversations

In the previous lesson you added `@auth.authenticate`, which confirms who each user is. But authentication alone does not restrict what users can see — Alice and Bob can still read each other's threads. In this lesson you will add authorization: `@auth.on` handlers that stamp each resource with its owner on creation and filter by that owner on every read.

By the end of this lesson, each user will have completely private conversations — threads created by Alice are invisible to Bob, and vice versa.

<style>@import url('../../shared/sd-components.css');</style>
<script src="../../shared/sd-components.js"></script>

**Creating a thread — ownership is stamped at write time**

<div class="sd-wrap" id="sd-authz-create"></div>

**Reading a thread — the filter makes Alice's thread invisible to Bob**

<div class="sd-wrap" id="sd-authz-read"></div>

---

## How @auth.on works

Every API operation that touches a resource — `threads.create()`, `threads.get()`, `threads.search()`, `runs.create()`, and so on — passes through `@auth.on`. It fires after `@auth.authenticate` confirms who the user is, and before the resource database read or write happens:

1. Request arrives
2. `@auth.authenticate` — who is this?
3. `@auth.on` — what can they do with this resource?
4. Resource database operation executes (with stamped metadata on writes, or a filter applied on reads)

The handler receives two arguments:

- **`ctx`** (`AuthContext`) — three attributes:
    - `ctx.user` — an object built from the dict you returned in `@auth.authenticate`. Each key becomes an attribute: `ctx.user.identity` is always present; `ctx.user.name` or `ctx.user.role` are available if you included them.
    - `ctx.resource` — string identifying the resource type: `"threads"`, `"runs"`, `"assistants"`, etc.
    - `ctx.action` — string identifying the operation: `"create"`, `"read"`, `"update"`, `"delete"`, `"search"`, or `"create_run"`. See [Supported actions and types](https://docs.langchain.com/langsmith/auth#supported-actions-and-types) for the full list of valid resource/action combinations.
- **`value`** (`dict`) — the live request payload for the operation. Its shape depends entirely on the resource and action. Full type definitions: [Python `types.py`](https://github.com/langchain-ai/langgraph/blob/main/libs/sdk-py/langgraph_sdk/auth/types.py) · [TypeScript `types.ts`](https://github.com/langchain-ai/langgraphjs/blob/main/libs/sdk/src/auth/types.ts).

For example, on `threads.create`, `value` looks like:

```python
{
    "thread_id": UUID("99b045bc-..."),
    "metadata": {},
    "if_exists": "raise"
}
```

You can read any field to make authorization decisions. The one documented mutation point is `value["metadata"]` — anything you write there is persisted with the resource on write operations.

The handler always returns a filter dict, but its effect differs by operation:
1. **On writes**: mutating `value["metadata"]` is what does the work — ownership is stamped on the resource before it is stored. The returned filter scopes what is accessible after the write.
2. **On reads**: the returned filter is what does the work — LangGraph applies it as a key-value query against the `metadata` column so users only see matching records. Mutating `value["metadata"]` is a no-op since nothing is stored.

---

## Project structure

There are three lab directories for this lesson:

```
python/m_auth/
├── l3a/                    ← Lab 1: broad handler, Alice and Bob
│   ├── agent/
│   │   ├── __init__.py
│   │   └── graph.py        ← same echo agent as the previous lesson
│   ├── auth.py
│   ├── client.py
│   ├── .env
│   ├── .env.example
│   ├── langgraph.json
│   └── pyproject.toml
├── l3b/                    ← Lab 2: scoped handlers, Alice, Bob, and admin
└── l3c/                    ← Lab 3: store authorization
```

---

## Lab 3a: Private conversations

`auth.py` in `python/m_auth/l3a/` — add the following handler below `@auth.authenticate`:

```python
@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict):
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)  # updates value["metadata"]
    return filters
```

A single broad `@auth.on` applies to every resource and action. It stamps `"owner": <identity>` into `metadata` on writes and returns the same dict as a filter so reads are automatically scoped to the current user.

Start the server:

```bash
cd python/m_auth/l3a
uv run langgraph dev --no-browser
```

<Tip>
**Starting fresh**

The server stores state in a `.langgraph_api` directory. If you run the client multiple times, thread counts will accumulate. To reset:

```bash
rm -rf .langgraph_api && uv run langgraph dev --no-browser
```
</Tip>

Run the client in a second terminal:

```bash
uv run python client.py
```

Expected output:

```
✅ Alice created thread: 019dc647-e8b8-7751-8689-4f2faae4347b
✅ Bob correctly blocked: 404 — Thread with ID 019dc647-... not found
✅ Alice sees 1 thread(s)
✅ Bob sees 0 thread(s)
```

<Tip>
**Why does Bob get a 404 instead of a 403?**

When the filter `{owner: "user2"}` is applied to the query, Alice's thread simply does not appear in the results. From the server perspective there is nothing to deny — the thread does not exist for Bob. This is intentional: a 403 would confirm that the resource exists, which leaks information. A 404 reveals nothing.
</Tip>

---

## Lab 3b: Admin access with scoped handlers

The broad `@auth.on` handles Alice and Bob, but it has one limitation: it always returns the same filter regardless of who is asking. An admin who needs to see all threads cannot be accommodated — the handler has no way to return `{}` for admin and `{"owner": identity}` for everyone else, because it runs identically for every action.

Scoped handlers fix this. Each targets a specific resource + action, so you can vary the filter by user.

`auth.py` in `python/m_auth/l3b/` uses three scoped handlers and adds `"admin-token"` to `VALID_TOKENS`:

```python
VALID_TOKENS = {
    "alice-token": {"id": "user1", "name": "Alice"},
    "bob-token":   {"id": "user2", "name": "Bob"},
    "admin-token": {"id": "admin", "name": "Admin"},
}

@auth.on.threads.create
async def on_thread_create(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.create.value,
):
    metadata = value.setdefault("metadata", {})
    metadata["owner"] = ctx.user.identity  # updates value["metadata"]["owner"]
    return {"owner": ctx.user.identity}

@auth.on.threads.read
async def on_thread_read(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.read.value,
):
    if ctx.user.identity == "admin":
        return {}
    return {"owner": ctx.user.identity}

@auth.on.threads.search
async def on_thread_search(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.search.value,
):
    if ctx.user.identity == "admin":
        return {}
    return {"owner": ctx.user.identity}
```

`on_thread_create` stamps ownership as before, but with typed `value` — your IDE knows the field names.

`on_thread_read` and `on_thread_search` return `{}` for admin (no filter = sees everything) and the owner filter for everyone else.

<Tip>
**The most specific handler wins**

If both `@auth.on` and `@auth.on.threads.create` are defined, the scoped handler runs for thread creation and the broad handler covers everything else. You can mix broad and scoped handlers in the same `auth.py`.
</Tip>

Start the server:

```bash
cd python/m_auth/l3b
uv run langgraph dev --no-browser
```

Run the client:

```bash
uv run python client.py
```

Expected output:

```
✅ Alice created thread: 019dc647-...
✅ Bob created thread: 019dc648-...
✅ Bob correctly blocked: 404 — Thread with ID 019dc647-... not found
✅ Alice sees 1 thread(s)
✅ Bob sees 1 thread(s)
✅ Admin sees 2 thread(s)
```

---

## Lab 3c: Store authorization

The store is a key-value store built into LangGraph. Items are addressed by a `namespace` tuple you control. Unlike threads, LangGraph does not automatically apply a returned filter dict to store queries — there is no built-in scoping mechanism. The handler receives the full request context and can allow or block access however it chooses. In this example it checks the namespace and raises if the caller does not own it.

`auth.py` in `python/m_auth/l3c/`:

```python
@auth.on.store()
async def on_store(ctx: Auth.types.AuthContext, value: dict):
    if ctx.user.identity == "admin":
        return
    namespace: tuple = value["namespace"]
    assert namespace[0] == ctx.user.identity, "Not authorized"
```

The handler returns nothing — `return` (or `return None`) means allow, `assert` raises an `AssertionError` to block. Admin bypasses the check entirely and can access any namespace.

The convention is to put the caller's identity as the first element of the namespace: `["user1", "notes"]` for Alice, `["user2", "notes"]` for Bob. The handler checks only that first element.

<Tip>
**Store uses assert, not a filter dict**

For threads and runs, LangGraph automatically applies the returned filter dict as a query constraint. For the store, no such mechanism exists — the namespace tuple is the natural access boundary. The handler's job is to allow or block access directly, not to scope a query.
</Tip>

Start the server:

```bash
cd python/m_auth/l3c
uv run langgraph dev --no-browser
```

Run the client:

```bash
uv run python client.py
```

Expected output:

```
✅ Alice stored a note
✅ Bob correctly blocked: ...
✅ Alice reads her note: Alice's private note
✅ Bob stored a note
✅ Admin reads Alice's note: Alice's private note
✅ Admin reads Bob's note: Bob's private note
```

---

## What you learned in this lesson

- **`@auth.on`** — runs after authentication on every resource access. Stamps `metadata` on writes and returns a filter dict on reads. A single broad handler covers all resources and actions.
- **`ctx.user.identity`** — the unique identifier returned by `@auth.authenticate`. This is the anchor that ties resources to their owner.
- **Filter application** — the returned dict is applied as a generic key-value query against the `metadata` column. Users only see records where the filter matches.
- **Scoped handlers** — `@auth.on.threads.create` and `@auth.on.threads.read` give per-action control and typed `value` dicts. The most specific handler wins.

---

## Up next

In the next lesson you will replace the hardcoded `VALID_TOKENS` dict with real user accounts via an identity provider. The `@auth.on` handlers you wrote here stay exactly as-is — only `@auth.authenticate` changes, swapping the dict lookup for a JWT validation call.

---

## Check your understanding

<MCQ
    question="What two things does an @auth.on handler do?"
    choices='["Validates the token and returns the user", "Stamps metadata on the resource and returns a filter dict", "Raises a 401 and logs the request", "Reads the database and returns all resources"]'
    correctIndex={1}
    explanation="@auth.on stamps metadata onto resources being written so ownership persists in the resource database, and returns a filter dict that LangGraph applies to scope subsequent reads to the current user."
/>

<MCQ
    question="Why does Bob get a 404 when trying to read Alice's thread?"
    choices='["LangGraph has a bug in its 403 handling", "The filter makes the thread invisible to Bob — it does not exist from his perspective", "Alice deleted the thread before Bob read it", "Bob does not have a valid token"]'
    correctIndex={1}
    explanation="The filter {owner: bob} is applied to the query. Alice's thread has owner: alice in its metadata so it does not match and is not returned. From the server perspective there is nothing to forbid — the thread simply does not exist for Bob. This also avoids leaking that the resource exists."
/>

<MCQ
    question="What does ctx.user.identity contain inside an @auth.on handler?"
    choices='["The raw bearer token", "The unique identifier returned by @auth.authenticate", "The user email address", "The LangSmith API key"]'
    correctIndex={1}
    explanation="ctx.user.identity is the identity field from the dict returned by @auth.authenticate. It is guaranteed to be present because identity is the one required field in Auth.types.MinimalUserDict."
/>

<MCQ
    question="If both @auth.on and @auth.on.threads.create are defined, which handler runs on thread creation?"
    choices='["Both, in order from broadest to most specific", "@auth.on", "@auth.on.threads.create", "Neither — they conflict and both are skipped"]'
    correctIndex={2}
    explanation="The most specific handler wins. @auth.on.threads.create takes precedence over the global @auth.on for that exact resource and action. @auth.on continues to cover everything else."
/>

<MCQ
    question="To block all access to the assistants resource, what should your @auth.on.assistants handler do?"
    choices='["Return an empty dict", "Return None", "Raise an HTTPException with status 403", "Delete the Auth instance"]'
    correctIndex={2}
    explanation="Raising Auth.exceptions.HTTPException with status_code=403 immediately terminates the request with a Forbidden response. Returning an empty dict or None would allow the request to proceed."
/>

<MCQ
    question="In the next lesson, when you switch to JWT-based authentication, what needs to change in auth.py?"
    choices='["Only @auth.authenticate — @auth.on stays the same", "Only @auth.on — @auth.authenticate stays the same", "Both handlers must be rewritten", "The langgraph.json auth path must be removed"]'
    correctIndex={0}
    explanation="The authorization logic in @auth.on only cares about ctx.user.identity, which is provided by @auth.authenticate regardless of how the token is validated. Only @auth.authenticate changes when you switch from hardcoded tokens to real JWTs."
/>

<script>
buildDiagram({
    id: 'sd-authz-create',
    participants: ['Alice', 'Agent Server', 'Resource Database'],
    cx: [130, 500, 870],
    bw: 140, bh: 40, tby: 10, bby: 350, vw: 1000, vh: 400,
    buildSteps: function(a) {
      return [
        solidArrow(130, 500, 80, 'POST /threads   Bearer alice-token', 310, a),
        labelBox(500, 115, 290, ['@auth.authenticate → identity: "user1"', '@auth.on → stamp metadata[owner] = user1']),
        solidArrow(500, 870, 215, 'INSERT thread WITH metadata {owner: "user1"}', 690, a),
        dashedArrow(870, 500, 270, 'stored', 690, a),
        dashedArrow(500, 130, 310, 'thread_id returned', 310, a),
      ];
    },
    steps: [
      { tag: 'Step 1 of 5', caption: 'Alice sends a request to create a thread with her bearer token.' },
      { tag: 'Step 2 of 5', caption: '@auth.authenticate fires first and confirms Alice is user1. Then @auth.on fires and stamps the thread metadata with owner: "user1" before the thread is written.' },
      { tag: 'Step 3 of 5', caption: 'The Agent Server writes the thread to the resource database, including the metadata that records Alice as owner.' },
      { tag: 'Step 4 of 5', caption: 'The resource database confirms the thread is stored.' },
      { tag: 'Step 5 of 5', caption: 'The thread ID is returned to Alice. The owner metadata is now persisted — it will be used to filter reads.' },
    ]
});

buildDiagram({
    id: 'sd-authz-read',
    participants: ['Bob', 'Agent Server', 'Resource Database'],
    cx: [130, 500, 870],
    bw: 140, bh: 40, tby: 10, bby: 350, vw: 1000, vh: 400,
    buildSteps: function(a) {
      return [
        solidArrow(130, 500, 80, 'GET /threads/alice-thread-id   Bearer bob-token', 310, a),
        labelBox(500, 115, 290, ['@auth.authenticate → identity: "user2"', '@auth.on → return filter {owner: "user2"}']),
        solidArrow(500, 870, 215, 'SELECT WHERE metadata @> {owner: "user2"}', 690, a),
        dashedArrow(870, 500, 270, 'no matching record', 690, a),
        dashedArrow(500, 130, 310, '404 Not Found', 310, a),
      ];
    },
    steps: [
      { tag: 'Step 1 of 5', caption: 'Bob sends a request for Alice\'s thread using his own bearer token.' },
      { tag: 'Step 2 of 5', caption: '@auth.authenticate confirms Bob is user2. @auth.on returns the filter {owner: "user2"} — this is applied to the resource database query automatically.' },
      { tag: 'Step 3 of 5', caption: 'The Agent Server queries the resource database with the filter applied: only threads where metadata.owner equals "user2" are returned.' },
      { tag: 'Step 4 of 5', caption: 'Alice\'s thread has owner: "user1" in its metadata. It does not match the filter, so no record is returned.' },
      { tag: 'Step 5 of 5', caption: 'The Agent Server returns 404 — not 403. From the server\'s perspective, there is no matching thread for Bob to be forbidden from.' },
    ]
});
</script>
