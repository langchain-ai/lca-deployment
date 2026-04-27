# Authentication and Authorization: Lesson 4 — Connect an Authentication Provider

In Lessons 2 and 3 you built a working auth system using hardcoded tokens. The `@auth.on` authorization handlers gave each user private conversations. What is still missing is a secure way to manage real user identities — hardcoded tokens are fine for learning the mechanics but not production.

In this lesson you will replace the `VALID_TOKENS` dict with real user accounts. Your `@auth.authenticate` handler will call an auth provider to validate JWT tokens instead of looking up a local dict. **The `@auth.on` authorization handlers stay exactly as-is** — they work from whatever fields `@auth.authenticate` returns, regardless of how the token was validated.

By the end of this lesson your deployment will have:
- Real user accounts managed by an auth provider
- Secure JWT validation on every request
- The same per-user resource isolation from Lesson 3

<style>@import url('../../shared/sd-components.css');</style>
<script src="../../shared/sd-components.js"></script>

<div class="sd-wrap" id="sd-oauth-flow"></div>

---

## How the OAuth2 flow works

In the hardcoded-token approach, your server was the only piece in the puzzle. With a real identity provider, three components are involved:

1. **Client Application** — your web or mobile UI. It collects credentials and exchanges them for a JWT from the auth provider.
2. **Auth Provider** — manages user accounts, handles login, and issues signed JWTs.
3. **Agent Server** — your LangGraph application. It validates JWTs by calling the auth provider and then applies `@auth.on` access control as before.

The JWT travels from the auth provider to the client and then to the agent server on every request. Your agent server never stores credentials — it only validates tokens.

`python/m_auth/l4/client.py`, which you will run later in the lesson, maps directly to the diagram — the comments show which steps each line corresponds to:

```python
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
```

---

## Step 1: Set up Supabase

