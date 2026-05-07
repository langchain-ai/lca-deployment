# Deploying with the Deep Agents CLI

The previous module covered the full LangGraph deployment stack: containers, workers, Postgres, Redis, `langgraph.json`. All of that infrastructure runs underneath every deployment — including ones built with the deepagents CLI.

The deepagents CLI is a higher-level tool. Instead of writing Python to define your graph and `langgraph.json` to configure the image, you configure the agent in a handful of files — a system prompt, a TOML config, and optionally some skills and MCP tools. The CLI generates the graph and the deployment config from those files.

---

## Project Structure

A deepagents project is a directory with a convention-based layout. The CLI discovers files by name — no registration required.

```
my-agent/
├── deepagents.toml    # Agent config (required)
├── AGENTS.md          # System prompt (required)
├── .env               # API keys
├── mcp.json           # MCP servers (optional)
├── skills/            # Skills directory (optional)
├── subagents/         # Sub-agents (optional)
└── user/              # Per-user writable memory (optional)
```

Two files are required. Everything else is optional and loaded only if present.

---

## deepagents.toml

The main config file. It has four sections:

```toml
[agent]
name = "my-agent"
model = "google_genai:gemini-2.5-flash"

[auth]
provider = "anonymous"

[frontend]
enabled = true
app_name = "My Agent"

[sandbox]
provider = "langsmith"
scope = "thread"
```

| Section | Required | What it configures |
|---|---|---|
| `[agent]` | Yes | Deployment name and model |
| `[auth]` | No | Who can call the agent (`anonymous`, `supabase`, `clerk`) |
| `[frontend]` | No | Deploy a built-in React UI |
| `[sandbox]` | No | Code execution environment for the agent |

**`[agent]`** is the only required section. Name and model use the same `provider:model` format as `init_chat_model` in LangGraph.

**`[auth]`** controls access. `anonymous` deploys an open endpoint — useful for demos and internal tools. `supabase` and `clerk` gate the API with real user tokens; threads and memory are automatically scoped per user.

**`[frontend]`** deploys a React chat UI alongside the agent API. Set `app_name` to customize the header.

**`[sandbox]`** provisions a code execution environment for the agent. The `langsmith` provider uses LangSmith's managed sandbox; `daytona`, `modal`, and `runloop` are third-party options. `scope = "thread"` creates a fresh sandbox per conversation; `scope = "assistant"` keeps one sandbox alive across all conversations.

---

## AGENTS.md

The system prompt. It is loaded at the start of every session and stays in context for the entire conversation. Write it the same way you would write a system prompt for any agent — instructions, persona, constraints.

```markdown
# Agent Instructions

You are a helpful assistant. Answer questions clearly and concisely.
Keep your responses focused on what the user asked.
```

AGENTS.md is read-only at runtime in the main agent. Skills can extend the agent's knowledge without changing the base prompt.

---

## mcp.json

Configures MCP (Model Context Protocol) servers — external tools the agent can call.

```json
{
  "mcpServers": {
    "docs": {
      "url": "https://docs.langchain.com/mcp",
      "transport": "http"
    }
  }
}
```

One constraint: **only HTTP and SSE transports are supported**. Stdio transports (which spawn a local process) are rejected at bundle time — there is no local process to spawn in a deployed container. Every MCP server must be reachable over HTTP.

---

## skills/

The `skills/` directory works the same way it does in a full LangGraph deployment. Each subdirectory is a skill, and the `SKILL.md` file in that directory contains instructions the agent loads on demand.

```
skills/
└── module-1/
    ├── SKILL.md        # Teaching instructions for this module
    └── information.md  # Reference material
```

The agent can read skill files at runtime via file I/O — the same way a LangGraph deployment with `FilesystemBackend` works. Skills let you update agent knowledge without touching the system prompt.

---

## user/

The `user/` directory is per-user writable memory. If `AGENTS.md` exists inside `user/`, it seeds as a template for each new user. The agent can read and write files under `user/` at runtime — changes persist across sessions for that user.

This is the mechanism for building agents that learn and adapt to individual users over time.

---

## The Three Commands

```bash
deepagents init [name]              # Scaffold a new project
deepagents dev [--port 2024]        # Local development server
deepagents deploy                   # Build and deploy to production
```

**`init`** creates a new project directory with the required files. Use it to start fresh.

**`dev`** starts a local server that reloads on file changes. This is your inner loop — make changes, test in the browser or via API, repeat. The dev server exposes the same API as the production deployment.

**`deploy`** builds a new image and creates a production revision. Every `deploy` call is a fresh deployment — it does not update in place. Use `dev` for iteration; `deploy` when you're ready to ship.

---

## Check Your Understanding

<MCQ
    question="Which file in a deepagents project defines the agent's system prompt?"
    choices='["deepagents.toml", "AGENTS.md", "mcp.json", "skills/SKILL.md"]'
    correctIndex={1}
    explanation="AGENTS.md is the system prompt. It is loaded at session start and stays in context for the entire conversation. deepagents.toml is the config file; mcp.json configures tools; SKILL.md extends the agent's knowledge for a specific topic."
/>

<MCQ
    question="You want to add a web search tool to your deepagents project. The tool's server only supports stdio transport. What happens?"
    choices='["It works — deepagents supports all MCP transports", "It is rejected at bundle time — stdio is not supported in deployment", "It works locally with deepagents dev but fails on deploy", "You need to add it to deepagents.toml instead of mcp.json"]'
    correctIndex={1}
    explanation="Only HTTP and SSE transports are supported. Stdio spawns a local process, which is not possible in a deployed container. You need an MCP server reachable over HTTP."
/>

<MCQ
    question="Which section of deepagents.toml is required?"
    choices='["[auth]", "[frontend]", "[agent]", "[sandbox]"]'
    correctIndex={2}
    explanation="Only [agent] is required — it sets the deployment name and model. The other three sections are optional and only included when you need their features."
/>

<MCQ
    question="You run deepagents deploy twice in a row without making any changes. What happens?"
    choices='["Nothing — deploy detects no changes and skips the build", "It creates two new production revisions", "It updates the existing deployment in place", "It fails with a conflict error"]'
    correctIndex={1}
    explanation="Every deploy call builds a new image and creates a new revision. There is no diff-based skip. Use deepagents dev for iteration — only deploy when you intend to ship."
/>

---

## What's Next

- **L2** — Exercise: walk through the `dacli_tutor` project. Explore the config files, run the agent locally with `deepagents dev`, and deploy it to production.
