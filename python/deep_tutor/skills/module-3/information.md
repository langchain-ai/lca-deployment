# Module 3 — Reference Material

## What this module is

A video walkthrough of the LangSmith deployment dashboard. The dashboard is the operational view of a deployment — everything the student deployed in module 1 and used via the SDK in module 2 shows up here as data they can browse.

There is no companion script. The agent's job is to answer questions about what the student saw in the video and help them find specific things in the dashboard.

## The dashboard entry point

URL: `https://smith.langchain.com/`

Top-level navigation:
- **Projects** — tracing projects (where free-form traces and evals live)
- **Deployments** — LangGraph deployments (the focus of this module)
- **Datasets**, **Prompts**, **Hub** — adjacent features not covered here

The deployments list shows every deployment the student has access to. Each row links to a deployment page.

## A deployment page

When the student clicks into a deployment, they see:

- **Overview** — graph list (each entry is one of the `graphs` from `langgraph.json`), deployment URL, current revision
- **Traces** — one row per run; the operational record of what the agent has been doing
- **Threads** — server-side conversation slots; one row per `thread_id`
- **Assistants** — named assistants tied to graphs; one row per `assistant_id` (including the auto-created default)
- **Revisions** — every `langgraph deploy` produces a new revision; older revisions can be activated to roll back
- **Settings / Env Vars** — secrets and config packaged into the container; `LANGSMITH_API_KEY` is a special case (used by `langgraph deploy` itself, not packaged unless explicitly set)
- **Monitoring** — request rate, latency, error rate, cost dashboards

## Traces

A trace is one full run captured for observability. Each trace shows:
- The full agent trajectory (every LLM call, tool call, middleware step)
- Inputs and outputs at each step, with token counts
- Latency per step
- Metadata — the same `metadata` dict the SDK sees, including `thread_id`, `assistant_id`, and anything written by `@auth.on` (e.g., `owner`)

Filtering: by date range, status (error/success), thread_id, assistant_id, custom metadata keys. The same identifiers the SDK uses are the join keys to find traces.

## Monitoring dashboard

The monitoring tab is the production view:
- Request rate, error rate, latency percentiles (p50/p95/p99)
- Token usage and cost per model
- Per-graph and per-assistant breakdowns

For cost charts to populate correctly when ingesting traces via the SDK, use two-step `client.batch_ingest_runs()` — see the bulk-upload pattern docs.

## Revisions

Every `langgraph deploy` (code path) or `deepagents deploy` (CLI path) creates a new revision. Each revision is an immutable image. The dashboard lets you:
- See the diff between revisions
- Activate any prior revision (roll back)
- Inspect the build logs for each revision

## Env vars vs API keys

Two distinct uses of credentials:
- **`.env` packaged into the deployment** — vars the agent reads at runtime (e.g., `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `JWT_SECRET`). Set in the dashboard's env vars panel or shipped via the `.env` field in `langgraph.json`.
- **Local `LANGSMITH_API_KEY`** — what `langgraph deploy` uses to authenticate with the LangSmith API. Lives in the developer's local shell environment, NOT packaged in the container.

If a deployment fails at runtime with a 500 on a request that depends on an env var, check the dashboard env vars panel first.

## Dashboard ↔ SDK mapping

The dashboard reads the same underlying data the SDK writes. Same objects, different surface:

| Dashboard | SDK |
|---|---|
| Threads tab | `client.threads.search()` / `client.threads.get()` |
| Assistants tab | `client.assistants.search()` / `client.assistants.get()` |
| Traces tab | Run records, accessible via `client.runs.*` |
| Env vars panel | Read at runtime via `os.environ[...]` inside the agent |

Knowing this mapping makes the dashboard a debugging tool: see something weird in a trace, then reproduce it from a client script using the same IDs.

## Quiz hooks (for the agent to use if asked)

- "Where do I find the URL my client should connect to?" → Deployment Overview → Deployment URL
- "How do I see what a user did last week?" → Traces → filter by `metadata.owner` and date range
- "I deployed but it's broken — what changed?" → Revisions → compare with prior, or roll back
- "Is my `JWT_SECRET` actually in the deployment?" → Settings → Env Vars panel
- "How much did this thread cost me?" → Monitoring → filter by `thread_id` or open the trace and sum tokens
