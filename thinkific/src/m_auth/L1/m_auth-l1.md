# Authentication and Authorization in a Multi-Tenant environment: Lesson 1

As your agent moves to production, it is likely that it will now be run by many (many!) users. Naturally, in a Multi-tenant situation like this you would like to 1) understand who is using your system  and 2) specify resources and actions are allowed to that user.

The terms we will use for these are:

- **Authentication (AuthN)** — verifying the user is who they claim to be. The "who are you?" check.
- **Authorization (AuthZ)** — determining what a verified identity is permitted to see or do. The "what can you do?" check.


There are three applications of Authentication and Authorization to consider: 

- **Controlling user access:** This relates to your users and is the focus of this module.
- **Controlling agent access:** This relates to the access provided to a users agents. For example, do they have access to the users email so they can read emails on the users behalf. This is "Agent Auth" and you can find more details on this [here](https://docs.langchain.com/langsmith/agent-auth). 
- **Controlling the deployment:** This relates to you and your team. LangSmith [RBAC (Role Based Acess Control)](https://docs.langchain.com/langsmith/rbac) gives you control of who can deploy, update and monitor your agents. 

In this lesson,  you will learn about:
- The base authentication system - the method you have been using.
- The authentication and authorization process.
- Custom authentication.
- Custom authorization.

## Base authorization

You have been using authentication throughout this course without thinking about it! Every time you call one of your deployment endpoints, you include a LangSmith API key in the request. That key is what grants access — the server validates it before processing anything.


Step through the diagram below — this is the same flow you have been using every time you call your deployed agent.

<style>@import url('../../shared/sd-components.css');</style>
<script src="../../shared/sd-components.js"></script>

<div class="sd-wrap" id="sd-arch"></div>

Here is the same four steps shown as a sequence diagram. We will be using sequence diagrams in this section because they are a great way to see the order of information exchange between elements of the system.

<div class="sd-wrap" id="sd-simple"></div>

---

The LangSmith docs cover the same split under [Authentication and access control](https://docs.langchain.com/langsmith/auth) (AuthN vs AuthZ and deployment hooks).

LangSmith deployment lets you customize both through `@auth` middleware hooks.

---

## The authentication and authorization process.

Lets consider what authentication and authorization looks like in general, and then you'll learn about each of the components in more detail. There are three components: a client application, an auth provider, and your agent server. 
**1. Client Application**
The frontend used by your users. It collects credentials, obtains a token from the auth provider, and includes that token in every request to your agent. 

**2. Auth Provider (Identity Provider)**
A dedicated service that manages user identities, handles login, and issues signed tokens. Examples: Auth0, Supabase Auth, Okta.

**3. Agent Server**
Your LangGraph application. It validates tokens through `@auth.authenticate`, enforces access control through `@auth.on.*`, and never stores credentials directly.


Step through the full sequence below.

<div class="sd-wrap" id="sd-multi"></div>

---
You will see multiple forms of clients and authentication providers in the coming lessons, but there are key elements to notice.
- The client authenticates and receives a token, typically a JSON Web Token (JWT) which identifies the user.
- The token identifies the user to the Agent Server.
- The agent server can verify the token and its contents are valid.
- THe user may have specific resources and functions they can access/use, that information can be indexed by the now validated user.

You can see the similarity to the base method. The LANGSMITH_API_KEY identifies a unique client. LangSmith confirms that key and user are valid and returns that information to the Agent Server.

Now, Lets look more closely at how you can customize authentication and authorization.

---

## Custom Authentication

Every request to Agent Server is authenticated. The notional diagram below show the input path of a request.

<pre style="font-size:0.85rem;line-height:1.5;background:none;border:none;padding:0;">
HTTP request
     │
     ▼
  Uvicorn                        ← owned by LangGraph
     │
     ▼
  LangGraph server
     │
     ├── auth                    ← runs on all LangGraph runtime requests *
     │   └── @auth.authenticate
     │
     ├── custom middleware       ← optional
     │
     ├── /runs, /threads, ...    ← LangGraph runtime
</pre>

> \* Custom routes bypass `@auth.authenticate` by default. Auth can be enabled on them via `"enable_custom_route_auth": true` in your `langgraph.json` HTTP config — but this applies to all custom routes. For selective auth (e.g. a public login route), declare a `path` parameter in your handler and branch on it.

The 'auth' step can be can be augmented with a custom authentication handler. The handler identified with @auth.authenticate performs the custom authentication for your system.

The handler runs on the server, which is Python. The client calling the server can be Python or TypeScript.

```python
@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    # add your custom authentication code here
    return {
        "identity": ...,  # required — unique user identifier
        # any additional fields (tokens, roles, org IDs, etc.) are optional
    }
```

The `Authorization` header is a standard HTTP header that clients include in every request to identify themselves. It typically takes the form `Bearer <token>`. The handler receives it, validates the token, and returns a dict with at least an `identity` field.

LangGraph automatically takes that returned dict and stores it in the request config under `config["configurable"]["langgraph_auth_user"]`. This means your graph nodes can read the authenticated user without any extra work:

```python
@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    # ... validate token ...
    return {
        "identity": "alice",
        "role": "admin",
        "org_id": "org-456",
        "github_token": "ghp_...",
    }
```

All of those fields are available in your graph nodes via the config:

```python
def my_node(state, config):
    user = config["configurable"].get("langgraph_auth_user")
    user["identity"]       # "alice"
    user["role"]           # "admin"
    user["org_id"]         # "org-456"
    user["github_token"]   # "ghp_..."
```

This is useful when your graph logic needs to know who is running it — for example to personalise responses, enforce role-based logic, or call external APIs on the user's behalf.

To add your custom authentication to the system, register the handler in `langgraph.json`:

```json
{
  "auth": {
    "path": "auth.py:auth"
  }
}
```

This will include the specified handler during the next build and deployment. The next lesson walks through a complete working example.

## Custom Authorization

Once the user's identity is established by `@auth.authenticate`, you can control what resources that user is allowed to access. This is done with `@auth.on` handlers.

An `@auth.on` handler runs after authentication and receives two arguments: the auth context (which includes the verified user) and the resource being accessed. It returns a filter that scopes the data to that user:

```python
@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict) -> dict:
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    return filters
```

The returned filter is applied automatically — a user can only see threads, runs, and other resources that match it. This is what gives each user their own isolated view of data in a multi-tenant system.

You can also write handlers for specific resource types if different rules apply to different actions:

```python
@auth.on.threads.create
async def on_thread_create(ctx, value):
    metadata = value.setdefault("metadata", {})  # get existing metadata dict, or create it if absent
    metadata["owner"] = ctx.user.identity        # stamp the new record in the database with the owner
    return {"owner": ctx.user.identity}    # filter: this user can only query records where owner matches

@auth.on.threads.read
async def on_thread_read(ctx, value):
    return {"owner": ctx.user.identity}    # filter: only return threads owned by this user
```

The most specific handler wins — so `@auth.on.threads.create` takes precedence over `@auth.on` for thread creation, while the general `@auth.on` handler covers everything else.

For example, consider two users — Alice with token `alice-token` and Bob with token `bob-token`. Each creates a thread and sends a message:

<Tabs>
<Tab title="Python">
```python
# Alice's client
alice = get_client(url="...", headers={"Authorization": "Bearer alice-token"})
alice_thread = await alice.threads.create()
await alice.runs.create(alice_thread["thread_id"], assistant_id="agent", input={"messages": [{"role": "user", "content": "Hello"}]})

# Bob's client
bob = get_client(url="...", headers={"Authorization": "Bearer bob-token"})
bob_thread = await bob.threads.create()
await bob.runs.create(bob_thread["thread_id"], assistant_id="agent", input={"messages": [{"role": "user", "content": "Hello"}]})
```
</Tab>
<Tab title="TypeScript">
```typescript
const alice = new Client({ apiUrl: "...", defaultHeaders: { Authorization: "Bearer alice-token" } });
const aliceThread = await alice.threads.create();

const bob = new Client({ apiUrl: "...", defaultHeaders: { Authorization: "Bearer bob-token" } });
const bobThread = await bob.threads.create();
```
</Tab>
</Tabs>

When Alice searches her threads she only gets her own back — Bob's thread is invisible to her, even though it exists in the same deployment:

```python
threads = await alice.threads.search()  # triggers @auth.on.threads.read, which filters to owner == alice
```

This isolation happens automatically because `@auth.on.threads.create` stamped each thread with its owner on creation, and `@auth.on.threads.read` filters by that same owner on every read.

<Tip>
**Under the hood ⚙️**

LangGraph stores a `metadata` column on every thread (and run, and other resources). When your create handler sets `metadata["owner"] = ctx.user.identity`, that value is written to the database alongside the thread.

The dict your read handler *returns* is applied as a generic filter against that metadata column — LangGraph doesn't know or care about the key name `owner`. It takes whatever dict you return and queries for records where each key matches. Any key name works, as long as it's consistent between your two handlers.

`identity` is the one field LangGraph *does* know about — it is required in the return value of `@auth.authenticate` so that `ctx.user.identity` is always guaranteed to be available in your `@auth.on` handlers. Everything else, including how you use it to filter, is your convention.

The key name (`owner` here) is a contract between your own handlers. If the keys differ between create and read, the filter silently returns nothing.
</Tip>

---

## What you learned in this lesson

- **AuthN vs AuthZ** — Authentication verifies who the user is; authorization determines what they can do.
- **The base auth flow** — every request to your deployment already carries a LangSmith API key, which is validated before anything runs. This is fine for development but provides no per-user isolation.
- **`@auth.authenticate`** — a server-side Python handler that validates incoming tokens and returns a user dict with at least an `identity` field. LangGraph makes the full dict available to your graph nodes via `config["configurable"]["langgraph_auth_user"]`.
- **`@auth.on` handlers** — run after authentication and return a filter dict that LangGraph applies generically against each resource's `metadata` column. The key name is your convention — you stamp it on create and filter by it on read.
- **Handler specificity** — `@auth.on.threads.create` takes precedence over `@auth.on` for that specific action. The most specific handler wins.
- **Custom routes** — `@auth.authenticate` does not run on custom routes by default. It can be enabled globally via `"enable_custom_route_auth": true`, or handled selectively inside the handler itself using the `path` parameter.

---

## Up next

In the coming lessons you will put both hooks into practice:

- **Local authentication** — start with hardcoded tokens to get comfortable with the `@auth.authenticate` and `@auth.on` pattern.
- **Tutor agent** — apply the same auth pattern to your AI tutor deployment.
- **OAuth** — delegate identity management to an external provider (Supabase Auth) so your users can log in with real credentials.

---

## Check your understanding

<MCQ
    question="What do multi-tenant applications need that the LangSmith API key auth flow does not provide?"
    choices='["Faster token validation", "Per-user data isolation", "A stronger API key", "OAuth support"]'
    correctIndex={1}
    explanation="The API key confirms that someone has access, but all users share the same view of data. Multi-tenant systems need to know not just that someone has access, but who they are and what data they are allowed to see."
/>

<MCQ
    question="What is missing from the LangSmith API key auth flow that makes it unsuitable for production?"
    choices='["It does not validate the key", "It is too slow", "There is no per-user data isolation", "It requires OAuth"]'
    correctIndex={2}
    explanation="The API key confirms that someone has access, but all users share the same view of data. A production multi-tenant system needs to scope each user to their own resources."
/>

<MCQ
    question="What does the dict returned from an @auth.on handler get applied to?"
    choices='["The request headers", "The user token", "The resource metadata column", "The LangGraph config"]'
    correctIndex={2}
    explanation="LangGraph applies the returned filter dict as a key-value query against the metadata column stored with each resource (thread, run, etc.). Any key name works — it is your convention."
/>

<MCQ
    question="Where does LangGraph make the authenticated user available to your graph nodes?"
    choices='["state.user", "config, under configurable then langgraph_auth_user", "ctx.user", "It is not accessible in graph nodes"]'
    correctIndex={1}
    explanation="LangGraph stores the full dict returned by @auth.authenticate under the langgraph_auth_user key in the configurable section of the node config. Every field you return — identity, role, org_id, tokens — is accessible there."
/>

<MCQ
    question="If both @auth.on and @auth.on.threads.create are defined, which runs on a thread creation?"
    choices='["Both, in order", "@auth.on", "@auth.on.threads.create", "Neither — they conflict"]'
    correctIndex={2}
    explanation="The most specific handler wins. @auth.on.threads.create takes precedence over the global @auth.on fallback for thread creation events."
/>

<MCQ
    question="By default, does @auth.authenticate run on your custom routes?"
    choices='["Yes, always", "No, opt-in via config", "Only on POST routes", "Only if you return identity"]'
    correctIndex={1}
    explanation="Custom routes bypass @auth.authenticate by default. You can enable auth on them globally via enable_custom_route_auth in your langgraph.json HTTP config, or handle it selectively inside the authenticate handler using the path parameter."
/>

<script>
buildDiagram({
    id: 'sd-arch',
    vw: 1000, vh: 480,
    stageBg: '#F2FAFF',
    participants: [],
    staticSVG: [
      '<rect width="1000" height="480" fill="#F2FAFF"/>',
      '<rect x="330" y="15" width="200" height="55" rx="8" fill="#006DDD"/>',
      '<text x="430" y="49" text-anchor="middle" fill="#F2FAFF" font-size="16" font-weight="500">LangSmith</text>',
      '<rect x="405" y="120" width="40" height="280" rx="6" fill="#161F34" stroke="#2F4B68" stroke-width="1.5"/>',
      '<text x="425" y="290" text-anchor="middle" dominant-baseline="central" fill="#E5F4FF" font-size="13" font-weight="500" transform="rotate(-90 425 290)">api server</text>',
    ].join(''),
    buildSteps: function(a) {
      return [
        // Step 1: client → api server
        '<rect class="aab" x="15" y="237" width="195" height="106" rx="6" stroke-width="1.5"/>' +
        '<text font-size="13">' +
          '<tspan class="aac" x="28" y="261">client.runs(&#8230;</tspan>' +
          '<tspan class="aak" x="40" y="283">  thread_id=1,</tspan>' +
          '<tspan class="aac" x="40" y="305">  &#34;tell me more&#8230;&#34;</tspan>' +
          '<tspan class="aac" x="28" y="327">&#8230;)</tspan>' +
        '</text>' +
        `<line class="aa" x1="212" y1="290" x2="403" y2="290" stroke-width="1.5" marker-end="url(#${a})"/>`,
        // Step 2: api server → LangSmith (upward dashed)
        `<line class="aa" x1="424" y1="118" x2="424" y2="72" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#${a})"/>` +
        '<text class="aat" x="455" y="86" font-size="12">validate API key</text>',
        // Step 3: LangSmith → api server (downward dashed)
        `<line class="aa" x1="438" y1="72" x2="438" y2="118" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#${a})"/>` +
        '<text class="aat" x="455" y="108" font-size="12">User info (who they are)</text>',
        // Step 4: api server → endpoint
        `<line class="aa" x1="447" y1="290" x2="708" y2="290" stroke-width="1.5" marker-end="url(#${a})"/>` +
        '<text class="aat" x="578" y="277" text-anchor="middle" font-size="12">../run/.. is ok</text>' +
        '<rect class="aab" x="710" y="267" width="100" height="46" rx="20" stroke-width="1.5"/>' +
        '<text class="aac" x="760" y="295" text-anchor="middle" font-size="13">request</text>',
      ];
    },
    steps: [
      { tag: 'Step 1 of 4', caption: 'The client sends a request — including a LangSmith API key in the headers — to your API server.' },
      { tag: 'Step 2 of 4', caption: 'The API server sends the key to LangSmith to verify it.' },
      { tag: 'Step 3 of 4', caption: 'LangSmith confirms the key is valid and returns the associated user information.' },
      { tag: 'Step 4 of 4', caption: 'With the key verified, the API server forwards the request to the agent. The check is complete — but there is no per-user isolation.' },
    ]
});

buildDiagram({
    id: 'sd-simple',
    participants: ['Client', 'api server', 'LangSmith'],
    cx: [140, 500, 860],
    bw: 150, bh: 40, tby: 10, bby: 410, vw: 1000, vh: 460,
    buildSteps: function(a) {
      return [
        solidArrow(140, 500, 120, 'client.runs( thread_id, message )', 320, a),
        solidArrow(500, 860, 220, 'validate API key', 680, a),
        dashedArrow(860, 500, 310, 'user info confirmed', 680, a),
        labelBox(500, 356, 290, ['request validated — forwarding to agent']),
      ];
    },
    steps: [
      { tag: 'Step 1 of 4', caption: 'The client sends a request to your API server. The LangSmith API key is included in the request headers.' },
      { tag: 'Step 2 of 4', caption: 'The API server sends the key to LangSmith to verify it and retrieve the associated user information.' },
      { tag: 'Step 3 of 4', caption: 'LangSmith confirms the key is valid and returns user information to the API server.' },
      { tag: 'Step 4 of 4', caption: 'With the key verified, the API server forwards the request to the agent endpoint. This is the only authorization check in place — there is no per-user isolation.' },
    ]
});

buildDiagram({
    id: 'sd-multi',
    participants: ['Client App', 'Auth Provider', 'Agent Server'],
    cx: [140, 500, 860],
    bw: 155, bh: 40, tby: 10, bby: 415, vw: 1000, vh: 465,
    buildSteps: function(a) {
      return [
        solidArrow(140, 500,   75, '1. Login (username/password)', 320, a),
        dashedArrow(500, 140, 115, '2. Return token',              320, a),
        solidArrow(140, 860,  155, '3. Request with token',        500, a),
        labelBox(860, 175, 250, ['4. Validate token', '(@auth.authenticate)']),
        solidArrow(860, 500,  250, '5. Fetch user info',           680, a),
        dashedArrow(500, 860, 285, '6. Confirm validity',          680, a),
        labelBox(860, 300, 250, ['7. Apply access control', '(@auth.on.*)']),
        dashedArrow(860, 140, 380, '8. Return resources',          500, a),
      ];
    },
    steps: [
      { tag: 'Step 1 of 8', caption: 'The client sends credentials (username and password) to the Auth Provider to obtain a session token.' },
      { tag: 'Step 2 of 8', caption: 'The Auth Provider validates the credentials and issues a signed token back to the client.' },
      { tag: 'Step 3 of 8', caption: 'The client makes a request to the Agent Server, attaching the token in the Authorization header.' },
      { tag: 'Step 4 of 8', caption: 'The Agent Server\'s @auth.authenticate hook fires. It begins verifying the incoming token before allowing the request to proceed.' },
      { tag: 'Step 5 of 8', caption: 'Inside the authentication hook, the Agent Server calls the Auth Provider to look up the user associated with this token.' },
      { tag: 'Step 6 of 8', caption: 'The Auth Provider confirms the token is valid and returns the user\'s identity information to the Agent Server.' },
      { tag: 'Step 7 of 8', caption: 'The @auth.on.* hook fires next, applying access control rules — scoping exactly what actions and resources this user is permitted to access.' },
      { tag: 'Step 8 of 8', caption: 'With identity verified and access control enforced, the Agent Server returns the requested resources to the client.' },
    ]
});
</script>
