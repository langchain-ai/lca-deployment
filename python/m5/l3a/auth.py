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


@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict):
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)  # written to metadata on write/create actions
    return filters
