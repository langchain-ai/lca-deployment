"""
m4 L2 — Part 1: The Store

Writes a student profile to the LangGraph Store and reads it back.

The Store is cross-thread, deployment-wide persistent storage. Anything written
here is immediately visible to all threads and survives redeployment.

Run against a local deployment (default) or pass a cloud URL:
  uv run python store.py
  uv run python store.py https://tutor-xyz.us.langgraph.app
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()  # expects python/.env — loads LANGSMITH_API_KEY

DEPLOYMENT_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:2024"
API_KEY = os.environ.get("LANGSMITH_API_KEY", "")

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


async def main() -> None:
    client = get_client(url=DEPLOYMENT_URL, api_key=API_KEY)

    # ---------------------------------------------------------------------------
    # Write the profile to the Store
    #
    # put_item is an upsert — writing the same namespace + key again overwrites.
    # The write is immediately visible to all threads in the deployment.
    # ---------------------------------------------------------------------------

    await client.store.put_item(NAMESPACE, key="profile", value=PROFILE)
    print(f"Wrote profile to Store under namespace {NAMESPACE!r}\n")

    # ---------------------------------------------------------------------------
    # Read it back
    #
    # get_item fetches a single item by namespace + key.
    # ---------------------------------------------------------------------------

    item = await client.store.get_item(NAMESPACE, key="profile")
    print("Read back:")
    for k, v in item["value"].items():
        print(f"  {k}: {v}")

    # ---------------------------------------------------------------------------
    # Search all items in the namespace
    #
    # search_items returns everything stored under a namespace prefix.
    # Useful for listing all data for a student.
    # ---------------------------------------------------------------------------

    print(f"\nAll items in namespace {NAMESPACE!r}:")
    result = await client.store.search_items(NAMESPACE)
    for entry in result["items"]:
        print(f"  key={entry['key']}  value={entry['value']}")


if __name__ == "__main__":
    asyncio.run(main())
