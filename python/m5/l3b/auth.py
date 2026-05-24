from langgraph_sdk import Auth

# Stand-in for a real user database. Do not use hardcoded tokens in production.
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


@auth.on.threads.create
async def on_thread_create(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.create.value,
):
    metadata = value.setdefault("metadata", {})
    metadata["owner"] = ctx.user.identity  # stamp owner on the new thread
    print(f"📝 threads.create → owner={ctx.user.identity}", flush=True)
    return {"owner": ctx.user.identity}


# Read does not write metadata — the thread already exists. We just return
# the filter that scopes the lookup to threads owned by this user.
@auth.on.threads.read
async def on_thread_read(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.read.value,
):
    print(f"🔍 threads.read   → filter owner={ctx.user.identity}", flush=True)
    return {"owner": ctx.user.identity}


@auth.on.threads.search
async def on_thread_search(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.search.value,
):
    print(f"🔎 threads.search → filter owner={ctx.user.identity}", flush=True)
    return {"owner": ctx.user.identity}


# Different rule for a different resource: deny all access to assistants.
@auth.on.assistants
async def on_assistants(ctx: Auth.types.AuthContext, value: dict):
    print(f"⛔ assistants     → DENY {ctx.user.identity}", flush=True)
    raise Auth.exceptions.HTTPException(
        status_code=403,
        detail="Assistants cannot be modified by users.",
    )
