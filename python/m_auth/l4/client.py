"""
Test client for Lesson 4 — run with: uv run python client.py
Requires the server to be running: uv run langgraph dev --no-browser
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
URL = "http://localhost:2024"

EMAIL1 = "alice+test@example.com"
EMAIL2 = "bob+test@example.com"
PASSWORD = "supersecret123"


async def login(email: str, pw: str) -> str:
    # Steps 1-2: send credentials to Supabase, receive a signed JWT
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": email, "password": pw},
            headers={"apiKey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        )
        if not r.is_success:
            raise Exception(f"{r.status_code}: {r.json()}")
        return r.json()["access_token"]


async def main():
    token1 = await login(EMAIL1, PASSWORD)
    token2 = await login(EMAIL2, PASSWORD)

    # Step 3: attach the JWT as a Bearer token on every request to the agent server
    alice = get_client(url=URL, headers={"Authorization": f"Bearer {token1}"})
    bob   = get_client(url=URL, headers={"Authorization": f"Bearer {token2}"})

    # Steps 3-8: each call sends the JWT; the server validates it with the auth provider
    # (@auth.authenticate, steps 4-6), applies @auth.on (step 7), and responds (step 8)
    alice_thread = await alice.threads.create()
    print(f"✅ Alice created thread: {alice_thread['thread_id']}")

    try:
        await bob.threads.get(alice_thread["thread_id"])  # returns 404 — filtered by @auth.on
        print("❌ Bob should not see Alice's thread!")
    except Exception as e:
        status = getattr(e, "status_code", "error")
        print(f"✅ Bob correctly blocked: {status} — {e}")

    alice_threads = await alice.threads.search()
    bob_threads   = await bob.threads.search()
    print(f"✅ Alice sees {len(alice_threads)} thread(s)")
    print(f"✅ Bob sees {len(bob_threads)} thread(s)")


asyncio.run(main())
