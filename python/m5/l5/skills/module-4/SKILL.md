---
name: module-4
description: Teaching instructions for Module 4 (Storage) — use when module_id is module-4
---

# Module 4 — Storage

## Lesson Title
Memory and Storage in LangGraph Deployments

## Goal
Help the student understand the three memory mechanisms in a LangGraph deployment (checkpointer, Store, filesystem), how to read and write the Store from a client, and how deepagents wraps these primitives behind a backend abstraction.

## How to run this lesson
- Start with the three memory types: each has a different scope and persistence story. Make sure the student can name them and say what each holds before diving into APIs.
- The **checkpointer** is automatic — no API to call directly. Mention it but don't dwell.
- The **Store** is the focus: cross-thread, persistent, namespaced. The SDK's `client.store.put_item / get_item / search_items` is how the UI reads/writes student profiles.
- The **filesystem** is read-only for runtime data (it's baked into the Docker image), useful for static content like skills and AGENTS.md.
- After the SDK surface is solid, introduce deepagents' BackendProtocol. The same `ls`/`read`/`download_files` interface is implemented by FilesystemBackend, StoreBackend, and StateBackend — swapping backends changes where data lives without changing middleware code.
- Reinforce the tutor as a worked example: register/login writes profile + sessions to the Store; the dynamic prompt reads the profile on every model call; skills are loaded from the filesystem by SkillsMiddleware.

## Key concepts to cover
1. Three memory types: checkpointer (per-thread, automatic), Store (cross-thread, namespaced, persistent), filesystem (read-only at runtime, image-baked)
2. Store namespace — a tuple keying into a per-deployment KV space; in deep_tutor it's `(email_with_dot_to_underscore,)`
3. SDK Store API — `put_item`, `get_item`, `search_items`, `delete_item`, `list_namespaces`
4. The `langgraph_auth_user` and the `runtime.store` injection inside graph nodes — direct access, no HTTP
5. deepagents `BackendProtocol` — uniform interface (`ls`, `read`, `write`, `download_files`)
6. FilesystemBackend with `virtual_mode=True` and `root_dir` — `/skills/` maps to `<root>/skills/`
7. StoreBackend — same interface, data lives in the Store instead of disk
8. StateBackend — same interface, data lives in agent state (per-thread)
9. SkillsMiddleware and MemoryMiddleware — what `create_deep_agent` wires up internally
10. Why skills are read on demand (`read_file` tool) instead of all loaded upfront — progressive disclosure for token economy
11. Why the filesystem is fine for read-only data but problematic for writes — a thread may execute across multiple containers
12. Permissions — `FilesystemPermission(operations=["write"], paths=["/skills/**"], mode="deny")` keeps the agent from clobbering skill files at runtime

## Tone guidance
Concrete and example-driven. The student has already used the SDK in module 2; now we're extending those calls with Store operations. When explaining backends, lead with what changes (where data lives) and what stays the same (the middleware code).

## Reference material
Full reference material is in `information.md` in this directory. Read it before answering factual questions.
