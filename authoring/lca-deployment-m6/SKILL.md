---
name: lca-deployment-m6
description: "Full context for authoring Module 7 of lca-deployment — Managed Deep Agents. Covers what the dacli_tutor exercise was, what changes for MDA, open questions, and key API details."
---

# LCA Deployment — Module 7: Managed Deep Agents

## Course-wide Conventions

- **No `<RunCode>` blocks.** Show commands as plain fenced `bash` code blocks only. The `<RunCode>` pulldown is not used in this course.
- **No `<Tabs>` for language selection.** The course is Python-only; no Python/TypeScript tab wrapping.
- **Block markers** (`<!-- block: ... -->`) on every code and result block for targeted editing.

---

## Course Context

Module 7 teaches Managed Deep Agents (MDA), LangSmith's hosted runtime for
deploying deep agents without standing up a custom agent server. Module 6
(dacli_tutor / deepagents.toml) stays intact in the working repo for comparison.

**Course repo (do not modify):** `/Users/geoffladwig/Documents/Github/lca-deployment`
**Working repo:** `/Users/geoffladwig/Documents/Github/deployment-update/lca-deployment`

---

## Lesson Structure

Two lessons:
1. **m7.1 — Conceptual Overview** (no code)
2. **m7.2 — Lab** (deploy the tutor agent, build and run the UI app)

No m7.3 — the old "Bring Your Own UI" is now part of the lab.

---

## The Exercise: dacli_tutor → MDA Tutor

The exercise is the same tutor agent from the old m6, migrated to Managed Deep Agents.

### What the tutor is

A LangChain Academy deployment course tutor. Students talk to it to learn
course material. It teaches from lesson skills using progressive disclosure.

**AGENTS.md (unchanged):**
```
You are a tutor for the LangChain Academy deployment course. You teach students
how to deploy LangGraph agents to production — covering architecture, storage,
auth, and the full deployment lifecycle.

Teaching style:
- Empathetic but concise. Meet the student where they are.
- Don't lecture unprompted — respond to what the student asks.
- After explaining 2–3 concepts, consider quizzing the student.

How lessons work:
Each lesson is a module with its own skill file. On the first turn of a new module:
1. Read the SKILL.md for the current module — it contains teaching instructions.
2. Follow those instructions. It tells you what concepts to cover and in what order.
3. When you need to answer a factual question, read information.md from the same directory.

Never read module files unless you need them — load on demand.
```

### Model

`anthropic:claude-sonnet-4-6` — students already have an Anthropic key from
the rest of the course. Do NOT use `openai:gpt-5.5` (would require a new key).

### Skills structure (unchanged concept, new location)

```
my-agent/
  agent.json
  AGENTS.md
  skills/
    module-1/
      SKILL.md          ← teaching instructions (name + description frontmatter required)
      information.md    ← reference material (read on demand by agent)
```

Each `SKILL.md` requires YAML frontmatter:
```yaml
---
name: module-1
description: Teaching instructions for Module 1 (LangGraph Deployment Architecture) — use when module_id is module-1
---
```

Progressive disclosure: at startup the agent sees only `name` + `description`
for every skill. When a student asks about a module, the agent reads the full
`SKILL.md` then `information.md` on demand.

---

## What Changed: Old → New

| Old (deepagents.toml) | New (agent.json) |
|---|---|
| `deepagents.toml` | `agent.json` |
| `mcp.json` | `tools.json` |
| `deepagents dev` (local server) | `deepagents deploy` only — no local server |
| `[auth] provider = "anonymous"` | No auth config — handled by platform |
| `[frontend] enabled = true` | No bundled UI — build your own |
| `[memories] backend = "store"` | No memories config — platform handles it |
| `langgraph-sdk` in app.py | Raw `httpx` in app.py |
| `assistant_id = "agent"` | `agent_id = "<uuid from deploy>"` |

### agent.json for this exercise

```json
{
  "name": "deep-tutor",
  "description": "LangChain Academy deployment course tutor.",
  "model": "anthropic:claude-sonnet-4-6",
  "backend": {
    "type": "default"
  }
}
```

### Deploy command

```bash
deepagents deploy
```

Prints `agent_id` on success. Student sets this as `AGENT_ID` env var.

---

## The UI App (app.py rewrite)

The old `app.py` used `langgraph-sdk`. MDA uses raw `httpx` with `X-Api-Key`.

