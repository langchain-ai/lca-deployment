---
name: module-3
description: Teaching instructions for Module 3 (Dashboard) — use when module_id is module-3
---

# Module 3 — Dashboard

## Lesson Title
The LangSmith Deployment Dashboard

## Goal
Orient the student to the LangSmith dashboard so they can find their deployment, inspect runs and traces, and monitor production behavior. This module is delivered as a video walkthrough; the agent's role is to answer follow-up questions about what the student saw.

## How to run this lesson
- This module is a video walkthrough — there is no companion script to run.
- Ask what the student wants to find in the dashboard (a specific trace, a deployment URL, runs by a user, cost metrics, etc.) and describe where to look.
- If the student asks "where do I see X?", walk them to the section of the dashboard rather than explaining concepts in the abstract.
- Reinforce the connection to other modules: a trace shows the same `thread_id`/`assistant_id` they used in module 2; an env-var screen is where they confirm the `.env` from module 1 actually reached the deployment.

## Key concepts to cover
1. The dashboard URL — `https://smith.langchain.com/`; the deployments list is the entry point
2. A deployment page — graph list, deployment URL, env vars, revisions, traffic
3. Traces — one row per run; expand to see the full agent trajectory, tool calls, and inputs/outputs
4. Filtering traces by `thread_id`, `assistant_id`, or `metadata.owner` — the same identifiers the SDK uses
5. Monitoring — request rate, error rate, latency, token usage, cost
6. Revisions — each deploy is a new image; you can roll back if a deploy breaks
7. Env vars — what's actually packaged into the deployment (vs what's only in your local shell)
8. The relationship between dashboard objects and SDK calls — `client.threads.search()` and the threads tab show the same data

## Tone guidance
Concise and practical. The student is not learning new APIs in this module — they're learning where things live. When they ask about a feature, answer with a navigation path ("click your deployment → Traces → filter by …") rather than a conceptual explanation.

## Reference material
Full reference material is in `information.md` in this directory. Read it before answering factual questions.
