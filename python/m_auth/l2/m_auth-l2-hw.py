"""
Lesson 2 Homework — run with: uv run m_auth-l2-hw.py

Part 1: Pass name through the auth pipeline
--------------------------------------------
Before running, make two small changes:

  auth.py — add "name" to the returned dict:

      return {
          "identity": user_data["id"],
          "name":     user_data["name"],
      }

  agent/graph.py — use name in the response:

      name = user.get("name", identity)
      return {"messages": [AIMessage(content=f"[{name}] {last}")]}

Part 2: Authentication is not authorization
--------------------------------------------
No changes needed — just run and observe.
"""

import asyncio
from langgraph_sdk import get_client

URL = "http://localhost:2024"


async def main():
    alice = get_client(url=URL, headers={"Authorization": "Bearer alice-token"})
    bob   = get_client(url=URL, headers={"Authorization": "Bearer bob-token"})

    # --- Part 1: name flows from auth.py into the graph ---
    thread = await alice.threads.create()
    result = await alice.runs.wait(
        thread["thread_id"], "agent",
        input={"messages": [{"role": "user", "content": "Hello!"}]},
    )
    print(f"✅ Part 1 — Alice's response: {result['messages'][-1]['content']}")
    print("   Expected: [Alice] Hello!  (not [user1] Hello!)")

    # --- Part 2: authentication is not authorization ---
    alice_thread = await alice.threads.create()
    print(f"\n   Alice created thread: {alice_thread['thread_id']}")

    bob_view = await bob.threads.get(alice_thread["thread_id"])
    print(f"✅ Part 2 — Bob read Alice's thread: {bob_view['thread_id']}")
    print("   Bob is authenticated as user2, but nothing stopped him reading Alice's data.")
    print("   @auth.on — added in the next lesson — is what closes this gap.")


asyncio.run(main())
