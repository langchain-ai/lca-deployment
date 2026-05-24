# LangChain Deployment — Python

You can find the course at https://academy.langchain.com/courses/take/langsmith-deployments.

## Setup

### Prerequisites

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

Insert API keys directly into `.env` — [LangSmith](#getting-started-with-langsmith) (required) and Anthropic (required):

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

Install dependencies:

```bash
uv sync
```

---

### Getting Started with LangSmith

- Create a [LangSmith](https://smith.langchain.com/) account
- Create a LangSmith API key

<img width="600" alt="LangSmith API key - step 1" src="https://github.com/user-attachments/assets/e39b8364-c3e3-4c75-a287-d9d4685caad5" />
<img width="600" alt="LangSmith API key - step 2" src="https://github.com/user-attachments/assets/2e916b2d-e3b0-4c59-a178-c5818604b8fe" />

### Installing uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS with Homebrew
brew install uv

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
