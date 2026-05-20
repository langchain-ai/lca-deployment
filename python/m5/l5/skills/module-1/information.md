# Module 1 — Reference Material

## The Three Layers

LangChain's stack has three distinct layers:

- **LangChain** — the framework. High-level abstractions for models, tools, and agent loops.
- **LangGraph** — the runtime. Low-level graph execution engine handling durable execution, checkpointing, streaming, and human-in-the-loop.
- **LangGraph Deployment** — the hosting platform. Infrastructure that runs LangGraph agents in production: containers, scaling, persistence, and the API layer.

These are often conflated because they come from the same company. They are different things.

## Control Plane and Data Plane

LangSmith has two planes:

- **Control plane** — shared infrastructure managed by LangChain. The management layer: UI and APIs for creating, updating, monitoring, and deleting deployments. Never touches run data directly.
- **Data plane** — per-customer infrastructure. Each deployment is a fully isolated Agent Server instance with its own Postgres, Redis, and containers.

## The Agent Server

The Agent Server is the name for an entire deployment instance — not a single component. It includes API servers, worker containers, Postgres, and Redis together.

It is **not truly serverless**. Workers are always-on containers that run and cost money even when idle. Minimum: 1 API server + 1 worker container. This is the price of no cold starts.

## The Two Container Pools

Every deployment has two kinds of containers, both built from the same Docker image:

- **API Server containers** — handle incoming HTTP requests (creating runs, fetching thread state, streaming results). Do not execute agent code.
- **Worker containers** — the execution engine. Listen to the task queue, execute graph code, write checkpoints. Each worker has a queue loop dispatching runs to worker processes. Each worker process handles up to 10 concurrent runs (configurable via `N_JOBS_PER_WORKER`).

The two pools scale independently.

## How a Run Flows Through the System

1. Client sends request to an API Server
2. API Server writes the run to Postgres
3. API Server drops a sentinel value on a Redis list (the doorbell)
4. A worker wakes up, reads run data from Postgres
5. Worker executes the agent graph
6. Worker writes checkpoints to Postgres after each node
7. Worker broadcasts streaming output via Redis PubSub
8. API Server subscribes to PubSub and forwards events to client via SSE
9. On completion, worker updates run status and releases its job slot

## Postgres and Redis

- **Postgres** — durable source of truth. Stores threads, runs, assistants, cron jobs, checkpoints, and the long-term memory store. No run data ever lives in Redis. Always required.
- **Redis** — ephemeral signalling layer. Wakes up workers (sentinel on list), broadcasts streaming output (PubSub), signals run cancellation. No user data stored. Everything in Redis is throwaway.

## The Three Persistence Stores

All three default to Postgres but can be configured separately:

- **Core data** (threads, runs, assistants, cron jobs) — always Postgres, no alternative.
- **Checkpointer** — saves graph execution state after each node. Makes runs durable: if a worker crashes, the next worker resumes from the last checkpoint. Default: Postgres; can switch to MongoDB or custom.
- **Store** — long-term memory persisting across threads. Your agent reads and writes it from code. Default: Postgres; can be replaced. Can be configured with semantic search.

Key distinction: the checkpointer is internal infrastructure you never touch directly. The store is also internal but is a first-class programming interface for your agent code.

## langgraph.json

The `langgraph.json` file is the blueprint for building the Docker image. It configures:

| Section | What it configures |
|---|---|
| `dependencies`, `base_image`, `python_version` | Docker image build |
| `graphs` | Assistants (one entry per agent graph) |
| `checkpointer` | Backend choice, TTL, deserialization |
| `store` | Semantic search index, TTL |
| `http`, `auth`, `webhooks` | API Server behaviour |
| `env` | Environment variables |

## Quiz Questions

1. What are the three layers of the LangChain stack? What does each one do?
2. What is the difference between the control plane and the data plane in LangSmith?
3. What does the Agent Server include? Is it truly serverless?
4. What is the difference between API Server containers and Worker containers?
5. Walk me through what happens when a client sends a request to a deployed LangGraph agent.
6. What does Postgres store? What does Redis store?
7. What is the difference between the checkpointer and the store?
8. What does `langgraph.json` configure?
