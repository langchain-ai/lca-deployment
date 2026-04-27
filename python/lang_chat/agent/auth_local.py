"""
auth_local.py — LangGraph agent auth using local JWT

Enable in langgraph.json:
    "auth": { "path": "./agent/auth_local.py:auth" }

@auth.authenticate validates a JWT signed by app.py with JWT_SECRET.
Role is baked into the token at login to avoid a circular Store lookup.

Compare with auth_supabase.py — only @auth.authenticate differs.
@auth.on is identical between the two files.
"""

import os

import jwt
from langgraph_sdk import Auth

auth = Auth()


@auth.authenticate
async def authenticate(authorization: str | None) -> dict:
    """Validate JWT. Returns identity and permissions derived from the token's role field."""
    if not authorization or not authorization.startswith("Bearer "):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid token")

    username = payload["sub"]
    role = payload.get("role", "user")
    namespace = payload.get("namespace", username)
    permissions = ["admin", "user"] if role == "admin" else ["user"]
    return {"identity": username, "permissions": permissions, "namespace": namespace}


@auth.on
async def on_resource(ctx: Auth.types.AuthContext, value: dict):
    """Stamp owner on creation; filter by owner on reads. Admins bypass filtering."""
    if "admin" in ctx.permissions:
        return  # admins see all resources

    filters = {"owner": ctx.user.identity}

    is_write = ctx.action in ("create", "update", "delete")
    if is_write:
        metadata = value.setdefault("metadata", {})
        metadata.update(filters)

    return filters


@auth.on.store()
async def on_store(ctx: Auth.types.AuthContext, value: dict):
    """Restrict store access to the user's own namespace. Admins bypass."""
    if "admin" in ctx.permissions:
        return

    namespace = tuple(value.get("namespace") or ())
    if not namespace or namespace[0] != ctx.user.namespace:
        raise Auth.exceptions.HTTPException(status_code=403, detail="Not authorized")
