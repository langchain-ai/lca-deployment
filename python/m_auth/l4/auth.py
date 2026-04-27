import os
import httpx
from langgraph_sdk import Auth

auth = Auth()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]


@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
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
    filters = {"owner": ctx.user.identity}
    if ctx.action in ("create", "update", "delete"):
        metadata = value.setdefault("metadata", {})
        metadata.update(filters)
    return filters
