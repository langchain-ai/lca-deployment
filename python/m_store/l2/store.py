"""
m_store L2 — Part 1: The Store

Writes a student profile to the LangGraph Store and reads it back.

The Store is cross-thread, deployment-wide persistent storage. Anything written
here is immediately visible to all threads and survives redeployment.

Run with deep_tutor running locally:
  uv run python store.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv(Path(__file__).parent / ".env")

DEPLOYMENT_URL = "http://127.0.0.1:2024"
API_KEY = os.environ.get("LANGSMITH_API_KEY", "")

# Each student's data is stored under their own namespace.
# The namespace is first_last — the same value the UI sets as store_namespace.
FIRST_NAME = "John"
LAST_NAME = "Doe"
NAMESPACE = (f"{FIRST_NAME.lower()}_{LAST_NAME.lower()}",)

PROFILE = {
    "first_name": FIRST_NAME,
    "last_name": LAST_NAME,
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
