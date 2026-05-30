# Module 5 — Reference Material

## Authentication vs authorization

Two questions, two handlers:

| Question | Handler | When it runs | What it returns |
|---|---|---|---|
| Who is this caller? | `@auth.authenticate` | Once per request, before anything else | `MinimalUserDict` or raises 401 |
| What can they do with this resource? | `@auth.on` (and scoped variants) | After authenticate, on every resource access | Filter dict (reads), stamp metadata (writes) |

Authentication establishes identity. Authorization scopes access. The two can be reasoned about, swapped, and tested independently — which is why m5.4 swaps the token store without touching `@auth.on`.

## `@auth.authenticate`

```python
from langgraph_sdk import Auth

auth = Auth()

@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    if not authorization:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Missing token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token not in VALID_TOKENS:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid token")
    return {"identity": VALID_TOKENS[token]["id"]}
```

The handler:
- Receives the raw `Authorization` header value
- Validates however it likes (dict lookup in m5.2, HTTP call to Supabase in m5.4)
- Returns a dict that must include `identity` (the unique user ID); may include `display_name`, `permissions`, custom fields
- Raising `HTTPException` terminates the request — no thread created, no run queued

LangGraph stores the returned dict in `config["configurable"]["langgraph_auth_user"]` so graph nodes can read it.

## Registration in `langgraph.json`

```json
{
  "dependencies": ["."],
  "graphs": { "agent": "./agent/graph.py:graph" },
  "auth": { "path": "./auth.py:auth" }
}
```

`path` is `file:object` — the Python file relative to `langgraph.json`, a colon, then the name of the `Auth` instance inside it.

By default, LangGraph Studio bypasses the auth handler so dev work isn't blocked. For production, add `"disable_studio_auth": true` to the `auth` block.

Custom routes bypass `@auth.authenticate` by default. Opt in with `"http": { "config": { "enable_custom_route_auth": true } }`.

## `@auth.on` — the broad handler

```python
@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict):
    filters = {"owner": ctx.user.identity}
    if ctx.action in ("create", "update", "delete"):
        metadata = value.setdefault("metadata", {})
        metadata.update(filters)
    return filters
```

Two behaviors in one handler:
- **On writes**: mutate `value["metadata"]` to stamp ownership on the resource as it's stored.
- **On reads**: return a filter dict that LangGraph applies as a query against `metadata`. Resources that don't match are invisible.

The same dict is used for both — `{"owner": ctx.user.identity}` — which is why a single broad handler suffices for simple per-user isolation.

## Why 404 instead of 403

When Bob tries to read Alice's thread, the filter `{owner: bob}` is applied to the database query. Alice's thread has `owner: alice` in its metadata — it doesn't match, so it's not returned. From the server's perspective, there is no matching thread for Bob. A 403 would confirm the resource exists (information leak); a 404 reveals nothing.

## Scoped handlers

Sometimes you need different logic per resource/action. `@auth.on.threads.read` is more specific than `@auth.on` — the most specific handler wins for that resource+action combination.

```python
@auth.on.threads.read
async def on_thread_read(ctx, value):
    if ctx.user.identity == "admin":
        return {}            # admin sees everything
    return {"owner": ctx.user.identity}
```

Returning `{}` is "no filter" — the user sees all matching rows (in admin's case, all threads). Returning a dict scopes the query. Raising `HTTPException(403)` denies outright.

You can mix broad and scoped handlers in the same `auth.py`. Broad fills in the gaps.

## `@auth.on.store()` is different

The Store has no automatic filter mechanism. The handler asserts to block or returns `None` to allow:

```python
@auth.on.store()
async def on_store(ctx: Auth.types.AuthContext, value: dict):
    if ctx.user.identity == "admin":
        return                                   # allow
    namespace: tuple = value["namespace"]
    assert namespace[0] == ctx.user.identity     # raises AssertionError → blocked
```

Convention: put the user's identity as the first element of the namespace (`["user1", "notes"]`). The handler enforces that the namespace prefix matches the caller.

Note the parentheses on the decorator — `@auth.on.store()` not `@auth.on.store`.

## Swapping the token store (m5.4)

```python
@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    if not authorization:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Missing token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid scheme")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"Authorization": authorization, "apiKey": SUPABASE_SECRET_KEY},
        )
        response.raise_for_status()
        user = response.json()
        return {"identity": user["id"], "email": user["email"], "is_authenticated": True}
```

The dict lookup is replaced by an HTTP call. `@auth.on` is untouched. Switching from Supabase to Auth0/Clerk/Firebase changes only the HTTP call inside this handler.

## The OAuth2 three-role model

```
Client App ──login──> Auth Provider ──issues JWT──> Client App
Client App ──request + Bearer JWT──> Agent Server ──validates with──> Auth Provider
                                          │
                                          └── @auth.authenticate, @auth.on, agent
```

The Agent Server never stores credentials. It validates JWTs by calling the auth provider and applies access control. The Client App holds the JWT and attaches it on every request.

Two distinct keys in this setup:
- **Secret key** — server-side secret used by `@auth.authenticate` to call the provider's user endpoint. Never sent to the client.
- **Publishable key** — client-side, used to obtain user JWTs from the provider's login endpoint.

## Two access paths to the user identity

Same authenticated user, two access points depending on where you are in the code:

| Where | API | Used by |
|---|---|---|
| `@auth.on` handlers | `ctx.user.identity` (`ctx` is `AuthContext`) | `auth.py` handlers in m5 lessons |
| Graph nodes / middleware | `runtime.server_info.user.identity` | Deepagents CLI per-user memory scoping, custom graph code that needs the caller |

m5 lessons primarily teach the `ctx.user.*` side. The `runtime.server_info.user.*` side is how a graph node can know who called it.

## Auth and namespace in `deep_tutor` (m5.5)

`deep_tutor` decouples auth identity from data namespace:

- **Auth identity** comes from `@auth.authenticate` (after m5.5, from Supabase).
- **Store namespace** comes from `context.store_namespace`, derived from the student's email by the UI (`email_to_namespace`). Same student across multiple per-module assistants shares one namespace and one profile entry.

`@auth.on.store()` is where they meet: it gates that a caller can only access namespaces matching their email-derived namespace. The two concerns stay decoupled — auth controls who can call; namespace controls where data lives.

This contrasts with the deepagents CLI, which uses `(assistant_id, user_identity)` as the namespace — auth identity IS the namespace, so per-user data is automatic but cross-assistant data sharing is not possible.

## Lesson-by-lesson summary

| Lesson | What's added |
|---|---|
| m5.1 — Intro | Concepts: pipeline diagram, two-decorator separation, request flow |
| m5.2 — Local auth | `@auth.authenticate` with hardcoded `VALID_TOKENS`; Alice and Bob have identities but no isolation |
| m5.3 — Private conversations | `@auth.on` (broad and scoped); per-user metadata stamping + filtering; `@auth.on.store()` |
| m5.4 — Auth provider | Replace hardcoded tokens with Supabase JWT validation; `@auth.on` unchanged |
| m5.5 — Tutor auth | Wire the auth handler into `deep_tutor`; auth-namespace decoupling explained |