### Key API calls

**Create thread:**
```python
POST https://api.smith.langchain.com/v1/deepagents/threads
Headers: X-Api-Key: <LANGSMITH_API_KEY>
Body: {"agent_id": "<agent_id>", "options": {"test_run": false, "skip_memory_write_protection": false}}
Response: {"id": "<thread_id>", "agent_id": "...", "status": "idle", ...}
```

**Stream a run:**
```python
POST https://api.smith.langchain.com/v1/deepagents/threads/<thread_id>/runs/stream
Headers: X-Api-Key: <LANGSMITH_API_KEY>, Accept: text/event-stream
Body: {
  "agent_id": "<agent_id>",
  "messages": [{"role": "user", "content": "..."}],
  "stream_mode": ["messages-tuple"],
  "stream_subgraphs": false
}
Response: SSE stream
```

**Note:** `assistant_id` is rejected — must use `agent_id`. The platform
translates it internally.

### Auth model in app.py

Same as old app: faked auth. Any email → stable thread (stored in-process dict).
Backend holds `LANGSMITH_API_KEY`; end users never see it.

```
User → app.py (holds API key) → MDA API → Context Hub / agent runtime
```

Per-user isolation = one thread per email address (tracked in `threads_by_email`).

### .env for the exercise

```
LANGSMITH_API_KEY=lsv2_...
AGENT_ID=<uuid printed by deepagents deploy>
DEEPAGENTS_BASE_URL=https://api.smith.langchain.com/v1/deepagents
```

---

## Key Concepts for m6.1 (Conceptual Lesson)

1. **What MDA is** — hosted runtime, no custom server needed
2. **Context Hub** — versioned store for instructions, skills, policies
   - Blog: https://www.langchain.com/blog/introducing-context-hub
   - Concepts: https://docs.langchain.com/langsmith/context-engineering-concepts
3. **Project structure** — `agent.json`, `AGENTS.md`, `skills/`, `tools.json`
4. **Progressive disclosure** — how skills load (name+desc at startup, full body on invoke)
5. **`deepagents deploy`** — creates agent + Context Hub repo + tracing project in one shot
6. **No bundled UI** — you build it; MDA is API-only at runtime
7. **Auth model** — `X-Api-Key` only; workspace-scoped; backend proxy pattern for apps
8. **When to use MDA vs standard deployment** — MDA = simple, no custom code needed;
   standard deployment = advanced auth, isolation controls, full Agent Server APIs

## Docs references

- Overview: https://docs.langchain.com/langsmith/managed-deep-agents-overview
- Deploy: https://docs.langchain.com/langsmith/managed-deep-agents-deploy
- Invoke: https://docs.langchain.com/langsmith/managed-deep-agents-invoke
- CLI ref: https://docs.langchain.com/langsmith/managed-deep-agents-cli
- API ref: https://docs.langchain.com/langsmith/managed-deep-agents-api

---

## Internal Backend Architecture (confirmed from source)

MDA runs a `CompositeBackend` internally. The user cannot configure the routes — only the
default (catch-all) backend via `backend.type` in `agent.json`:

```
backend.type = "default"           → StateBackend  (ephemeral per-thread scratch)
backend.type = "thread_scoped_sandbox"  → LangSmithSandbox (code execution, new sandbox per thread)
backend.type = "agent_scoped_sandbox"   → LangSmithSandbox (code execution, shared across threads)
```

Platform-wired routes (always present, regardless of `backend.type`):
- `/skills/`, `AGENTS.md` → `ContextHubBackend` (backed by the Context Hub repo created at deploy time)
- `/memories/` → `StoreBackend` (auto-provisioned; this is why cross-thread memory works without any app code)
- everything else → whatever `backend.type` selects

`skip_memory_write_protection` (thread creation option) controls writes to `/memories/`:
- `false` (default): platform interrupts for human approval before the agent writes
- `true`: agent can write to `/memories/` without approval

**For the tutor exercise:** `backend.type = "default"` is correct. No code execution needed.

---

## Open Questions (as of 2026-06-06)

- How fast is the deploy turnaround? Students iterate by redeploying — is the
  cycle fast enough for a lab, or do we need to warn them to expect a wait?
- Scope of lab: MCP tools and subagents, or just the basic deploy-and-invoke loop?
  (Recommendation: keep the lab focused on basic loop for clarity.)
