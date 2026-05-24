---
name: module-5
description: Teaching instructions for Module 5 (Authentication and Authorization) — use when module_id is module-5
---

# Module 5 — Authentication and Authorization

## Lesson Title
Authentication and Authorization in a Multi-Tenant Deployment

## Goal
Walk the student through adding real auth to a LangGraph deployment: first identifying users (`@auth.authenticate`), then scoping their access to resources (`@auth.on`), then swapping the toy token store for a real identity provider, then wiring it into the tutor agent.

## How to run this lesson
- Start with the **distinction**: authentication answers "who is this?", authorization answers "what can they do?". The two decorators map cleanly to those two questions.
- Walk through m5.1's request-pipeline diagram before touching code. Students should know where in the request lifecycle the auth handler runs.
- For m5.2 (local auth), emphasize that `@auth.authenticate` is the ONLY interception point and that its return value flows into the rest of the request.
- For m5.3 (private conversations), the key idea is metadata stamping on writes + filter dict on reads. Bob gets a 404 (not 403) on Alice's thread because the filter makes the thread invisible — there's nothing to forbid.
- For m5.4 (Supabase), call out that the `@auth.on` handler from m5.3 does NOT change — only `@auth.authenticate` is swapped. This is the payoff for keeping auth and authz decoupled.
- For m5.5 (tutor), reinforce that `deep_tutor`'s `store_namespace` is email-derived (independent of auth identity). Auth gates "can this user call?" while namespace decides "where does their data live?". They meet in `@auth.on.store()`.

## Key concepts to cover
1. `@auth.authenticate` — receives the raw `Authorization` header, returns a `MinimalUserDict` with at minimum `identity`, or raises `Auth.exceptions.HTTPException(401)`
2. `@auth.on` — fires after authenticate, on every resource access; stamps metadata on writes and returns a filter dict on reads
3. The `langgraph.json` registration — `auth.path = "./auth.py:auth"` is what wires the handler in
4. Scoped vs broad handlers — `@auth.on.threads.create` is more specific than `@auth.on`; most specific wins
5. Why Bob gets a 404 (filter, not deny) — the resource is invisible, not forbidden
6. `@auth.on.store()` is different — no automatic filter, the handler asserts/raises to allow/block; namespace[0] convention
7. Swapping the token store — from hardcoded dict (m5.2) to Supabase JWT validation (m5.4); only `@auth.authenticate` changes
8. Two access paths to the authenticated user — `ctx.user.identity` in `@auth.on` handlers, `runtime.server_info.user.identity` in graph nodes
9. The OAuth2 three-role model — Client App, Auth Provider, Agent Server; the Agent Server never stores credentials
10. Auth vs namespace in `deep_tutor` — auth gates calls; `context.store_namespace` (email-derived) decides where data lives; meeting point is `@auth.on.store()`

## Tone guidance
Precise about the contract — students often confuse authentication with authorization. Hammer the separation. When discussing examples, refer to Alice/Bob/admin (the lesson personas) so the student can connect explanations to concrete lab runs.

## Reference material
Full reference material is in `information.md` in this directory. Read it before answering factual questions.
