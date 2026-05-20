"""
Auth handler for the tutor deployment.

Wires Supabase JWT validation (@auth.authenticate) and per-user resource
scoping (@auth.on, @auth.on.store) on top of the tutor agent.
"""
import os
import httpx
from langgraph_sdk import Auth

auth = Auth()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]


def email_to_namespace(email: str) -> str:
    """Same conversion used by the UI's `email_to_namespace`."""
    return email.replace(".", "_")


@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    """Validate JWT against Supabase and return the authenticated user."""
    if not authorization:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Missing token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid scheme")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": authorization,
                    "apiKey": SUPABASE_SERVICE_KEY,
                },
            )
            response.raise_for_status()
            user = response.json()
            return {
                "identity": user["id"],
                "email": user["email"],
                "is_authenticated": True,
            }
    except Exception as e:
        raise Auth.exceptions.HTTPException(status_code=401, detail=str(e))


@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict):
    """Stamp `owner` on writes; return same filter so reads scope to this user."""
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)  # written to metadata on write/create actions
    return filters


@auth.on.store()
async def on_store(ctx: Auth.types.AuthContext, value: dict):
    """Only allow access to the namespace matching the caller's email.

    The UI builds the namespace via email.replace(".", "_") — same here.
    """
    expected = email_to_namespace(ctx.user["email"])
    namespace = value["namespace"]
    assert namespace[0] == expected, "Not authorized"
