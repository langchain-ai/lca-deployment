"""
Test client for Lesson 3 part 2b — run with: uv run python client.py
Requires the server to be running: langgraph dev --no-browser
"""

import asyncio
from langgraph_sdk import get_client

URL = "http://localhost:2024"


async def main():
    alice = get_client(url=URL, headers={"Authorization": "Bearer alice-token"})
    bob   = get_client(url=URL, headers={"Authorization": "Bearer bob-token"})
    admin = get_client(url=URL, headers={"Authorization": "Bearer admin-token"})

    # Alice creates a thread
    alice_thread = await alice.threads.create()
    print(f"✅ Alice created thread: {alice_thread['thread_id']}")

    # Bob creates a thread
    bob_thread = await bob.threads.create()
    print(f"✅ Bob created thread: {bob_thread['thread_id']}")

    # Bob tries to access Alice's thread — should get 404
    try:
        await bob.threads.get(alice_thread["thread_id"])
        print("❌ Bob should not see Alice's thread!")
    except Exception as e:
        status = getattr(e, "status_code", "error")
        print(f"✅ Bob correctly blocked: {status} — {e}")

    # Each user lists only their own threads
    alice_threads = await alice.threads.search()
    bob_threads   = await bob.threads.search()
    print(f"✅ Alice sees {len(alice_threads)} thread(s)")
    print(f"✅ Bob sees {len(bob_threads)} thread(s)")

    # Admin sees all threads
    admin_threads = await admin.threads.search()
    print(f"✅ Admin sees {len(admin_threads)} thread(s)")


asyncio.run(main())
