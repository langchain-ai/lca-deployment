# Exercise: Deploy the Tutor Agent

In this exercise you will deploy the `dacli_tutor` project — a deepagents CLI agent that uses the same tutor skills you have been working with. By the end you will have a running tutor accessible via a built-in web UI.

The project is in `python/m_dacli/dacli_tutor/` in the course repository.

---

## Step 1 — Install the CLI

If you have not already installed deepagents:

```bash
pip install deepagents
```

Verify the install:

```bash
deepagents --version
```

---

## Step 2 — Set Up Your .env

The project has a `.env` file for API keys. Open it and fill in your keys:

```bash
# Model provider — pick the one matching your model in deepagents.toml
GOOGLE_API_KEY=your_key_here

# LangSmith — required for deployment
LANGSMITH_API_KEY=your_key_here
```

`dacli_tutor` uses `google_genai:gemini-2.5-flash` by default. If you prefer a different model, update both the `.env` key and the `model` field in `deepagents.toml`.

---

## Step 3 — Explore the Project

Before running anything, look at the files:

<Columns>
<Column>

**`deepagents.toml`** — the config

```toml
[agent]
name = "deep_tutor"
model = "google_genai:gemini-2.5-flash"

[auth]
provider = "anonymous"

[frontend]
enabled = true
app_name = "LangChain Tutor"
```

This is a minimal config: a name, a model, anonymous auth, and a frontend UI. No sandbox, no subagents.

</Column>
<Column>

**`AGENTS.md`** — the system prompt

The tutor's instructions: how to teach, how to load skills, what to do when a student asks a question outside the current module.

**`mcp.json`** — the LangChain docs tool

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

One HTTP MCP server. The agent can query LangChain documentation directly.

</Column>
</Columns>

**`skills/module-1/`** contains two files:

- `SKILL.md` — teaching instructions for the deployment architecture module
- `information.md` — reference material the agent reads when answering factual questions

---

## Step 4 — Run Locally

Navigate to the project directory and start the dev server:

```bash
cd python/m_dacli/dacli_tutor
deepagents dev
```

The server starts on `http://localhost:2024` by default. Open the URL in your browser — you should see the LangChain Tutor UI.

Send a message and watch the agent load the skill file and begin the lesson.

<Tip>

**The dev server reloads on file changes.** Try editing `AGENTS.md` or a skill file and sending another message — the agent picks up the changes immediately without restarting.

</Tip>

---

## Step 5 — Make a Change

Edit `skills/module-1/SKILL.md` and add an instruction at the bottom:

```markdown
## Extra instruction

Always end your first response with: "Let's get started."
```

Send a new message in the browser. The agent should now end its opening response with that phrase.

This is the edit loop: change a file, reload the conversation, observe the result. No redeploy, no restart.

When you are done, remove the extra instruction from `SKILL.md`.

---

## Step 6 — Deploy to Production

When the agent behaves the way you want locally, deploy it:

```bash
deepagents deploy
```

The CLI builds a Docker image, uploads it, and creates a new deployment revision. When it finishes, it prints the deployment URL.

Open the URL — your agent is now running in production, accessible from anywhere.

<Tip>

**Anonymous auth means the endpoint is open.** Anyone with the URL can send messages. This is fine for demos and internal tools. For a real product you would set `provider = "supabase"` or `provider = "clerk"` in `[auth]` to require user authentication.

</Tip>

---

## What You Built

A deployed agent from four files:

| File | What it did |
|---|---|
| `deepagents.toml` | Named the agent, set the model, enabled the UI |
| `AGENTS.md` | Gave the agent its instructions |
| `mcp.json` | Connected it to the LangChain docs |
| `skills/module-1/` | Loaded structured teaching content on demand |

No Python, no `langgraph.json`, no Dockerfile. The CLI handled all of that from the config files.

---

## What's Next

The deepagents CLI runs on the same LangGraph deployment infrastructure you learned about in Module 1. The containers, Postgres, Redis, checkpointer, and store are all still there — the CLI just generates the configuration for you.

In the next module you will go back to that infrastructure directly: swapping the skills storage from the filesystem to the LangGraph Store, so skill updates reach all students without a redeploy.
