"""
Test client for Lesson 2 — run with: uv run python client.py
Requires the server to be running: langgraph dev --no-browser
"""

import asyncio
from langgraph_sdk import get_client

URL = "http://localhost:2024"


async def main():
    # --- Unknown token: not in VALID_TOKENS, should be blocked ---
    hacker = get_client(url=URL, headers={"Authorization": "Bearer hacker-token"})
    try:
        await hacker.threads.create()
        print("❌ Should have been blocked!")
    except Exception as e:
        print(f"✅ Unknown token correctly blocked: {e}")

    # --- Valid token (Alice) ---
    alice = get_client(url=URL, headers={"Authorization": "Bearer alice-token"})
    thread = await alice.threads.create()
    print(f"✅ Alice created thread: {thread['thread_id']}")

    result = await alice.runs.wait(
        thread["thread_id"], "agent",
        input={"messages": [{"role": "user", "content": "Hello from Alice!"}]},
    )
    print(f"✅ Response: {result['messages'][-1]['content']}")

    # --- Valid token (Bob) ---
    bob = get_client(url=URL, headers={"Authorization": "Bearer bob-token"})
    thread = await bob.threads.create()
    print(f"✅ Bob created thread: {thread['thread_id']}")

    # --- Bob can see Alice's thread! No @auth.on means no isolation ---
    bob_view = await bob.threads.search()
    print(f"⚠️  Bob can see {len(bob_view)} thread(s) — including Alice's.")
    print("   Authentication confirmed who Bob is, but didn't scope what he sees.")
    print("   m5.3 fixes this with @auth.on.")


asyncio.run(main())
