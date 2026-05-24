"""
One-time setup — creates Alice and Bob in your Supabase project.
Run with: uv run python setup.py
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)  # prefer .env file

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]

EMAIL1 = "alice+test@example.com"
EMAIL2 = "bob+test@example.com"
PASSWORD = "supersecret123"


async def sign_up(email: str, pw: str):
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            json={"email": email, "password": pw},
            headers={"apiKey": SUPABASE_ANON_KEY},
        )
        if not r.is_success:
            raise Exception(f"{r.status_code}: {r.json()}")
        print(f"✅ Created {email}")


async def main():
    await sign_up(EMAIL1, PASSWORD)
    await sign_up(EMAIL2, PASSWORD)


asyncio.run(main())
