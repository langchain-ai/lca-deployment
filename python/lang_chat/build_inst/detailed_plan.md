# Detailed Build Plan — Tutor Chat Agent

<!-- SDK & Library References -->
<!-- Deep Agents (Python):          https://docs.langchain.com/oss/python/deepagents/overview -->
<!-- Deep Agents (TypeScript):      https://github.com/langchain-ai/deepagentsjs -->
<!-- LangGraph SDK (Python):        https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/ -->
<!-- LangGraph SDK (TypeScript):    https://langchain-ai.github.io/langgraphjs/reference/ -->
<!-- langchain-mcp-adapters:        https://github.com/langchain-ai/langchain-mcp-adapters -->
<!-- LangChain MCP docs server:     https://docs.langchain.com/use-these-docs -->
<!-- LangSmith Assistants:          https://docs.langchain.com/langsmith/assistants -->

## Phase 1: Project Scaffolding

### 1.1 Directory structure
Create the full directory layout:
```
lca-deployment/
  python/
    lang_chat/
      agent/
      ui/
      tutor_l1/
  ts/
    lang_chat/
      agent/
      ui/
      tutor_l1/
```

### 1.2 Python project setup (`python/lang_chat/`)
- `pyproject.toml` with dependencies:
  - `deepagents`
  - `langgraph`
  - `langchain-mcp-adapters`
  - `langchain-google-genai` (active)
  - `langchain-openai` (included, commented in usage)
  - `langchain-anthropic` (included, commented in usage)
  - `langchain-ollama` (included, commented in usage)
  - `fastapi`, `uvicorn`
- `.env.example` with placeholder keys for all providers
- `.gitignore` including `.env` and `.venv`
- `langgraph.json` pointing to the agent graph

### 1.3 TypeScript project setup (`ts/lang_chat/`)
- `package.json` with dependencies:
  - `deepagentsjs`
  - `@langchain/langgraph`
  - `@langchain/langgraph-sdk`
  - `@langchain/google-genai` (active)
  - `@langchain/openai` (included, commented in usage)
  - `@langchain/anthropic` (included, commented in usage)
  - `@langchain/community` (for Ollama)
  - `express`, `@types/express`
  - `langchain-mcp-adapters` (TS)
- `tsconfig.json` — match essentials course config
- `.env.example`
- `.gitignore`
- `langgraph.json` pointing to the agent graph

---

## Phase 2: Lesson Content Placeholders

### 2.1 Python side (`python/lang_chat/tutor_l1/`)
- `tutor_l1_instructions.md` — placeholder: lesson title, brief description of how the lesson runs, placeholder for tutor behavior guidance
- `tutor_l1_information.md` — placeholder: lesson topic, placeholder content sections

### 2.2 TypeScript side (`ts/lang_chat/tutor_l1/`)
- Same files, same placeholder content

---

## Phase 3: The Agent

### 3.1 Python agent (`python/lang_chat/agent/`)

**`agent.py`** — the main graph file
- Import `create_deep_agent` from `deepagents`
- Initialize model with `init_chat_model`:
  ```python
  model = init_chat_model("google_genai:gemini-2.0-flash")
  # model = init_chat_model("anthropic:claude-sonnet-4-6")
  # model = init_chat_model("openai:gpt-4o")
  # model = init_chat_model("ollama:llama3")
  ```
- Define `read_lesson_material` tool — reads from `tutor_l1/tutor_l1_information.md`
- Connect to LangChain MCP server at `https://docs.langchain.com/mcp` via `langchain-mcp-adapters`
- Create agent with `create_deep_agent(model=model, tools=[read_lesson_material, ...mcp_tools], system_prompt=...)`
- System prompt: empathetic but concise tutor persona; priority order (lesson instructions → lesson material → MCP); quiz students occasionally
- Export the compiled graph as `graph`

**`system_prompt.py`** — the tutor system prompt (kept separate for clarity as a lesson example)

### 3.2 TypeScript agent (`ts/lang_chat/agent/`)

**`agent.ts`** — equivalent implementation in TypeScript
- Same structure as Python version
- Uses `createDeepAgent` from `deepagentsjs`
- `initChatModel` for model initialization with same commented alternatives
- `readLessonMaterial` tool
- MCP connection to `https://docs.langchain.com/mcp`

**`systemPrompt.ts`** — tutor system prompt

