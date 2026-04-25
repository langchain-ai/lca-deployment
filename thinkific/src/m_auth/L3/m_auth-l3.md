# Authentication and Authorization: Lesson 3 — Private Conversations

In Lesson 2 you added `@auth.authenticate`, which confirms who each user is. But authentication alone does not restrict what users can see — Alice and Bob can still read each other's threads. In this lesson you will add authorization: `@auth.on` handlers that stamp each resource with its owner on creation and filter by that owner on every read.

By the end of this lesson, each user will have completely private conversations — threads created by Alice are invisible to Bob, and vice versa.

<style>@import url('../../shared/sd-components.css');</style>
<script src="../../shared/sd-components.js"></script>

<div class="sd-wrap" id="sd-authz-create"></div>

<div class="sd-wrap" id="sd-authz-read"></div>

---

## How @auth.on works

An `@auth.on` handler runs after `@auth.authenticate` succeeds and receives two arguments:

- **`ctx`** (`AuthContext`) — the verified user, their permissions, the resource name (`"threads"`, `"runs"`, etc.), and the action (`"create"`, `"read"`, `"update"`, `"delete"`, `"search"`, `"create_run"`).
- **`value`** (`dict`) — the data being created or accessed. Its exact shape depends on the resource and action.

The handler does two jobs:
1. **On writes**: adds metadata to the resource before it is stored, so ownership is persisted in the database.
2. **Returns a filter dict**: LangGraph applies this as a key-value query against the `metadata` column so users only see matching records.

---

## Step 1: Add an @auth.on handler

Open `agent/auth.py` and add the following handler below `@auth.authenticate`. Nothing else in the file changes:

```python
@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict):
    """Stamp owner on creation; filter by owner on every read."""
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    return filters
```

A single broad `@auth.on` handler applies to **every resource type and every action**. It:
- Adds `"owner": <identity>` to the resource's `metadata` dict (written to the database with the record).
- Returns `{"owner": <identity>}` as a filter, so every read is automatically scoped to resources owned by the current user.

---

## Step 2: Test private conversations

Restart the server and run the following code:

```python
from langgraph_sdk import get_client

alice = get_client(
    url="http://localhost:2024",
    headers={"Authorization": "Bearer alice-token"}
)
bob = get_client(
    url="http://localhost:2024",
    headers={"Authorization": "Bearer bob-token"}
)

# Alice creates a thread
alice_thread = await alice.threads.create()
print(f"Alice created: {alice_thread['thread_id']}")

# Bob tries to access Alice's thread — should be blocked
try:
    await bob.threads.get(alice_thread["thread_id"])
    print("Bob should not see this!")
except Exception as e:
    print("Bob correctly denied:", e)

# Each user lists only their own threads
alice_threads = await alice.threads.search()
bob_threads = await bob.threads.search()
print(f"Alice sees {len(alice_threads)} thread(s)")   # 1
print(f"Bob sees {len(bob_threads)} thread(s)")       # 0
```

<Tip>
**Why does Bob get a 404 instead of a 403?**

When the filter `{owner: "user2"}` is applied to the query, Alice's thread simply does not appear in the results. From the server perspective there is nothing to deny — the thread does not exist for Bob. This is intentional: a 403 would confirm that the resource exists, which leaks information. A 404 reveals nothing.
</Tip>

---

## Scoped handlers

A single `@auth.on` handler is concise, but it applies the same logic to every resource and action. If you need different rules for different situations — or want a typed `value` dict — use scoped handlers:

```python
@auth.on.threads.create
async def on_thread_create(ctx: Auth.types.AuthContext, value: Auth.types.on.threads.create.value):
    """Stamp owner when a thread is created."""
    metadata = value.setdefault("metadata", {})
    metadata["owner"] = ctx.user.identity
    return {"owner": ctx.user.identity}

@auth.on.threads.read
async def on_thread_read(ctx: Auth.types.AuthContext, value: Auth.types.on.threads.read.value):
    """Filter threads to this user on reads."""
    return {"owner": ctx.user.identity}
```

The most specific handler wins. If both `@auth.on` and `@auth.on.threads.create` are defined, the scoped handler runs for thread creation and the broad handler covers everything else.

You can also block entire resource types outright:

```python
@auth.on.assistants
async def on_assistants(ctx, value):
    raise Auth.exceptions.HTTPException(status_code=403, detail="Not permitted")
```

---

## The full auth.py at this point

```python
from langgraph_sdk import Auth

VALID_TOKENS = {
    "alice-token": {"id": "user1", "name": "Alice"},
    "bob-token":   {"id": "user2", "name": "Bob"},
}

auth = Auth()

@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    if not authorization:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Missing token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token not in VALID_TOKENS:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid token")
    return {"identity": VALID_TOKENS[token]["id"]}

@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict):
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    return filters
```

---

## What you learned in this lesson

- **`@auth.on`** — runs after authentication on every resource access. Stamps `metadata` on writes and returns a filter dict on reads. A single broad handler covers all resources and actions.
- **`ctx.user.identity`** — the unique identifier returned by `@auth.authenticate`. This is the anchor that ties resources to their owner.
- **Filter application** — the returned dict is applied as a generic key-value query against the `metadata` column. Users only see records where the filter matches.
- **404 vs 403** — filtered-out resources return 404 to avoid confirming that the resource exists.
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
    explanation="@auth.on stamps metadata onto resources being written so ownership persists in the database, and returns a filter dict that LangGraph applies to scope subsequent reads to the current user."
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
    explanation="ctx.user.identity is the identity field from the dict returned by @auth.authenticate. It is guaranteed to be present because identity is the one required field in MinimalUserDict."
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
    participants: ['Alice', 'Agent Server', 'Database'],
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
      { tag: 'Step 3 of 5', caption: 'The Agent Server writes the thread to the database, including the metadata that records Alice as owner.' },
      { tag: 'Step 4 of 5', caption: 'The database confirms the thread is stored.' },
      { tag: 'Step 5 of 5', caption: 'The thread ID is returned to Alice. The owner metadata is now persisted — it will be used to filter reads.' },
    ]
});

buildDiagram({
    id: 'sd-authz-read',
    participants: ['Bob', 'Agent Server', 'Database'],
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
      { tag: 'Step 2 of 5', caption: '@auth.authenticate confirms Bob is user2. @auth.on returns the filter {owner: "user2"} — this is applied to the database query automatically.' },
      { tag: 'Step 3 of 5', caption: 'The Agent Server queries the database with the filter applied: only threads where metadata.owner equals "user2" are returned.' },
      { tag: 'Step 4 of 5', caption: 'Alice\'s thread has owner: "user1" in its metadata. It does not match the filter, so no record is returned.' },
      { tag: 'Step 5 of 5', caption: 'The Agent Server returns 404 — not 403. From the server\'s perspective, there is no matching thread for Bob to be forbidden from.' },
    ]
});
</script>
