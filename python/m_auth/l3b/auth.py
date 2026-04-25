from langgraph_sdk import Auth

# Stand-in for a real user database. Do not use hardcoded tokens in production.
VALID_TOKENS = {
    "alice-token": {"id": "user1", "name": "Alice"},
    "bob-token":   {"id": "user2", "name": "Bob"},
    "admin-token": {"id": "admin", "name": "Admin"},
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
