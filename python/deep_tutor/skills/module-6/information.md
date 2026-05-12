# Module 6 — Reference Material

## What the deepagents CLI is

A command-line tool that builds, runs, and deploys LangGraph agents **without writing Python code**. The student authors config files (`deepagents.toml`, `AGENTS.md`, `skills/`, `mcp.json`) and the CLI generates the underlying LangGraph project (handler code, `langgraph.json`, Docker image) at build time.

Same underlying deployment server (Agent Server). Different developer surface.

Install: `uv tool install deepagents-cli`

## The three commands

| Command | What it does |
|---|---|
| `deepagents init` | Scaffolds a new project — creates `deepagents.toml`, `AGENTS.md`, empty `skills/`, `.env.example` |
| `deepagents dev` | Local development server — starts the agent, serves the bundled UI at `<url>/app`, hot-loads on restart only |
| `deepagents deploy` | Builds and pushes to LangSmith; produces a public deployment URL |

`deepagents dev` does NOT hot-reload on file changes. Skills and `AGENTS.md` are bundled into `_seed.json` at startup. Editing a skill requires restarting `deepagents dev` AND starting a new thread (the seed is read once per thread).

## Project structure

```
my_agent/
├── deepagents.toml          ← config file (replaces langgraph.json)
├── AGENTS.md                ← agent persona / system prompt content
├── mcp.json                 ← MCP tool servers
├── skills/                  ← progressive-disclosure knowledge
│   └── module-1/
│       ├── SKILL.md
│       └── information.md
├── subagents/               ← optional sub-agent definitions
├── user/                    ← per-user memory (managed by CLI)
└── .env                     ← secrets (not committed)
```

## `deepagents.toml` sections

```toml
[agent]
name = "deep_tutor"
model = "anthropic:claude-sonnet-4-6"

[auth]
provider = "anonymous"        # or "supabase", "clerk"

[frontend]
enabled = true                # bundle the React UI
app_name = "Deep Tutor"
subtitle = "Your AI tutor"

[memories]
backend = "filesystem"        # or "store"

[mcp]
config = "mcp.json"
```

The CLI bundler turns this into a generated `langgraph.json` with a handler implementing the chosen auth provider.

## What gets deployed

A CLI deployment exposes:
- All the standard Agent Server routes (`/runs/*`, `/threads/*`, `/assistants/*`, `/store/*`, `/mcp/*`, `/docs`)
- A bundled React frontend at `<deployment-url>/app` (when `[frontend].enabled = true`)
- A health-check JSON at `<deployment-url>/` (root)

The bundled frontend has chat UI, thread list, and a settings panel. It uses the same SDK endpoints any UI would.

## Auth in the CLI

`[auth].provider` selects one of three pre-built `@auth.authenticate` handlers:

| Provider | Behavior | Client header |
|---|---|---|
| `anonymous` | All requests return `{"identity": "anonymous"}`; single shared user | None |
| `supabase` | Validates JWT against Supabase `/auth/v1/user` | `Authorization: Bearer <JWT>` |
| `clerk` | Validates JWT against Clerk | `Authorization: Bearer <JWT>` |

The same `@auth.on.threads` handler is applied for all three — it stamps `metadata.owner = ctx.user.identity` on writes and filters by owner on reads. This is the m5.3 pattern, templated.

Studio bypass is always active (`is_studio_user(ctx.user)` returns `{}` so admins can browse all threads in the dashboard).

## Per-user memory namespace

The CLI bundles a namespace factory that returns `(assistant_id, str(identity))`. So `/memories/user/...` is scoped per **(assistant, user)** — same user on assistant A vs assistant B sees different memory. Auth identity IS the namespace.

This is opinionated for single-assistant-per-user apps. For cross-assistant shared user data (like `deep_tutor`'s student profile that all per-module assistants share), the CLI shape does NOT fit. You'd drop to the code path.

For `provider = "anonymous"`, the literal string `"anonymous"` is used for every request. All anonymous users share one namespace per assistant. The "per-browser UUID cookie" mentioned in some docs is frontend-only (UI scoping) — server-side, anonymous is single-user.

## Memory backends

`[memories].backend`:
- `filesystem` — memories live on the container filesystem; reset on every redeploy
- `store` — memories live in the LangGraph Store; persist across redeploys

For dev work (`deepagents dev`), `backend = "store"` uses an in-memory store that re-seeds from local files on every restart — convenient for content iteration. In production behavior is less well understood; recommend testing before relying on `store` backend for prod.

## MCP support

`mcp.json` follows the standard MCP config shape:

```json
{
  "mcpServers": {
    "langchain-docs": {
      "url": "https://example.com/mcp",
      "transport": "sse"
    }
  }
}
```

CLI deployments support **HTTP/SSE transports only**. Stdio MCP servers (e.g., locally-spawned subprocesses) are NOT supported — they would require Python process management inside the deployment, which the CLI's read-only filesystem doesn't accommodate.

## What the CLI does NOT support

- Custom middleware (e.g., `@dynamic_prompt`)
- Custom HTTP routes (no `http.app` in the generated `langgraph.json`)
- Stdio MCP servers
- Cross-assistant shared user data (per-assistant namespace is hardcoded)
- Hot reload during `deepagents dev`

If a student needs any of these, the answer is: drop to the code path, write Python, use `langgraph.json` directly.

## Hub seeding (one-shot gotcha)

When `memories.backend = "hub"`, the LangSmith Hub repo is seeded **once on the first deploy**. Subsequent deploys do NOT refresh the hub content even if the local files changed. To force a refresh: delete the hub repo and re-deploy, or edit via the Hub UI/agent directly.

This is a known quirk; document it for students so they don't expect git-like sync behavior.

## "Bring Your Own UI" (m6.3)

The CLI's bundled frontend at `<url>/app` is convenient but opinionated. If you want a different UI:

1. The agent is still a standard LangSmith deployment, so SDK calls work normally.
2. Run any UI locally that uses the SDK — `client.threads.create()`, `client.runs.stream()`, etc.
3. Point your UI server's deployment URL at the CLI deployment.

`deep_tutor`'s UI runs against `deep_tutor`'s code-path deployment by default. m6.3 shows it running against the CLI deployment instead — only the deployment URL changes.

Note: CLI deployments don't expose custom HTTP routes, so a UI that depends on `/register`, `/login`, `/modules` (like `deep_tutor`'s app.py routes) needs those routes hosted somewhere else — typically a local server on the student's machine that calls the CLI deployment via the SDK. See `python/m6/ui/app.py`.

## When to choose CLI vs code path

| Use the CLI when | Use the code path when |
|---|---|
| Standard agent with skills + MCP tools | Need custom middleware (`@dynamic_prompt`, etc.) |
| One auth provider per the supported set | Need custom HTTP routes co-deployed |
| Single-assistant-per-user app | Cross-assistant shared per-user data |
| Want the bundled UI | Want a custom UI co-deployed |
| Don't want to write Python | Need stdio MCP or arbitrary Python |

Both produce LangSmith deployments. The CLI is faster to set up; the code path is more flexible.

## TypeScript note

`deepagentsjs` ships only `deepagents-acp` (an ACP server for IDE integration), not an equivalent of the Python `deepagents init/dev/deploy` CLI. m6 is Python-only for now. A TypeScript student doing this module would install the Python CLI — the agent project itself is language-neutral config.