### 3.3 `langgraph.json` (both sides)
```json
{
  "dependencies": ["."],
  "graphs": {
    "tutor_l1": "./agent/agent.py:graph"
  },
  "env": ".env"
}
```

---

## Phase 4: The UI

### 4.1 HTML (`index.html`) — duplicated in each side (`python/lang_chat/ui/` and `ts/lang_chat/ui/`)
- Refactored from `langgraph_interactive.html`
- Config bar: deployment URL, API key, assistant ID
- Tabs: one per lesson (lesson 1 active, others greyed out)
- Graphic area: interactive SVG diagram (lesson 1 diagram from existing HTML)
- Chat area: agent response panel + free-form text input
- "New thread" button
- Does NOT contain agent client logic — only DOM structure and event wiring that calls into `agent_client`

### 4.2 Python agent client (`python/lang_chat/ui/agent_client.py`)
The interesting file — clearly documented for students:
- `get_client(url, api_key)` — creates LangGraph SDK client
- `get_or_create_thread(client, thread_id)` — creates a new thread or returns existing
- `send_message(client, thread_id, assistant_id, message)` — sends a message and streams the response
- Uses `langgraph-sdk` Python client

### 4.3 Python server (`python/lang_chat/ui/server.py`)
- FastAPI app
- Serves `index.html`
- POST `/chat` endpoint — calls `agent_client.py` functions and streams response back
- Minimal — just glue

### 4.4 TypeScript agent client (`ts/lang_chat/ui/agent_client.ts`)
The interesting file — parallel structure to Python version:
- `getClient(url, apiKey)` — creates LangGraph SDK client
- `getOrCreateThread(client, threadId)` — creates or returns thread
- `sendMessage(client, threadId, assistantId, message)` — sends message and streams response
- Uses `@langchain/langgraph-sdk`

### 4.5 TypeScript server (`ts/lang_chat/ui/server.ts`)
- Express app
- Serves `index.html`
- POST `/chat` endpoint — calls `agent_client.ts` and streams response
- Minimal — just glue

---

## Phase 5: Running & Verification

### 5.1 Local — LangGraph Studio (Python)
```bash
cd python/lang_chat
uv run langgraph dev
```
- Opens LangGraph Studio at `http://localhost:8123`
- Select the `tutor_l1` assistant
- Verify MCP tool connects to LangChain docs
- Verify `read_lesson_material` tool reads lesson content
- Test a few predefined questions and free-form input

### 5.2 Local — LangGraph Studio (TypeScript)
```bash
cd ts/lang_chat
pnpm langgraph dev
```
- Same verification as Python

### 5.3 UI — Python (against local Studio)
```bash
cd python/lang_chat/ui
uv run uvicorn server:app --reload
```
- Open `http://localhost:8000` in browser
- Enter `http://localhost:8123` as deployment URL
- Enter LangSmith API key
- Enter `tutor_l1` as assistant ID
- Test click-to-ask and free-form chat
- Test "new thread" button

### 5.4 UI — TypeScript (against local Studio)
```bash
cd ts/lang_chat/ui
pnpm dev
```
- Open `http://localhost:3000` in browser
- Same tests as Python UI

### 5.5 Deploy to LangGraph Cloud
**Python:**
```bash
cd python/lang_chat
uv run langgraph deploy
```
**TypeScript:**
```bash
cd ts/lang_chat
pnpm langgraph deploy
```
- Note the deployment URL for each
- Set up assistant `tutor_l1` in LangSmith UI for each deployment

### 5.6 UI — against deployed agents
- Update deployment URL in the UI config bar to the LangGraph Cloud URL
- Re-run smoke tests for both Python and TS UI
- Verify streaming works end-to-end
- Verify thread persistence across page refreshes

---

## Build Order
1. Scaffolding (Phase 1)
2. Lesson placeholders (Phase 2)
3. Python agent (Phase 3.1)
4. Python UI (Phase 4.2 + 4.3 + 4.1)
5. Verify Python end-to-end (Phase 5.1 + 5.3)
6. TypeScript agent (Phase 3.2)
7. TypeScript UI (Phase 4.4 + 4.5)
8. Verify TypeScript end-to-end (Phase 5.2 + 5.4)
9. Deploy both (Phase 5.5)
10. Smoke test deployed versions (Phase 5.6)
