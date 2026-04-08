# Tutor Chat Agent — Instructions v1

We are building a tutor chat agent.
The agent will help students understand lessons on LangChain, LangGraph, and LangSmith. It will be useful both as a tutor and as a coding example. The code to implement the agent will also be used as the subject of lessons.

The agent can be invoked via a UI or individual calls.

## Project Structure

The project lives in the `lca-deployment` repo. There are two fully self-contained implementations — Python and TypeScript — so a student follows one path end to end without touching the other.

```
lca-deployment/
  python/
    lang_chat/
      agent/
      ui/
      tutor_l1/
        tutor_l1_instructions.md
        tutor_l1_information.md
  ts/
    lang_chat/
      agent/
      ui/
      tutor_l1/
        tutor_l1_instructions.md
        tutor_l1_information.md
```

## UI

### General layout
The UI will have a graphic area at the top and a chat area at the bottom. The starting point is `langgraph_interactive.html`. There will be tabs for different lessons — starting with 1, growing over time. Only lesson 1 will be populated to start. Each lesson has a graphic area and a chat area.

### The graphic area
The graphics are interactive, as shown in `langgraph_interactive.html`. Clicking on sections sends a predefined question to the tutor agent, who responds in the chat area. There is also a free-form text input for students to ask their own questions.

### UI implementation
- `index.html` — layout and diagram, shared structure
- `agent_client.py` / `agent_client.ts` — the interesting file: connects to the deployed agent, manages assistants and threads. This is kept clearly separate from UI glue code so students can focus on the agent interaction logic.
- `server.py` (FastAPI) / `server.ts` (Express) — serves the HTML

### LangSmith Assistants
Each lesson tab maps to a different LangSmith assistant. The assistant's system prompt includes the lesson instructions (`tutor_lx_instructions.md`). Within a tab, users can create new threads representing different conversation threads.

## The Agent

### Libraries
- **Python**: `deepagents` (`uv add deepagents`), LangGraph, `langchain-mcp-adapters`
- **TypeScript**: `deepagentsjs`, LangGraph.js, MCP adapter

Both are separate LangGraph Cloud deployments.

### Model
Uses `init_chat_model` so any supported foundation model can be used. Default is `google_genai:gemini-2.0-flash` (generous free tier). Libraries for OpenAI, Anthropic, Gemini, and Ollama are included; all but Gemini are commented out.

### Persona
Empathetic but concise.

### Behavior
When a student asks a question, the agent:
1. Refers first to the lesson instructions (injected into the system prompt via the LangSmith assistant)
2. Calls `read_lesson_material` tool to retrieve content from the `tutor_lx/` directory
3. Falls back to the LangChain MCP docs server (`https://docs.langchain.com/mcp`) if needed
4. Occasionally quizzes the student when appropriate

### Tools
- `read_lesson_material` — reads lesson content from the `tutor_lx/` directory
- LangChain MCP docs server — `https://docs.langchain.com/mcp`
- Deep Agents built-ins as needed

### Deployment
- Runs locally via LangGraph Studio
- Deployed to LangGraph Cloud
- `langgraph.json` configured for each side (Python and TS)

## Lessons

Lesson content lives in `tutor_lx/` directories inside each `lang_chat/` folder:
- `tutor_lx_instructions.md` — how the lesson should be run (injected into the assistant system prompt)
- `tutor_lx_information.md` — lesson content used to answer questions and quiz students

Only `tutor_l1` is populated to start.
