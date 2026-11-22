# LangSmith Deployment — Python

You can find the course at [LangSmith Deployments](https://academy.langchain.com/courses/take/langsmith-deployments).

## Setup

### Prerequisites

- [LangSmith account](#getting-started-with-langsmith)
  - To deploy to the cloud you will need a Plus plan or above
    - You can deploy locally with a [Developer account (free)](https://www.langchain.com/pricing)
- Python 3.11–3.13
- [uv](https://docs.astral.sh/uv/) package manager — see [Installing uv](#installing-uv)
- Docker (optional, recommended) — `langgraph deploy` uses Docker to build the container locally. Without it the CLI falls back to a remote build in LangSmith's cloud, which works fine but is slower. [Install Docker Desktop](https://www.docker.com/products/docker-desktop/).

### Installation

Clone the repository and move to the `python` directory:

```bash
git clone https://github.com/langchain-ai/lca-deployment.git
cd lca-deployment/python
```

Make a copy of `.env.example`:

```bash
cp .env.example .env
```

Choose one model authentication path. Direct provider keys remain the default: fill in [LangSmith](#getting-started-with-langsmith) for deployment access and Anthropic for the default model in `.env`:

```bash
# LangSmith — tracing and deployment
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=lca-deployment

# Model provider API keys — set the one you're using
ANTHROPIC_API_KEY=your-anthropic-api-key
# OPENAI_API_KEY=your-openai-api-key
# GOOGLE_API_KEY=your-google-api-key
```

Course scripts call `load_dotenv(override=True)`, so values in `.env` take precedence over any conflicting environment variables already set in your shell.

### Optional: LangSmith LLM Gateway

If your workspace administrator has enabled [LLM Gateway](https://docs.langchain.com/langsmith/llm-gateway-direct-model-access) and configured access to your chosen provider and model, replace the model-provider key requirement for supported chat calls with:

```dotenv
LANGSMITH_GATEWAY=true
LANGSMITH_GATEWAY_API_KEY=your-gateway-enabled-langsmith-key
```

`LANGSMITH_GATEWAY_API_KEY` overrides `LANGSMITH_API_KEY` for gateway authentication; if unset or empty, the integrations fall back to `LANGSMITH_API_KEY`. Keep native model names and provider selections unchanged. `true` (also `1` or `yes`) selects the hosted gateway; `false` (also `0` or `no`) or an unset or empty flag keeps direct access. A custom gateway root URL is also accepted; integrations append their provider paths. Remove explicit provider base URLs when using this switch, since those override gateway routing.

Sync each Python project you run: the root, `deep_tutor`, and `m5/l5` declare gateway-capable Anthropic, OpenAI, and Google integration minimums.

Tracing is separate: use `LANGSMITH_TRACING=true` and a valid `LANGSMITH_API_KEY` to trace, or `LANGSMITH_TRACING=false` to turn tracing off. A dedicated gateway key does not enable tracing, and `LANGSMITH_ENDPOINT` configures LangSmith APIs, not the gateway URL.

The root lesson scripts are clients of a deployment: setting gateway variables on a client does not change a remote agent. Set them in the agent server’s runtime environment (`deep_tutor/.env`, `m5/l5/.env`, or the deployment’s environment settings). `langgraph deploy` strips `LANGSMITH_API_KEY`, so explicitly supply `LANGSMITH_GATEWAY_API_KEY` as a runtime secret. Keep `LANGSMITH_API_KEY` locally for CLI and remote SDK authentication, and keep `DEEP_TUTOR_API_KEY`, Supabase, JWT, and other lesson credentials where used. The pinned Module 6 CLI has its own authentication and version requirements; use its direct-provider setup unless you separately verify gateway support for that CLI version.

You may export these settings in your shell instead of writing `.env`. Remove conflicting values from `.env` first: lesson loaders that use `override=True` / `override: true` prefer the file. Never commit credentials.

### Install dependencies

```bash
uv sync
```

---

## Setup Your Coding Agent

Using a coding agent to build your agents is encouraged throughout this course. Two additions make it significantly more effective: the LangChain Docs MCP server and the LangSmith tracing plugin.

### LangChain Docs MCP Server

Adding the LangChain Docs MCP server gives your coding agent direct access to LangChain, LangGraph, and LangSmith documentation — including search and a loaded skill that covers core concepts. Add it once and it is available in all your projects.

[Full setup instructions](https://docs.langchain.com/use-these-docs#use-our-mcp-server)

### LangSmith Skills

LangSmith skills give your coding agent on-demand capabilities for querying traces, generating datasets, and defining evaluators — directly from within your agent session.

[Full setup instructions](https://docs.langchain.com/langsmith/skills)

---

## Getting Started with LangSmith

- Create a [LangSmith](https://smith.langchain.com/) account
- Create a LangSmith API key

<img width="600" alt="LangSmith API key - step 1" src="https://github.com/user-attachments/assets/e39b8364-c3e3-4c75-a287-d9d4685caad5" />
<img width="600" alt="LangSmith API key - step 2" src="https://github.com/user-attachments/assets/2e916b2d-e3b0-4c59-a178-c5818604b8fe" />

### Installing uv

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for full instructions. Common options:


```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS with Homebrew
brew install uv

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
