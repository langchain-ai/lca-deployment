"""
m4 L2 — Part 1: The Store

Writes a student profile to the LangGraph Store and reads it back.

The Store is cross-thread, deployment-wide persistent storage. Anything written
here is immediately visible to all threads and survives redeployment.

Steps:
  1. Connect to your deployment
  2. Write a profile to the Store
  3. Read it back
  4. List all items in the namespace

Run against a local deployment (default) or pass a cloud URL:
  uv run python store.py
  uv run python store.py https://tutor-xyz.us.langgraph.app
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv(override=True)  # prefer .env file

_url_provided = len(sys.argv) > 1
DEPLOYMENT_URL = sys.argv[1] if _url_provided else "http://localhost:2024"
API_KEY = os.environ.get("LANGSMITH_API_KEY", "")

CHECK = "✅"
ARROW = "→"

# Each student's data is stored under their own namespace.
# The deep_tutor UI builds the namespace from the student's email by replacing
# `.` with `_` (e.g. jane@example.com -> "jane@example_com"). Here we use a
# hardcoded "john_doe" namespace as a stand-in.
NAMESPACE = ("john_doe",)

PROFILE = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "goals": "Understand how LangGraph deployments work end to end.",
}


async def check_connection() -> None:
    try:
        async with httpx.AsyncClient() as http:
            r = await http.get(f"{DEPLOYMENT_URL}/ok", timeout=5)
            r.raise_for_status()
    except Exception as e:
        if _url_provided:
            sys.exit(f"Cannot reach deployment at {DEPLOYMENT_URL}\nCheck the URL and try again.\n{e}")
        else:
            sys.exit(f"Cannot reach local dev server at {DEPLOYMENT_URL}\nIs `langgraph dev` running?\n{e}")


async def main() -> None:
    await check_connection()

    # ---------------------------------------------------------------------------
    # Step 1: Connect to your deployment
    # ---------------------------------------------------------------------------

    client = get_client(url=DEPLOYMENT_URL, api_key=API_KEY)
    print(f"{CHECK} Connected: {DEPLOYMENT_URL}")

    # ---------------------------------------------------------------------------
    # Step 2: Write the profile to the Store
    #
    # put_item is an upsert — writing the same namespace + key again overwrites.
    # The write is immediately visible to all threads in the deployment.
    # ---------------------------------------------------------------------------

    await client.store.put_item(NAMESPACE, key="profile", value=PROFILE)
    print(f"{CHECK} Wrote profile to Store under namespace {NAMESPACE!r}")

    # ---------------------------------------------------------------------------
    # Step 3: Read it back
    #
    # get_item fetches a single item by namespace + key.
    # ---------------------------------------------------------------------------

    item = await client.store.get_item(NAMESPACE, key="profile")
    print(f"\n{ARROW} Read back:")
    for k, v in item["value"].items():
        print(f"  {k}: {v}")

    # ---------------------------------------------------------------------------
    # Step 4: Search all items in the namespace
    #
    # search_items returns everything stored under a namespace prefix.
    # Useful for listing all data for a student.
    # ---------------------------------------------------------------------------

    print(f"\n{ARROW} All items in namespace {NAMESPACE!r}:")
    result = await client.store.search_items(NAMESPACE)
    for entry in result["items"]:
        print(f"  key={entry['key']}  value={entry['value']}")


if __name__ == "__main__":
    asyncio.run(main())
