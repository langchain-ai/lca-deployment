"""
auth_supabase.py — LangGraph agent auth using Supabase OAuth

Enable in langgraph.json:
    "auth": { "path": "./agent/auth_supabase.py:auth" }

@auth.authenticate validates regular user tokens via the Supabase API on every request.
This is the full OAuth pattern: the provider confirms the token is still valid, enabling
revocation detection and support for multiple providers.

Admin tokens are issued locally by app.py and verified locally with SUPABASE_JWT_SECRET.

Required .env:
    SUPABASE_OAUTH=true
    SUPABASE_URL=https://<project>.supabase.co
    SUPABASE_ANON_KEY=<anon key — used to call Supabase auth API>
    SUPABASE_JWT_SECRET=<JWT secret — used to sign and verify admin tokens>
"""

import os

import httpx
import jwt
from langgraph_sdk import Auth

auth = Auth()


@auth.authenticate
async def authenticate(authorization: str | None) -> dict:
    """Validate token. Admin tokens verified locally; regular users validated via Supabase API."""
    if not authorization or not authorization.startswith("Bearer "):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]

    # Admin/service tokens are signed with JWT_SECRET (same as auth_local.py).
    # SUPABASE_JWT_SECRET is for Supabase user tokens only — not for internal service tokens.
    admin_secret = os.environ.get("JWT_SECRET")
    if admin_secret:
        try:
            payload = jwt.decode(
                token,
                admin_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            if payload.get("role") == "admin":
                username = payload["sub"]
                namespace = payload.get("namespace", username)
                return {"identity": username, "permissions": ["admin", "user"], "namespace": namespace}
            # Non-admin locally-signed token — fall through to Supabase API
        except jwt.ExpiredSignatureError:
            raise Auth.exceptions.HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            pass  # Not a locally-signed token — try Supabase API

    # Regular users — validate via Supabase API.
    # This call confirms the token is still valid (handles revocation, account disabling,
    # and works across any Supabase-supported OAuth provider).
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{os.environ['SUPABASE_URL']}/auth/v1/user",
                headers={
                    "Authorization": authorization,
                    "apiKey": os.environ["SUPABASE_ANON_KEY"],
                },
            )
            response.raise_for_status()
            user = response.json()
    except httpx.HTTPStatusError:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise Auth.exceptions.HTTPException(status_code=401, detail=str(e))

    username = user.get("email") or user["id"]
    namespace = (user.get("user_metadata") or {}).get("namespace") or username
    return {"identity": username, "permissions": ["user"], "namespace": namespace}


@auth.on
async def on_resource(ctx: Auth.types.AuthContext, value: dict):
    """Stamp owner on creation; filter by owner on reads. Admins bypass filtering."""
    if "admin" in ctx.permissions:
        return

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
