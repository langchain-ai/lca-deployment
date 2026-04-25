"""
Test client for Lesson 3c — run with: uv run python client.py
Requires the server to be running: langgraph dev --no-browser
"""

import asyncio
from langgraph_sdk import get_client

URL = "http://localhost:2024"


async def main():
    alice = get_client(url=URL, headers={"Authorization": "Bearer alice-token"})
    bob   = get_client(url=URL, headers={"Authorization": "Bearer bob-token"})
    admin = get_client(url=URL, headers={"Authorization": "Bearer admin-token"})

    # Alice stores a note in her namespace
    await alice.store.put_item(
        ["user1", "notes"],
        key="note1",
        value={"content": "Alice's private note"},
    )
    print("✅ Alice stored a note")

    # Bob tries to read Alice's note — should be blocked
    try:
        await bob.store.get_item(["user1", "notes"], key="note1")
        print("❌ Bob should not see Alice's note!")
    except Exception as e:
        print(f"✅ Bob correctly blocked: {e}")

    # Alice reads her own note
    item = await alice.store.get_item(["user1", "notes"], key="note1")
    print(f"✅ Alice reads her note: {item['value']['content']}")

    # Bob stores his own note
    await bob.store.put_item(
        ["user2", "notes"],
        key="note1",
        value={"content": "Bob's private note"},
    )
    print("✅ Bob stored a note")

    # Admin can read from any namespace
    alice_item = await admin.store.get_item(["user1", "notes"], key="note1")
    bob_item   = await admin.store.get_item(["user2", "notes"], key="note1")
    print(f"✅ Admin reads Alice's note: {alice_item['value']['content']}")
    print(f"✅ Admin reads Bob's note: {bob_item['value']['content']}")


asyncio.run(main())
