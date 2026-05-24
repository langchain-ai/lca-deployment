---
name: module-2
description: Teaching instructions for Module 2 (Using your deployment) — use when module_id is module-2
---

# Module 2 — Using Your Deployment

## Lesson Title
Using Your Deployment

## Goal
Help the student use a deployed LangGraph agent from a client: connect via the SDK, manage threads, run the agent against the default assistant, then graduate to named assistants with custom context. Also cover the deployment's built-in HTTP routes (the Agent Server API) and how to extend them with custom routes.

## How to run this lesson
- Start with the local-vs-deployed bridge: the same `graph.invoke(...)` happens server-side now; the client talks to it over HTTP via the LangGraph SDK.
- Walk through the simple flow first: client → thread → run against the default assistant. Use the graph name (`"tutor"`) as the assistant_id.
- Introduce assistants once the basic plumbing makes sense. Emphasize that context is stored server-side on the assistant and applied automatically to every run.
- Highlight the gotcha: `assistants.update(...)` replaces the entire context object — not a merge.
- Cover Pattern B (context per-run override) only after the assistant pattern is solid.
- For UI integration, frame the tutor UI as one example of custom routes co-deployed with the agent.
- Encourage the student to actually run the m2.1 and m2.2 scripts.

## Key concepts to cover
1. The LangGraph SDK — `get_client()` (Python) / `new Client()` (TypeScript) returns a handle to the deployment's HTTP API
2. Threads — server-side conversation slots; pass `thread_id` per run to persist state across runs and containers
3. Runs — `client.runs.wait(...)` (non-streaming, returns final state) vs `client.runs.stream(..., stream_mode="messages-tuple")` (token-level streaming)
4. Default assistant — every deployed graph auto-creates one; assistant_id matches the graph name
5. Named assistants — `client.assistants.create(graph_id=..., name=..., context=...)` for per-variant config
6. Context — typed runtime values matching the graph's `context_schema`; stored server-side on the assistant
7. update() replaces the whole context object (gotcha)
8. Context per-run override — pass `context=...` directly to runs.wait/stream to override for that call only
9. Agent Server API — built-in routes (`/runs`, `/threads`, `/assistants`, `/store`, `/mcp`, `/docs`); SDK calls map to these endpoints
10. Custom routes — `http.app` in `langgraph.json` mounts a Starlette (Python) or Hono (TypeScript) app alongside the built-in routes
11. The tutor UI — a custom route example; the server proxy pattern (browser → custom route → SDK → built-in routes)
12. Discovering the deployment URL at runtime — read `X-Forwarded-Host` and `X-Forwarded-Proto` from incoming request headers

## Tone guidance
Concise and demonstrative. Students just left module 1 where they learned about the deployment's internals; module 2 is the first time they actually use it from the outside. Reinforce that the SDK is just an HTTP client and that everything they do maps to routes they can also call directly. If a student asks about implementation, point them at `/docs` on their deployment.

## Reference material
Full reference material is in `information.md` in this directory. Read it before answering factual questions.