This lesson uses Supabase, but any JWT-based auth provider will work. Other common options are [Auth0](https://auth0.com), [Firebase Authentication](https://firebase.google.com/docs/auth), and [Clerk](https://clerk.com). The only thing that changes between providers is the HTTP call inside `@auth.authenticate`.

If you do not have a Supabase project yet, see the [Supabase getting started guide](https://supabase.com/docs/guides/getting-started) or go directly to [database.new](https://database.new) to create one.

Once your project is ready, open the [Supabase dashboard](https://supabase.com/dashboard) and navigate to your project:

1. Go to **Project Settings → API Keys**. Copy the **service_role** key and add it to `.env`:
   ```
   SUPABASE_SERVICE_KEY=your-service-role-key
   ```
2. On the same page, copy the **Publishable key** and add it to `.env`:
   ```
   SUPABASE_ANON_KEY=your-publishable-key
   ```
3. Your project URL is derived from your project reference, which appears in the browser address bar: `https://supabase.com/dashboard/project/[project-ref]/...`. Add it to `.env`:
   ```
   SUPABASE_URL=https://[project-ref].supabase.co
   ```
   Note: the dashboard is at `supabase.com` but your project URL uses `supabase.co` — they are different domains.
4. Go to **Authentication → Providers → Email** and turn off **Confirm email**. This allows test accounts to log in immediately without requiring a real inbox. Re-enable it for production.

<Tip>
**Two keys, two purposes**

The **service role key** is a server-side secret. Your agent server uses it to call the auth provider API and validate tokens. It must never be exposed to the client.

The **Publishable key** (also called the anon key) is safe to include in client-side code. Your UI uses it when calling the auth provider login endpoint to obtain a user JWT.
</Tip>

---

## Step 2: Review auth.py

`python/m_auth/l4/auth.py` replaces the dict lookup with a call to the auth provider. The `@auth.on` handler at the bottom is unchanged from Lesson 3:

```python {19-26}
import os
import httpx
from langgraph_sdk import Auth

auth = Auth()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    """Validate JWT with the auth provider and return the authenticated user."""
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

# @auth.on is unchanged — same broad handler as used previously
@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict):
    filters = {"owner": ctx.user.identity}
    if ctx.action in ("create", "update", "delete"):
        metadata = value.setdefault("metadata", {})
        metadata.update(filters)
    return filters
```

The only difference from Lesson 3 is the body of `@auth.authenticate`. Instead of a dict lookup it makes an HTTP call to the auth provider's `/auth/v1/user` endpoint, which validates the token and returns the user's profile. Everything else — the `Auth` instance, the `@auth.on` handler, the `langgraph.json` registration — is unchanged.

Start the server:

```bash
cd python/m_auth/l4
uv run langgraph dev --no-browser
```

---

## Step 3: Create test users

`python/m_auth/l4/setup.py` registers Alice and Bob in your Supabase project. Run it once from a second terminal:

```bash
cd python/m_auth/l4
uv run python setup.py
```

Expected output:

```
✅ Created alice+test@example.com
✅ Created bob+test@example.com
```

## Step 4: Test isolation

Run `python/m_auth/l4/client.py` to log in as both users and verify they can only see their own threads:

```bash
cd python/m_auth/l4
uv run python client.py
```

In the `langgraph dev` terminal you can see each request as it happens. The log mostly shows **outgoing** calls from LangGraph to Supabase — one `GET /auth/v1/user` per authenticated request. Failed incoming requests are logged as warnings. Here is a summary:

```
→ GET /auth/v1/user 200  — Alice's token validated (thread create)
→ GET /auth/v1/user 200  — Bob's token validated (thread get)
← GET /threads/{id} 404  — Bob's request filtered: thread not visible to him
→ GET /auth/v1/user 200  — Alice's token validated (thread search)
→ GET /auth/v1/user 200  — Bob's token validated (thread search)
```

(`→` outgoing to Supabase, `←` incoming to LangGraph)

Every outgoing call is `@auth.authenticate` firing. The 404 on Bob's thread read is `@auth.on` in action: his filter returns no match, so the thread does not exist from his perspective.

The results should be identical to the previous lesson — the same isolation, now backed by real user accounts.

---

## What you learned in this lesson

- **OAuth2 roles** — client application, auth provider, and agent server each have a distinct responsibility. The agent server validates tokens but never stores credentials.
- **Auth provider setup** — two keys serve different roles: the service role key is a server-side secret used to validate tokens; the Publishable key is used client-side to log in and obtain JWTs.
- **Upgrading `@auth.authenticate`** — replace the dict lookup with an HTTP call to the auth provider's user endpoint. The user profile returned is the source of truth for `identity` and `email`.
- **`@auth.on` unchanged** — authorization logic is fully decoupled from authentication. Swapping the identity provider requires no changes to your access control handlers.

---

## What you have learned so far

- **L1** — understood the auth architecture: `@auth.authenticate` for identity, `@auth.on` for access control.
- **L2** — implemented `@auth.authenticate` with hardcoded tokens.
- **L3** — added `@auth.on` to give each user private conversations.
- **L4** — replaced hardcoded tokens with real JWT validation.

The pattern you learned here applies to any OAuth2 provider. If you switch from Supabase to Auth0 or Google, only the HTTP call inside `@auth.authenticate` changes. The authorization handlers, the `langgraph.json` config, and your agent graph are all unaffected.

## Up next

In the next lesson you will wire this auth system into the tutor agent — replacing the test echo graph with a real deployed application backed by the same `@auth.authenticate` and `@auth.on` handlers you wrote here.

---

## Check your understanding

<MCQ
    question="Which component issues the JWT that your agent server validates?"
    choices='["The Agent Server itself", "The Client Application", "The Auth Provider", "LangSmith"]'
    correctIndex={2}
    explanation="The auth provider manages user accounts, handles login, and issues signed JWTs. The client application receives the JWT and passes it to the agent server. The agent server only validates — it never issues tokens."
/>

<MCQ
    question="What does the service role key do in this lesson?"
    choices='["It is used by the client to log in", "It is used by the agent server to validate tokens via the auth provider API", "It signs new JWTs for each request", "It is an alternative to the bearer token"]'
    correctIndex={1}
    explanation="The service role key is a server-side secret. The agent server uses it in the apiKey header when calling the auth provider user endpoint to validate the user token. It must never be sent to the client."
/>

<MCQ
    question="What does your agent server call to validate a JWT?"
    choices='["POST /auth/v1/signup", "GET /auth/v1/user", "POST /auth/v1/token", "GET /auth/v1/validate"]'
    correctIndex={1}
    explanation="GET /auth/v1/user with the user bearer token in the Authorization header and the service role key in the apiKey header returns the user profile if the token is valid, or an error if not. You can verify this in python/m_auth/l4/auth.py."
/>

<MCQ
    question="After connecting an auth provider in Lesson 4, what changes in your @auth.on handler?"
    choices='["It must now call the auth provider to fetch ownership data", "Nothing — @auth.on is unchanged", "It must validate the JWT before stamping metadata", "It receives a different ctx.user type"]'
    correctIndex={1}
    explanation="@auth.on uses ctx.user fields populated by @auth.authenticate, regardless of how the token was validated. In this lesson that is just ctx.user.identity, but @auth.authenticate can return any fields the provider supplies — roles, email, metadata. The clean separation means @auth.on does not care which provider issued the token, only what @auth.authenticate extracted from it."
/>

<MCQ
    question="If you switched from Supabase to a different OAuth2 provider, what would you need to change?"
    choices='["The @auth.authenticate handler only", "The @auth.on handler only", "Both handlers and langgraph.json", "The agent graph itself"]'
    correctIndex={0}
    explanation="Only @auth.authenticate changes — the HTTP call and the field names from the provider response. @auth.on, langgraph.json, and your agent graph are all unaffected because they only depend on what @auth.authenticate returns, not on which provider issued the token."
/>

<script>
buildDiagram({
    id: 'sd-oauth-flow',
    participants: ['Client App', 'Auth Provider', 'Agent Server'],
    cx: [130, 500, 870],
    bw: 150, bh: 40, tby: 10, bby: 415, vw: 1000, vh: 465,
    buildSteps: function(a) {
      return [
        solidArrow(130, 500,  75, '1. login (email + password)', 310, a),
        dashedArrow(500, 130, 125, '2. signed JWT', 310, a),
        solidArrow(130, 870,  175, '3. request + Bearer JWT', 500, a),
        labelBox(870, 210, 260, ['4. @auth.authenticate fires', 'call /auth/v1/user']),
        solidArrow(870, 500,  290, '5. validate JWT (service key)', 690, a),
        dashedArrow(500, 870, 340, '6. user profile confirmed', 690, a),
        labelBox(870, 370, 260, ['7. @auth.on fires', 'stamp / filter by owner']),
        dashedArrow(870, 130, 415, '8. response returned', 600, a),
      ];
    },
    steps: [
      { tag: 'Step 1 of 8', caption: 'The user logs in through the client application. Credentials are sent to the auth provider, not to your agent server.' },
      { tag: 'Step 2 of 8', caption: 'The auth provider validates the credentials and issues a signed JWT back to the client.' },
      { tag: 'Step 3 of 8', caption: 'The client attaches the JWT as a Bearer token and sends the request to your agent server.' },
      { tag: 'Step 4 of 8', caption: '@auth.authenticate fires. It extracts the token from the Authorization header and calls the auth provider user endpoint.' },
      { tag: 'Step 5 of 8', caption: 'The agent server calls the auth provider with the user token and the service role key. This is the server-to-server validation step.' },
      { tag: 'Step 6 of 8', caption: 'The auth provider confirms the token is valid and returns the user profile — including the user ID, which becomes ctx.user.identity.' },
      { tag: 'Step 7 of 8', caption: '@auth.on fires next. It uses ctx.user.identity to stamp ownership on writes and filter reads — exactly as in Lesson 3.' },
      { tag: 'Step 8 of 8', caption: 'With identity verified and access control applied, the agent server processes the request and returns the response.' },
    ]
});
</script>
