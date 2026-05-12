---
name: module-6
description: Teaching instructions for Module 6 (Deepagents CLI) — use when module_id is module-6
---

# Module 6 — Deploying with the Deepagents CLI

## Lesson Title
Deploying Agents Without Writing Code: the Deepagents CLI

## Goal
Show the student the alternative path: a "no Python" deployment that uses config files (`deepagents.toml`, `AGENTS.md`, `skills/`, `mcp.json`) instead of code. Cover the three commands (`init`, `dev`, `deploy`), what the deployment exposes (built-in routes + bundled React frontend), the constraints (no custom middleware, no custom HTTP routes, fixed namespace shape), and the "bring your own UI" pattern for when the bundled frontend isn't enough.

## How to run this lesson
- Frame as a contrast with module 1: the code path is flexible but verbose; the CLI is convention-based and fast. Both produce a LangSmith deployment behind the scenes.
- m6.1 (concepts): walk the student through `deepagents.toml` sections, the files (AGENTS.md, mcp.json, skills/, subagents/, user/), and the three commands. Mention that under the hood the CLI generates a `langgraph.json` + handler code from the template.
- m6.2 (exercise): hands-on with `dacli_tutor`. Install CLI, set up `.env`, run `deepagents dev`, edit a skill, deploy. The deployment exposes both the standard API routes AND the bundled React UI at `/app`.
- m6.3 (bring your own UI): use `deep_tutor`'s UI locally pointed at the CLI deployment. The point is API compatibility — same SDK calls work against any deployment, so a UI built for one runs against another with just a URL change.
- Hammer the contrast: code path = Python code + langgraph.json; CLI = config files only, no Python. Same underlying deployment server.

## Key concepts to cover
1. `deepagents.toml` — the config file that replaces `langgraph.json` for CLI deploys
2. `AGENTS.md` — agent persona, loaded as system prompt
3. `skills/` — progressive-disclosure knowledge directories
4. `mcp.json` — MCP tool servers; CLI supports HTTP/SSE only (no stdio)
5. `subagents/` — optional sub-agent definitions
6. `user/` — per-user memory directory; populated by the CLI's user-memory scoping
7. The three commands: `deepagents init` (scaffold), `deepagents dev` (local), `deepagents deploy` (production)
8. What the CLI deployment exposes: standard Agent Server API + bundled React UI at `<url>/app`
9. `[auth] provider` options — `anonymous`, `supabase`, `clerk`; per-user identity comes from `runtime.server_info.user.identity`
10. The per-user namespace shape — `(assistant_id, user_identity)`; auth identity IS the namespace
11. CLI constraints — no custom middleware, no custom HTTP routes, no Python code; trade flexibility for speed
12. The "bring your own UI" pattern — local UI server uses the SDK to talk to the CLI deployment
13. The seed file (`_seed.json`) — skills + AGENTS.md are bundled at startup; no hot reload during `deepagents dev`
14. Hub seeding — LangSmith Hub repo is seeded once per first deploy; refreshes require deleting the hub or editing via Hub UI

## Tone guidance
Contrast-driven. Students just spent five modules on the code path. The CLI is the same deployment underneath — but the developer surface is config-only. When the student asks "but how do I do X?", check whether X is supported (most things are) or excluded by the CLI's opinions (custom middleware, custom routes, stdio MCP). If excluded, the answer is "drop to the code path."

## Reference material
Full reference material is in `information.md` in this directory. Read it before answering factual questions.
